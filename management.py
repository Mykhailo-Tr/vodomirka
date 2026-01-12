from datetime import datetime

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)

from models import db, Scope, Rifle, Jacket, Rank, Athlete, Location

management_bp = Blueprint("management", __name__, template_folder="templates")


@management_bp.route("/")
def dashboard():
    """Landing page for the management section."""
    return render_template("management/index.html")


# ---------- Scope ----------


@management_bp.route("/scopes")
def scopes_list():
    scopes = Scope.query.order_by(Scope.name).all()
    return render_template("management/scopes/list.html", scopes=scopes)


@management_bp.route("/scopes/create", methods=["GET", "POST"])
def scopes_create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        note = request.form.get("note") or None
        if not name:
            flash("Scope name is required.", "danger")
        else:
            scope = Scope(name=name, note=note)
            db.session.add(scope)
            db.session.commit()
            flash("Scope created successfully.", "success")
            return redirect(url_for("management.scopes_list"))
    return render_template("management/scopes/form.html", scope=None)


@management_bp.route("/scopes/<int:scope_id>/edit", methods=["GET", "POST"])
def scopes_edit(scope_id: int):
    scope = Scope.query.get_or_404(scope_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        note = request.form.get("note") or None
        if not name:
            flash("Scope name is required.", "danger")
        else:
            scope.name = name
            scope.note = note
            db.session.commit()
            flash("Scope updated successfully.", "success")
            return redirect(url_for("management.scopes_list"))
    return render_template("management/scopes/form.html", scope=scope)


@management_bp.route("/scopes/<int:scope_id>/delete", methods=["POST"])
def scopes_delete(scope_id: int):
    scope = Scope.query.get_or_404(scope_id)
    db.session.delete(scope)
    db.session.commit()
    flash("Scope deleted.", "info")
    return redirect(url_for("management.scopes_list"))


# ---------- Rifle ----------


@management_bp.route("/rifles")
def rifles_list():
    rifles = Rifle.query.order_by(Rifle.name).all()
    return render_template("management/rifles/list.html", rifles=rifles)


@management_bp.route("/rifles/create", methods=["GET", "POST"])
def rifles_create():
    scopes = Scope.query.order_by(Scope.name).all()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        scope_id = request.form.get("scope_id")
        note = request.form.get("note") or None

        if not name or not scope_id:
            flash("Rifle name and scope are required.", "danger")
        else:
            rifle = Rifle(name=name, scope_id=int(scope_id), note=note)
            db.session.add(rifle)
            db.session.commit()
            flash("Rifle created successfully.", "success")
            return redirect(url_for("management.rifles_list"))

    return render_template("management/rifles/form.html", rifle=None, scopes=scopes)


@management_bp.route("/rifles/<int:rifle_id>/edit", methods=["GET", "POST"])
def rifles_edit(rifle_id: int):
    rifle = Rifle.query.get_or_404(rifle_id)
    scopes = Scope.query.order_by(Scope.name).all()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        scope_id = request.form.get("scope_id")
        note = request.form.get("note") or None

        if not name or not scope_id:
            flash("Rifle name and scope are required.", "danger")
        else:
            rifle.name = name
            rifle.scope_id = int(scope_id)
            rifle.note = note
            db.session.commit()
            flash("Rifle updated successfully.", "success")
            return redirect(url_for("management.rifles_list"))

    return render_template("management/rifles/form.html", rifle=rifle, scopes=scopes)


@management_bp.route("/rifles/<int:rifle_id>/delete", methods=["POST"])
def rifles_delete(rifle_id: int):
    rifle = Rifle.query.get_or_404(rifle_id)
    db.session.delete(rifle)
    db.session.commit()
    flash("Rifle deleted.", "info")
    return redirect(url_for("management.rifles_list"))


# ---------- Jacket ----------


@management_bp.route("/jackets")
def jackets_list():
    jackets = Jacket.query.order_by(Jacket.name).all()
    return render_template("management/jackets/list.html", jackets=jackets)


@management_bp.route("/jackets/create", methods=["GET", "POST"])
def jackets_create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        note = request.form.get("note") or None
        if not name:
            flash("Jacket name is required.", "danger")
        else:
            jacket = Jacket(name=name, note=note)
            db.session.add(jacket)
            db.session.commit()
            flash("Jacket created successfully.", "success")
            return redirect(url_for("management.jackets_list"))
    return render_template("management/jackets/form.html", jacket=None)


@management_bp.route("/jackets/<int:jacket_id>/edit", methods=["GET", "POST"])
def jackets_edit(jacket_id: int):
    jacket = Jacket.query.get_or_404(jacket_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        note = request.form.get("note") or None
        if not name:
            flash("Jacket name is required.", "danger")
        else:
            jacket.name = name
            jacket.note = note
            db.session.commit()
            flash("Jacket updated successfully.", "success")
            return redirect(url_for("management.jackets_list"))
    return render_template("management/jackets/form.html", jacket=jacket)


@management_bp.route("/jackets/<int:jacket_id>/delete", methods=["POST"])
def jackets_delete(jacket_id: int):
    jacket = Jacket.query.get_or_404(jacket_id)
    db.session.delete(jacket)
    db.session.commit()
    flash("Jacket deleted.", "info")
    return redirect(url_for("management.jackets_list"))


# ---------- Rank ----------


@management_bp.route("/ranks")
def ranks_list():
    ranks = Rank.query.order_by(Rank.name).all()
    return render_template("management/ranks/list.html", ranks=ranks)


@management_bp.route("/ranks/create", methods=["GET", "POST"])
def ranks_create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        note = request.form.get("note") or None
        if not name:
            flash("Rank name is required.", "danger")
        else:
            rank = Rank(name=name, note=note)
            db.session.add(rank)
            db.session.commit()
            flash("Rank created successfully.", "success")
            return redirect(url_for("management.ranks_list"))
    return render_template("management/ranks/form.html", rank=None)


@management_bp.route("/ranks/<int:rank_id>/edit", methods=["GET", "POST"])
def ranks_edit(rank_id: int):
    rank = Rank.query.get_or_404(rank_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        note = request.form.get("note") or None
        if not name:
            flash("Rank name is required.", "danger")
        else:
            rank.name = name
            rank.note = note
            db.session.commit()
            flash("Rank updated successfully.", "success")
            return redirect(url_for("management.ranks_list"))
    return render_template("management/ranks/form.html", rank=rank)


@management_bp.route("/ranks/<int:rank_id>/delete", methods=["POST"])
def ranks_delete(rank_id: int):
    rank = Rank.query.get_or_404(rank_id)
    db.session.delete(rank)
    db.session.commit()
    flash("Rank deleted.", "info")
    return redirect(url_for("management.ranks_list"))


# ---------- Location ----------


@management_bp.route("/locations")
def locations_list():
    locations = Location.query.order_by(Location.name).all()
    return render_template("management/locations/list.html", locations=locations)


@management_bp.route("/locations/create", methods=["GET", "POST"])
def locations_create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        note = request.form.get("note") or None
        if not name:
            flash("Location name is required.", "danger")
        else:
            location = Location(name=name, note=note)
            db.session.add(location)
            db.session.commit()
            flash("Location created successfully.", "success")
            return redirect(url_for("management.locations_list"))
    return render_template("management/locations/form.html", location=None)


@management_bp.route("/locations/<int:location_id>/edit", methods=["GET", "POST"])
def locations_edit(location_id: int):
    location = Location.query.get_or_404(location_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        note = request.form.get("note") or None
        if not name:
            flash("Location name is required.", "danger")
        else:
            location.name = name
            location.note = note
            db.session.commit()
            flash("Location updated successfully.", "success")
            return redirect(url_for("management.locations_list"))
    return render_template("management/locations/form.html", location=location)


@management_bp.route("/locations/<int:location_id>/delete", methods=["POST"])
def locations_delete(location_id: int):
    location = Location.query.get_or_404(location_id)
    db.session.delete(location)
    db.session.commit()
    flash("Location deleted.", "info")
    return redirect(url_for("management.locations_list"))


# ---------- Athlete ----------


@management_bp.route("/athletes")
def athletes_list():
    athletes = (
        Athlete.query.order_by(Athlete.first_name).all()
    )
    return render_template("management/athletes/list.html", athletes=athletes)


@management_bp.route("/athletes/create", methods=["GET", "POST"])
def athletes_create():
    ranks = Rank.query.order_by(Rank.name).all()
    rifles = Rifle.query.order_by(Rifle.name).all()
    jackets = Jacket.query.order_by(Jacket.name).all()
    locations = Location.query.order_by(Location.name).all()

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip() or None
        gender = request.form.get("gender", "").strip()
        dob_raw = request.form.get("date_of_birth", "").strip()
        rank_id = request.form.get("rank_id") or None
        rifle_id = request.form.get("rifle_id")
        jacket_id = request.form.get("jacket_id")
        location_id = request.form.get("location_id") or None
        team = request.form.get("team") or None
        phone_number = request.form.get("phone_number") or None

        if not first_name or not gender or not rifle_id or not jacket_id:
            flash("First name, gender, rifle and jacket are required.", "danger")
        else:
            dob = None
            if dob_raw:
                try:
                    dob = datetime.strptime(dob_raw, "%Y-%m-%d").date()
                except ValueError:
                    flash("Invalid date format for date of birth.", "danger")
                    return render_template(
                        "management/athletes/form.html",
                        athlete=None,
                        ranks=ranks,
                        rifles=rifles,
                        jackets=jackets,
                        locations=locations,
                    )

            athlete = Athlete(
                first_name=first_name,
                last_name=last_name,
                gender=gender,
                date_of_birth=dob,
                rank_id=int(rank_id) if rank_id else None,
                rifle_id=int(rifle_id),
                jacket_id=int(jacket_id),
                location_id=int(location_id) if location_id else None,
                team=team,
                phone_number=phone_number,
            )
            db.session.add(athlete)
            db.session.commit()
            flash("Athlete created successfully.", "success")
            return redirect(url_for("management.athletes_list"))

    return render_template(
        "management/athletes/form.html",
        athlete=None,
        ranks=ranks,
        rifles=rifles,
        jackets=jackets,
        locations=locations,
    )


@management_bp.route("/athletes/<int:athlete_id>/edit", methods=["GET", "POST"])
def athletes_edit(athlete_id: int):
    athlete = Athlete.query.get_or_404(athlete_id)
    ranks = Rank.query.order_by(Rank.name).all()
    rifles = Rifle.query.order_by(Rifle.name).all()
    jackets = Jacket.query.order_by(Jacket.name).all()
    locations = Location.query.order_by(Location.name).all()

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip() or None
        gender = request.form.get("gender", "").strip()
        dob_raw = request.form.get("date_of_birth", "").strip()
        rank_id = request.form.get("rank_id") or None
        rifle_id = request.form.get("rifle_id")
        jacket_id = request.form.get("jacket_id")
        location_id = request.form.get("location_id") or None
        team = request.form.get("team") or None
        phone_number = request.form.get("phone_number") or None

        if not first_name or not gender or not rifle_id or not jacket_id:
            flash("First name, gender, rifle and jacket are required.", "danger")
        else:
            dob = None
            if dob_raw:
                try:
                    dob = datetime.strptime(dob_raw, "%Y-%m-%d").date()
                except ValueError:
                    flash("Invalid date format for date of birth.", "danger")
                    return render_template(
                        "management/athletes/form.html",
                        athlete=athlete,
                        ranks=ranks,
                        rifles=rifles,
                        jackets=jackets,
                        locations=locations,
                    )

            athlete.first_name = first_name
            athlete.last_name = last_name
            athlete.gender = gender
            athlete.date_of_birth = dob
            athlete.rank_id = int(rank_id) if rank_id else None
            athlete.rifle_id = int(rifle_id)
            athlete.jacket_id = int(jacket_id)
            athlete.location_id = int(location_id) if location_id else None
            athlete.team = team
            athlete.phone_number = phone_number

            db.session.commit()
            flash("Athlete updated successfully.", "success")
            return redirect(url_for("management.athletes_list"))

    return render_template(
        "management/athletes/form.html",
        athlete=athlete,
        ranks=ranks,
        rifles=rifles,
        jackets=jackets,
        locations=locations,
    )


@management_bp.route("/athletes/<int:athlete_id>/delete", methods=["POST"])
def athletes_delete(athlete_id: int):
    athlete = Athlete.query.get_or_404(athlete_id)
    db.session.delete(athlete)
    db.session.commit()
    flash("Athlete deleted.", "info")
    return redirect(url_for("management.athletes_list"))

