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

    # Ensure filesystem structure exists
    upload_dir = "static/uploads"
    snapshot_dir = "static/snapshots"
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(snapshot_dir, exist_ok=True)

    # Create database tables if they do not exist yet
    with app.app_context():
        db.create_all()

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