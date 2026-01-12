from flask import Flask, render_template, request, jsonify
import os
import base64
import cv2
import numpy as np
from scorer import score_image
from config import OUTPUT_DIR

app = Flask(__name__)

UPLOAD_DIR = "static/uploads"
SNAPSHOT_DIR = "static/snapshots"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("image")
    if not file:
        return jsonify({"error": "No file"}), 400

    path = os.path.join(UPLOAD_DIR, file.filename)
    file.save(path)

    return jsonify({
        "image_url": "/" + path.replace("\\", "/"),
        "filename": file.filename
    })

@app.route("/snapshot", methods=["POST"])
def snapshot():
    """Обработка снимка с камеры"""
    try:
        data = request.json.get("image")
        if not data:
            return jsonify({"error": "No image data"}), 400
        
        # Remove data URL prefix
        if ',' in data:
            data = data.split(',')[1]
        
        # Decode base64
        img_data = base64.b64decode(data)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return jsonify({"error": "Invalid image data"}), 400
        
        # Generate filename
        import uuid
        filename = f"snapshot_{uuid.uuid4().hex[:8]}.jpg"
        path = os.path.join(SNAPSHOT_DIR, filename)
        
        # Save image
        cv2.imwrite(path, img)
        
        return jsonify({
            "image_url": "/" + path.replace("\\", "/"),
            "filename": filename,
            "type": "snapshot"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/process", methods=["POST"])
def process():
    filename = request.json.get("filename")
    if not filename:
        return jsonify({"error": "No filename"}), 400

    # Check if file is in uploads or snapshots
    upload_path = os.path.join(UPLOAD_DIR, filename)
    snapshot_path = os.path.join(SNAPSHOT_DIR, filename)
    
    if os.path.exists(upload_path):
        path = upload_path
    elif os.path.exists(snapshot_path):
        path = snapshot_path
    else:
        return jsonify({"error": "File not found"}), 404
    
    result = score_image(path)

    name, ext = os.path.splitext(filename)

    return jsonify({
        "stats": {
            "shots": result["shots_count"],
            "total_score": result["total_score"]
        },
        "json": result,
        "images": {
            "scored": f"/{OUTPUT_DIR}/{name}_scored{ext}",
            "ideal": f"/{OUTPUT_DIR}/{name}_ideal{ext}",
            "overlay": f"/{OUTPUT_DIR}/{name}_overlay{ext}",
        }
    })
    
if __name__ == "__main__":
    app.run(debug=True, port=5002)