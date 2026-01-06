from flask import Flask, render_template, request, jsonify
import os
from scorer import score_image
from config import OUTPUT_DIR

app = Flask(__name__)

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

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

@app.route("/process", methods=["POST"])
def process():
    filename = request.json.get("filename")
    if not filename:
        return jsonify({"error": "No filename"}), 400

    path = os.path.join(UPLOAD_DIR, filename)
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
    app.run(debug=True)
