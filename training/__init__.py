from flask import Blueprint, render_template, request, jsonify, current_app
from sqlalchemy.exc import IntegrityError
from models import db, Session, Image, Shot, ShotRevision, Athlete
import os
import json

training_bp = Blueprint("training", __name__, template_folder="templates", static_folder="static")


@training_bp.route("/")
def index():
    # Render main training UI
    athletes = Athlete.query.order_by(Athlete.first_name, Athlete.last_name).all()
    return render_template("training/index.html", athletes=athletes)


@training_bp.route("/athletes", methods=["GET"])
def athletes_list():
    athletes = Athlete.query.order_by(Athlete.first_name, Athlete.last_name).all()
    return jsonify([{"id": a.id, "name": f"{a.first_name} {a.last_name or ''}".strip()} for a in athletes])


@training_bp.route("/start", methods=["POST"])
def start_session():
    try:
        data = request.json or {}
        name = data.get("name") or "Training"
        athlete_ids = data.get("athlete_ids", [])

        s = Session(name=name, mode="training")

        if athlete_ids:
            athletes = Athlete.query.filter(Athlete.id.in_(athlete_ids)).all()
            s.athletes = athletes

        db.session.add(s)
        db.session.commit()

        return jsonify({"id": s.id, "name": s.name, "athletes": [a.id for a in s.athletes]})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to start session: {e}", exc_info=True)
        return jsonify({"error": f"Failed to start session: {str(e)}"}), 500


@training_bp.route("/session/<int:session_id>/images", methods=["GET"])
def session_images(session_id):
    s = Session.query.get_or_404(session_id)
    images = []
    for img in s.images:
        d = img.to_dict()
        # include minimal shots info
        d["shots"] = [{"id": sh.id, "auto_score": sh.auto_score, "final_score": sh.final_score} for sh in img.shots]
        d["created_at"] = str(img.created_at)
        images.append(d)
    # sort by created_at ascending
    images.sort(key=lambda x: x.get("created_at") or "")
    return jsonify(images)


@training_bp.route("/image/<int:image_id>", methods=["GET"])
def image_detail(image_id):
    img = Image.query.get_or_404(image_id)
    d = img.to_dict()
    d["shots"] = [s.to_dict() for s in img.shots]
    # Include athlete info if present
    if img.athlete:
        d['athlete'] = { 'id': img.athlete.id, 'name': f"{img.athlete.first_name} {img.athlete.last_name or ''}".strip() }
    return jsonify(d)


@training_bp.route("/save", methods=["POST"])
def save_image_and_shots():
    """Persist processed scoring result into DB for a given session.

    Expects JSON: { "session_id": int, "filename": str, "result": dict }
    The `result` should be identical to score_image() output.
    """
    data = request.json or {}
    session_id = data.get("session_id")
    filename = data.get("filename")
    result = data.get("result")

    if not session_id or not filename or not result:
        return jsonify({"error": "session_id, filename and result are required"}), 400

    sess = Session.query.get_or_404(session_id)

    # Determine paths
    upload_orig = None
    # Look in static/uploads and static/snapshots
    uploads = os.path.join(current_app.root_path, "static", "uploads")
    snaps = os.path.join(current_app.root_path, "static", "snapshots")
    p1 = os.path.join(uploads, filename)
    p2 = os.path.join(snaps, filename)

    if os.path.exists(p1):
        upload_orig = "/static/uploads/" + filename
    elif os.path.exists(p2):
        upload_orig = "/static/snapshots/" + filename
    else:
        # If file doesn't exist we still persist record with filename if the file is external
        upload_orig = f"/static/uploads/{filename}"

    out_overlay = result.get("images", {}).get("overlay")
    out_scored = result.get("images", {}).get("scored")
    out_ideal = result.get("images", {}).get("ideal")

    # Normalize paths to be absolute (start with '/') to avoid blueprint-relative requests
    def norm(p):
        if not p:
            return p
        return p if p.startswith("/") else f"/{p}"

    out_overlay = norm(out_overlay)
    out_scored = norm(out_scored)
    out_ideal = norm(out_ideal)
    upload_orig = norm(upload_orig)

    # allow passing athlete_id to assign image to an athlete
    athlete_id = data.get('athlete_id') if data else None
    img = Image(filename=filename, original_path=upload_orig, overlay_path=out_overlay, scored_path=out_scored, session=sess, athlete_id=athlete_id)
    # store ideal path if model provides it
    if out_ideal:
        img.scored_path = img.scored_path or None
        # attach as attribute - add column support in model
        try:
            img.ideal_path = out_ideal
        except Exception:
            pass
    db.session.add(img)
    db.session.flush()  # get id

    shots = result.get("shots", [])
    for s in shots:
        shot = Shot(
            shot_index=s.get("id"),
            center_px=s.get("center_px"),
            dx_mm=s.get("dx_mm"),
            dy_mm=s.get("dy_mm"),
            dist_mm=s.get("dist_mm"),
            bullet_radius_px=s.get("bullet_radius_px"),
            auto_score=s.get("score"),
            final_score=s.get("score"),
            metadata_json=s,
            image=img,
        )
        db.session.add(shot)

    db.session.commit()

    # Add messages/warnings for client UI when detection had issues
    messages = []
    if not shots:
        messages.append("No shots detected by the model.")
    if isinstance(result, dict) and result.get("errors"):
        # append stringified errors
        try:
            messages.extend([str(x) for x in result.get("errors")])
        except Exception:
            messages.append(str(result.get("errors")))

    return jsonify({"ok": True, "image_id": img.id, "shots_count": len(shots), "total_score": sum(s.get("score",0) for s in shots), "messages": messages})


@training_bp.route("/image/<int:image_id>/delete", methods=["POST"])
def delete_image(image_id):
    img = Image.query.get_or_404(image_id)
    db.session.delete(img)
    db.session.commit()
    return jsonify({"ok": True})


@training_bp.route("/session/<int:session_id>/finish", methods=["POST"])
def finish_session(session_id):
    s = Session.query.get_or_404(session_id)
    s.finished_at = db.func.now()
    db.session.commit()
    return jsonify({"ok": True, "finished_at": str(s.finished_at)})


@training_bp.route("/shot/<int:shot_id>", methods=["GET"])
def get_shot(shot_id):
    shot = Shot.query.get_or_404(shot_id)
    res = shot.to_dict()
    res.update({
        "image": {"id": shot.image.id, "filename": shot.image.filename, "overlay_path": shot.image.overlay_path},
    })
    return jsonify(res)


@training_bp.route("/shot/<int:shot_id>/edit", methods=["POST"])
def edit_shot(shot_id):
    shot = Shot.query.get_or_404(shot_id)
    data = request.json or {}
    new_score = data.get("final_score")
    note = data.get("note")

    if new_score is None:
        return jsonify({"error": "final_score required"}), 400

    prev = shot.final_score
    shot.final_score = int(new_score)

    rev = ShotRevision(shot=shot, prev_score=prev or shot.auto_score, new_score=shot.final_score, note=note)
    db.session.add(rev)
    db.session.commit()

    return jsonify({"ok": True, "shot": shot.to_dict()})


@training_bp.route("/shot_sample", methods=["GET"])
def shot_sample():
    image_id = request.args.get('image_id', type=int)
    if not image_id:
        return jsonify({"error": "image_id required"}), 400
    img = Image.query.get_or_404(image_id)
    shots = [ {"id": s.id, "auto_score": s.auto_score, "final_score": s.final_score} for s in img.shots ]
    return jsonify({"image_id": img.id, "shots": shots})
