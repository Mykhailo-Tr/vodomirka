from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from datetime import datetime
import os
import base64
import uuid
from sqlalchemy import or_
from models import db, Exercise, Competition, CompetitionAthlete, Series, Athlete, Image, Shot
from scorer import score_image
from config import OUTPUT_DIR

competition_bp = Blueprint('competition', __name__)

# Helper functions
def get_upload_dirs():
    """Get upload and snapshot directories."""
    upload_dir = "static/uploads"
    snapshot_dir = "static/snapshots"
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(snapshot_dir, exist_ok=True)
    return upload_dir, snapshot_dir

def ensure_system_exercises():
    """Create system exercises if they don't exist."""
    system_exercises = [
        {
            "name": "ГП-11",
            "description": "Standard exercise with small and large speed, 20 + 20 shots",
            "total_series": 2,
            "shots_per_series": 20,
            "timing_type": "mixed"
        },
        {
            "name": "ГП-11a", 
            "description": "Variable speed exercise, 20 + 20 shots",
            "total_series": 2,
            "shots_per_series": 20,
            "timing_type": "variable"
        },
        {
            "name": "ГП-12",
            "description": "Extended exercise, 30 + 30 shots", 
            "total_series": 2,
            "shots_per_series": 30,
            "timing_type": "fixed"
        }
    ]
    
    for ex_data in system_exercises:
        existing = Exercise.query.filter_by(name=ex_data["name"], is_system=True).first()
        if not existing:
            exercise = Exercise(
                name=ex_data["name"],
                description=ex_data["description"],
                total_series=ex_data["total_series"],
                shots_per_series=ex_data["shots_per_series"],
                timing_type=ex_data["timing_type"],
                is_system=True
            )
            db.session.add(exercise)
    
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

# Routes

@competition_bp.route('/')
def index():
    """Competition mode main page."""
    ensure_system_exercises()
    
    # Get active and recent competitions
    active_competitions = Competition.query.filter_by(status='active').order_by(Competition.created_at.desc()).all()
    recent_competitions = Competition.query.filter(
        or_(Competition.status=='draft', Competition.status=='finished')
    ).order_by(Competition.created_at.desc()).limit(10).all()
    
    return render_template('competition/index.html', 
                         active_competitions=active_competitions,
                         recent_competitions=recent_competitions)

@competition_bp.route('/exercises')
def exercises():
    """List and manage exercises."""
    system_exercises = Exercise.query.filter_by(is_system=True).order_by(Exercise.name).all()
    custom_exercises = Exercise.query.filter_by(is_system=False).order_by(Exercise.name).all()
    
    return render_template('competition/exercises.html',
                         system_exercises=system_exercises,
                         custom_exercises=custom_exercises)

@competition_bp.route('/exercises/create', methods=['GET', 'POST'])
def create_exercise():
    """Create a new custom exercise."""
    if request.method == 'POST':
        data = request.get_json()
        
        exercise = Exercise(
            name=data['name'],
            description=data.get('description', ''),
            total_series=int(data['total_series']),
            shots_per_series=int(data['shots_per_series']),
            timing_type=data['timing_type'],
            is_system=False
        )
        
        db.session.add(exercise)
        try:
            db.session.commit()
            return jsonify({"success": True, "exercise": exercise.to_dict()})
        except Exception as e:
            db.session.rollback()
            return jsonify({"success": False, "error": str(e)}), 400
    
    return render_template('competition/create_exercise.html')

@competition_bp.route('/exercises/<int:exercise_id>/edit', methods=['GET', 'POST'])
def edit_exercise(exercise_id):
    """Edit a custom exercise."""
    exercise = Exercise.query.get_or_404(exercise_id)
    
    if exercise.is_system:
        flash('System exercises cannot be edited', 'error')
        return redirect(url_for('competition.exercises'))
    
    if request.method == 'POST':
        data = request.get_json()
        
        exercise.name = data['name']
        exercise.description = data.get('description', '')
        exercise.total_series = int(data['total_series'])
        exercise.shots_per_series = int(data['shots_per_series'])
        exercise.timing_type = data['timing_type']
        
        try:
            db.session.commit()
            return jsonify({"success": True, "exercise": exercise.to_dict()})
        except Exception as e:
            db.session.rollback()
            return jsonify({"success": False, "error": str(e)}), 400
    
    return render_template('competition/edit_exercise.html', exercise=exercise)

@competition_bp.route('/exercises/<int:exercise_id>/delete', methods=['POST'])
def delete_exercise(exercise_id):
    """Delete a custom exercise."""
    exercise = Exercise.query.get_or_404(exercise_id)
    
    if exercise.is_system:
        return jsonify({"success": False, "error": "System exercises cannot be deleted"}), 400
    
    try:
        db.session.delete(exercise)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400

@competition_bp.route('/create', methods=['GET', 'POST'])
def create_competition():
    """Create a new competition."""
    ensure_system_exercises()
    
    if request.method == 'POST':
        data = request.get_json()
        
        competition = Competition(
            name=data['name'],
            exercise_id=int(data['exercise_id'])
        )
        
        db.session.add(competition)
        db.session.flush()  # Get the ID
        
        # Add athletes
        for athlete_id in data['athlete_ids']:
            comp_athlete = CompetitionAthlete(
                competition_id=competition.id,
                athlete_id=int(athlete_id)
            )
            db.session.add(comp_athlete)
        
        try:
            db.session.commit()
            return jsonify({"success": True, "competition": competition.to_dict()})
        except Exception as e:
            db.session.rollback()
            return jsonify({"success": False, "error": str(e)}), 400
    
    exercises = Exercise.query.order_by(Exercise.is_system.desc(), Exercise.name).all()
    athletes = Athlete.query.order_by(Athlete.first_name, Athlete.last_name).all()
    
    return render_template('competition/create_competition.html',
                         exercises=exercises,
                         athletes=athletes)

@competition_bp.route('/<int:competition_id>')
def manage_competition(competition_id):
    """Manage a specific competition."""
    competition = Competition.query.get_or_404(competition_id)
    competition_data = competition.to_dict()
    
    # Get detailed athlete data with series
    athletes_data = []
    for comp_athlete in competition.athletes:
        athlete_data = comp_athlete.to_dict()
        
        # Add series details
        series_list = []
        for i in range(competition.exercise.total_series):
            series = Series.query.filter_by(
                competition_athlete_id=comp_athlete.id,
                series_number=i + 1
            ).first()
            
            if not series:
                series = Series(
                    competition_athlete_id=comp_athlete.id,
                    series_number=i + 1
                )
                db.session.add(series)
                db.session.commit()
            
            series_list.append(series.to_dict())
        
        athlete_data['series'] = series_list
        athletes_data.append(athlete_data)
    
    return render_template('competition/manage.html',
                         competition=competition_data,
                         athletes=athletes_data,
                         exercise=competition.exercise.to_dict())

@competition_bp.route('/<int:competition_id>/start', methods=['POST'])
def start_competition(competition_id):
    """Start a competition."""
    competition = Competition.query.get_or_404(competition_id)
    
    if competition.status != 'draft':
        return jsonify({"success": False, "error": "Competition can only be started from draft status"}), 400
    
    competition.status = 'active'
    competition.started_at = datetime.utcnow()
    
    try:
        db.session.commit()
        return jsonify({"success": True, "competition": competition.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400

@competition_bp.route('/<int:competition_id>/finish', methods=['POST'])
def finish_competition(competition_id):
    """Finish a competition."""
    competition = Competition.query.get_or_404(competition_id)
    
    if competition.status != 'active':
        return jsonify({"success": False, "error": "Only active competitions can be finished"}), 400
    
    if not competition.can_finish():
        return jsonify({"success": False, "error": "Cannot finish competition: some athletes have unfinished series"}), 400
    
    competition.status = 'finished'
    competition.finished_at = datetime.utcnow()
    
    try:
        db.session.commit()
        return jsonify({"success": True, "competition": competition.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400

@competition_bp.route('/<int:competition_id>/delete', methods=['POST'])
def delete_competition(competition_id):
    """Delete a competition."""
    competition = Competition.query.get_or_404(competition_id)
    
    if competition.status == 'active':
        return jsonify({"success": False, "error": "Active competitions cannot be deleted"}), 400
    
    try:
        db.session.delete(competition)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400

@competition_bp.route('/series/<int:series_id>/start', methods=['POST'])
def start_series(series_id):
    """Start a series for an athlete."""
    series = Series.query.get_or_404(series_id)
    
    if series.status != 'active':
        return jsonify({"success": False, "error": "Series is already finished"}), 400
    
    if series.started_at is None:
        series.started_at = datetime.utcnow()
    
    try:
        db.session.commit()
        return jsonify({"success": True, "series": series.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400

@competition_bp.route('/series/<int:series_id>/finish', methods=['POST'])
def finish_series(series_id):
    """Finish a series (normal or early)."""
    series = Series.query.get_or_404(series_id)
    
    if series.status != 'active':
        return jsonify({"success": False, "error": "Series is already finished"}), 400
    
    data = request.get_json()
    finish_type = data.get('type', 'normal')  # 'normal' or 'early'
    
    series.status = 'finished' if finish_type == 'normal' else 'finished_early'
    series.finished_at = datetime.utcnow()
    
    try:
        db.session.commit()
        return jsonify({"success": True, "series": series.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400

@competition_bp.route('/series/<int:series_id>/upload', methods=['POST'])
def upload_image(series_id):
    """Upload an image for a series."""
    series = Series.query.get(series_id)
    if not series:
        return jsonify({"success": False, "error": f"Series {series_id} not found"}), 404
    
    if series.status != 'active':
        return jsonify({"success": False, "error": "Cannot upload images to finished series"}), 400
    
    upload_dir, snapshot_dir = get_upload_dirs()
    
    # Primary: multipart/form-data (same pattern as scoring/training)
    file = request.files.get("image")
    if file and file.filename:
        filename = f"series_{series_id}_{uuid.uuid4().hex[:8]}_{file.filename}"
        path = os.path.join(upload_dir, filename)
        file.save(path)
        image_type = "upload"
    else:
        # Backward-compatible fallback: JSON base64 snapshot
        payload = request.get_json(silent=True) or {}
        data = payload.get("image")
        if not data:
            return jsonify({"success": False, "error": "No image file provided"}), 400

        if "," in data:
            data = data.split(",")[1]

        import cv2
        import numpy as np

        try:
            img_data = base64.b64decode(data)
        except Exception:
            return jsonify({"success": False, "error": "Invalid base64 image data"}), 400

        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({"success": False, "error": "Invalid image data"}), 400

        filename = f"series_{series_id}_{uuid.uuid4().hex[:8]}_snapshot.jpg"
        path = os.path.join(snapshot_dir, filename)
        cv2.imwrite(path, img)
        image_type = "snapshot"
    
    # Process image with scorer first (like training mode)
    try:
        result = score_image(path)
        
        # Create image record following training mode pattern
        image = Image(
            filename=filename,
            original_path="/" + path.replace("\\", "/"),
            athlete_id=series.competition_athlete.athlete_id,
            series_id=series_id
            # session_id will be automatically set by the event listener
        )
        
        # Update image with processed paths
        name, ext = os.path.splitext(filename)
        image.overlay_path = f"/{OUTPUT_DIR}/{name}_overlay{ext}"
        image.scored_path = f"/{OUTPUT_DIR}/{name}_scored{ext}"
        image.ideal_path = f"/{OUTPUT_DIR}/{name}_ideal{ext}"
        
        db.session.add(image)
        db.session.flush()  # get id
        
        # Create shot records (mirror Training's safe access)
        for i, shot_data in enumerate(result.get('shots', []) or []):
            # scorer outputs differ slightly across modes; be defensive and follow Training's pattern
            auto_score = shot_data.get('auto_score')
            if auto_score is None:
                auto_score = shot_data.get('score')

            shot = Shot(
                shot_index=shot_data.get('id') or (i + 1),
                center_px=shot_data.get('center_px'),
                dx_mm=shot_data.get('dx_mm') or 0,
                dy_mm=shot_data.get('dy_mm') or 0,
                dist_mm=shot_data.get('dist_mm') or 0,
                bullet_radius_px=shot_data.get('bullet_radius_px') or 0,
                auto_score=auto_score or 0,
                final_score=shot_data.get('final_score', auto_score) if shot_data.get('final_score') is not None else auto_score,
                metadata_json=shot_data,
                image_id=image.id
            )
            db.session.add(shot)
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "image": image.to_dict(),
            "result": result,
            "image_url": "/" + path.replace("\\", "/"),
            "type": image_type
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to process image: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@competition_bp.route('/series/<int:series_id>/images')
def get_series_images(series_id):
    """Get all images for a series."""
    series = Series.query.get_or_404(series_id)
    
    images = []
    for image in series.images:
        image_data = image.to_dict()
        image_data['shots'] = [shot.to_dict() for shot in image.shots]
        images.append(image_data)
    
    return jsonify({"success": True, "images": images})

@competition_bp.route('/competitions/<int:competition_id>/results')
def competition_results(competition_id):
    """Get detailed results for a competition."""
    competition = Competition.query.get_or_404(competition_id)
    
    results = {
        "competition": competition.to_dict(),
        "athletes": []
    }
    
    for comp_athlete in competition.athletes:
        athlete_data = comp_athlete.to_dict()
        
        # Add series details with images
        series_details = []
        for series in comp_athlete.series:
            series_data = series.to_dict()
            
            # Add images with shots
            images_data = []
            for image in series.images:
                image_data = image.to_dict()
                image_data['shots'] = [shot.to_dict() for shot in image.shots]
                images_data.append(image_data)
            
            series_data['images'] = images_data
            series_details.append(series_data)
        
        athlete_data['series'] = series_details
        results["athletes"].append(athlete_data)
    
    return jsonify(results)
