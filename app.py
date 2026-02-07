from flask import Flask, render_template, request, jsonify
import os
import base64
import cv2
import numpy as np
from scorer import score_image
from config import OUTPUT_DIR
from models import db
from management import management_bp


def create_app() -> Flask:
    """Application factory to configure Flask, database and blueprints."""
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///shooting.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = "change-me-in-production"

    # Initialise extensions
    db.init_app(app)

    # Register blueprints
    app.register_blueprint(management_bp, url_prefix="/management")

    # Competition blueprint
    try:
        from competition import competition_bp
        app.register_blueprint(competition_bp, url_prefix="/competition")
    except Exception:
        # Keep app import-safe even if competition module has issues
        pass

    # Training blueprint (separate UI and APIs for training mode)
    try:
        from training import training_bp
        app.register_blueprint(training_bp, url_prefix="/training")
    except Exception:
        # Keep app import-safe even if training module has issues
        pass

    # Analytics blueprint
    try:
        from analytics import analytics_bp
        app.register_blueprint(analytics_bp, url_prefix="/analytics")
    except Exception:
        # Keep app import-safe even if analytics module has issues
        pass

    # Ensure filesystem structure exists
    upload_dir = "static/uploads"
    snapshot_dir = "static/snapshots"
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(snapshot_dir, exist_ok=True)

    # Create database tables if they do not exist yet
    with app.app_context():
        db.create_all()

        # Lightweight migration: add missing columns to existing tables when necessary.
        # This keeps local deployments working without Alembic while being safe (no-op if columns exist).
        try:
            from sqlalchemy import text

            with db.engine.begin() as conn:
                def cols_for(tbl: str) -> set:
                    res = conn.execute(text(f"PRAGMA table_info('{tbl}')")).mappings().all()
                    return {r['name'] for r in res} if res else set()

                # Shots: ensure all expected columns exist. Handle legacy `idx` column name.
                shots_expected = [
                    ("idx", "INTEGER DEFAULT 0"),
                    ("center_px", "JSON"),
                    ("dx_mm", "REAL DEFAULT 0"),
                    ("dy_mm", "REAL DEFAULT 0"),
                    ("dist_mm", "REAL DEFAULT 0"),
                    ("bullet_radius_px", "REAL DEFAULT 0"),
                    ("auto_score", "INTEGER DEFAULT 0"),
                    ("final_score", "INTEGER"),
                    ("metadata_json", "JSON"),
                    ("created_at", "DATETIME")
                ]

                existing = cols_for('shots')
                if existing:
                    # If `idx` is missing but `shot_index` exists, create `idx` and copy values
                    if 'idx' not in existing and 'shot_index' in existing:
                        conn.execute(text("ALTER TABLE shots ADD COLUMN idx INTEGER DEFAULT 0"))
                        conn.execute(text("UPDATE shots SET idx = shot_index WHERE idx IS NULL"))
                        existing.add('idx')

                    for name, ctype in shots_expected:
                        if name not in existing:
                            conn.execute(text(f"ALTER TABLE shots ADD COLUMN {name} {ctype}"))
                    # Ensure 'idx' has a default for future inserts
                    if 'idx' in existing:
                        try:
                            conn.execute(text("UPDATE shots SET idx = 0 WHERE idx IS NULL"))
                        except Exception:
                            pass

                # Images: add overlay/scored/ideal paths and created_at & athlete_id if missing
                images_expected = [
                    ("overlay_path", "TEXT"),
                    ("scored_path", "TEXT"),
                    ("ideal_path", "TEXT"),
                    ("created_at", "DATETIME"),
                    ("athlete_id", "INTEGER")
                ]
                existing = cols_for('images')
                if existing:
                    for name, ctype in images_expected:
                        if name not in existing:
                            conn.execute(text(f"ALTER TABLE images ADD COLUMN {name} {ctype}"))

                # Sessions: add mode, started_at, finished_at, name if missing
                sessions_expected = [
                    ("mode", "TEXT DEFAULT 'training'"),
                    ("started_at", "DATETIME"),
                    ("finished_at", "DATETIME"),
                    ("name", "TEXT")
                ]
                existing = cols_for('sessions')
                if existing:
                    for name, ctype in sessions_expected:
                        if name not in existing:
                            conn.execute(text(f"ALTER TABLE sessions ADD COLUMN {name} {ctype}"))

                # Shot revisions: ensure audit fields exist
                rev_expected = [
                    ("prev_score", "INTEGER DEFAULT 0"),
                    ("new_score", "INTEGER DEFAULT 0"),
                    ("note", "TEXT"),
                    ("changed_at", "DATETIME")
                ]
                existing = cols_for('shot_revisions')
                if existing:
                    for name, ctype in rev_expected:
                        if name not in existing:
                            conn.execute(text(f"ALTER TABLE shot_revisions ADD COLUMN {name} {ctype}"))

                # Competition mode tables
                exercises_expected = [
                    ("id", "INTEGER PRIMARY KEY"),
                    ("name", "VARCHAR(100) NOT NULL"),
                    ("description", "TEXT"),
                    ("total_series", "INTEGER NOT NULL"),
                    ("shots_per_series", "INTEGER NOT NULL"),
                    ("timing_type", "VARCHAR(20) NOT NULL DEFAULT 'fixed'"),
                    ("is_system", "BOOLEAN NOT NULL DEFAULT 0"),
                    ("created_at", "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP")
                ]
                
                # Create exercises table if it doesn't exist
                if not conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='exercises'")).scalar():
                    columns = ", ".join([f"{name} {ctype}" for name, ctype in exercises_expected])
                    conn.execute(text(f"CREATE TABLE exercises ({columns})"))

                competitions_expected = [
                    ("id", "INTEGER PRIMARY KEY"),
                    ("name", "VARCHAR(200) NOT NULL"),
                    ("status", "VARCHAR(20) NOT NULL DEFAULT 'draft'"),
                    ("started_at", "DATETIME"),
                    ("finished_at", "DATETIME"),
                    ("created_at", "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"),
                    ("exercise_id", "INTEGER NOT NULL REFERENCES exercises(id)")
                ]
                
                if not conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='competitions'")).scalar():
                    columns = ", ".join([f"{name} {ctype}" for name, ctype in competitions_expected])
                    conn.execute(text(f"CREATE TABLE competitions ({columns})"))

                competition_athletes_expected = [
                    ("id", "INTEGER PRIMARY KEY"),
                    ("competition_id", "INTEGER NOT NULL REFERENCES competitions(id)"),
                    ("athlete_id", "INTEGER NOT NULL REFERENCES athletes(id)")
                ]
                
                if not conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='competition_athletes'")).scalar():
                    columns = ", ".join([f"{name} {ctype}" for name, ctype in competition_athletes_expected])
                    conn.execute(text(f"CREATE TABLE competition_athletes ({columns})"))

                series_expected = [
                    ("id", "INTEGER PRIMARY KEY"),
                    ("series_number", "INTEGER NOT NULL"),
                    ("status", "VARCHAR(20) NOT NULL DEFAULT 'active'"),
                    ("started_at", "DATETIME"),
                    ("finished_at", "DATETIME"),
                    ("created_at", "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"),
                    ("competition_athlete_id", "INTEGER NOT NULL REFERENCES competition_athletes(id)"),
                    ("session_id", "INTEGER NOT NULL REFERENCES sessions(id)")
                ]
                
                if not conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='series'")).scalar():
                    columns = ", ".join([f"{name} {ctype}" for name, ctype in series_expected])
                    conn.execute(text(f"CREATE TABLE series ({columns})"))

                # Add series_id to images table if missing
                images_existing = cols_for('images')
                if images_existing and 'series_id' not in images_existing:
                    conn.execute(text("ALTER TABLE images ADD COLUMN series_id INTEGER REFERENCES series(id)"))

                # Add session_id to series table if missing
                series_existing = cols_for('series')
                if series_existing and 'session_id' not in series_existing:
                    from datetime import datetime
                    
                    conn.execute(text("ALTER TABLE series ADD COLUMN session_id INTEGER NOT NULL DEFAULT 0"))
                    # For existing series without sessions, create competition sessions
                    existing_series = conn.execute(text("SELECT id, competition_athlete_id FROM series WHERE session_id = 0")).fetchall()
                    for series_id, comp_athlete_id in existing_series:
                        # Get competition info
                        comp_info = conn.execute(text("""
                            SELECT c.name, c.created_at
                            FROM competition_athletes ca
                            JOIN competitions c ON ca.competition_id = c.id
                            WHERE ca.id = :comp_athlete_id
                        """), {"comp_athlete_id": comp_athlete_id}).fetchone()
                        
                        if comp_info:
                            # Create session for existing series
                            session_result = conn.execute(text("""
                                INSERT INTO sessions (mode, name, started_at, finished_at)
                                VALUES ('competition', :name, :started_at, NULL)
                                RETURNING id
                            """), {
                                "name": f"Competition: {comp_info.name}",
                                "started_at": comp_info.created_at or datetime.utcnow()
                            })
                            session_id = session_result.scalar_one()
                            conn.execute(text("UPDATE series SET session_id = :session_id WHERE id = :series_id"), 
                                       {"session_id": session_id, "series_id": series_id})
        except Exception:
            # Avoid crashing the app if migration fails; manual migration may be required in production.
            pass

    # Routes for scoring functionality remain attached to this app instance

    @app.route("/")
    def index():
        return render_template("index.html")


    @app.route("/upload", methods=["POST"])
    def upload():
        file = request.files.get("image")
        if not file:
            return jsonify({"error": "No file"}), 400

        path = os.path.join(upload_dir, file.filename)
        file.save(path)

        return jsonify(
            {
                "image_url": "/" + path.replace("\\", "/"),
                "filename": file.filename,
            }
        )

    @app.route("/snapshot", methods=["POST"])
    def snapshot():
        """Handle snapshot from camera (base64 image)."""
        try:
            data = request.json.get("image")
            if not data:
                return jsonify({"error": "No image data"}), 400

            # Remove data URL prefix
            if "," in data:
                data = data.split(",")[1]

            # Decode base64
            img_data = base64.b64decode(data)
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img is None:
                return jsonify({"error": "Invalid image data"}), 400

            # Generate filename
            import uuid

            filename = f"snapshot_{uuid.uuid4().hex[:8]}.jpg"
            path = os.path.join(snapshot_dir, filename)

            # Save image
            cv2.imwrite(path, img)

            return jsonify(
                {
                    "image_url": "/" + path.replace("\\", "/"),
                    "filename": filename,
                    "type": "snapshot",
                }
            )
        except Exception as e:  # pragma: no cover - defensive
            return jsonify({"error": str(e)}), 500

    @app.route("/process", methods=["POST"])
    def process():
        filename = request.json.get("filename")
        if not filename:
            return jsonify({"error": "No filename"}), 400

        # Check if file is in uploads or snapshots
        upload_path = os.path.join(upload_dir, filename)
        snapshot_path = os.path.join(snapshot_dir, filename)

        if os.path.exists(upload_path):
            path = upload_path
        elif os.path.exists(snapshot_path):
            path = snapshot_path
        else:
            return jsonify({"error": "File not found"}), 404

        result = score_image(path)

        name, ext = os.path.splitext(filename)

        return jsonify(
            {
                "stats": {
                    "shots": result["shots_count"],
                    "total_score": result["total_score"],
                },
                "json": result,
                "images": {
                    "scored": f"/{OUTPUT_DIR}/{name}_scored{ext}",
                    "ideal": f"/{OUTPUT_DIR}/{name}_ideal{ext}",
                    "overlay": f"/{OUTPUT_DIR}/{name}_overlay{ext}",
                },
            }
        )

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(debug=True, port=5002)
