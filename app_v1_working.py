from flask import Flask, request, jsonify
import os
import re
import json
import hashlib
import unicodedata
from werkzeug.utils import secure_filename
from datetime import datetime

BASE_UPLOAD_DIR = "/app/uploads"
DUPLICATES_DIR = os.path.join(BASE_UPLOAD_DIR, "_duplicates")
HASH_INDEX_FILE = os.path.join(BASE_UPLOAD_DIR, "_hash_index.json")

os.makedirs(BASE_UPLOAD_DIR, exist_ok=True)
os.makedirs(DUPLICATES_DIR, exist_ok=True)

app = Flask(__name__)

def load_hash_index():
    if not os.path.exists(HASH_INDEX_FILE):
        return {}
    try:
        with open(HASH_INDEX_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except Exception:
        return {}

def save_hash_index(index):
    with open(HASH_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

def sha256_of_file_storage(file_storage):
    hasher = hashlib.sha256()
    file_storage.stream.seek(0)
    while True:
        chunk = file_storage.stream.read(8192)
        if not chunk:
            break
        hasher.update(chunk)
    file_storage.stream.seek(0)
    return hasher.hexdigest()

def normalize_filename(filename: str) -> str:
    filename = secure_filename(filename)
    if not filename:
        filename = "document"

    if "." in filename:
        base, ext = filename.rsplit(".", 1)
        ext = "." + ext.lower()
    else:
        base, ext = filename, ""

    base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode("ascii")
    base = base.lower()
    base = re.sub(r"[^a-z0-9]+", "-", base)
    base = re.sub(r"-+", "-", base).strip("-")

    if not base:
        base = "document"

    return base + ext

def build_dated_path(base_dir: str) -> str:
    now = datetime.utcnow()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    day = now.strftime("%d")
    path = os.path.join(base_dir, year, month, day)
    os.makedirs(path, exist_ok=True)
    return path

def build_final_filename(original_filename: str, upload_dir: str) -> str:
    cleaned = normalize_filename(original_filename)

    if "." in cleaned:
        base, ext = cleaned.rsplit(".", 1)
        ext = "." + ext
    else:
        base, ext = cleaned, ""

    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    final_name = f"{timestamp}-{base}{ext}"

    counter = 1
    candidate = final_name
    while os.path.exists(os.path.join(upload_dir, candidate)):
        candidate = f"{timestamp}-{base}-{counter}{ext}"
        counter += 1

    return candidate

@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "no file field"}), 400

    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "empty filename"}), 400

    file_hash = sha256_of_file_storage(f)
    hash_index = load_hash_index()

    if file_hash in hash_index:
        duplicate_dir = build_dated_path(DUPLICATES_DIR)
        final_name = build_final_filename(f.filename, duplicate_dir)
        path = os.path.join(duplicate_dir, final_name)
        f.save(path)

        return jsonify({
            "status": "duplicate",
            "filename": final_name,
            "directory": duplicate_dir,
            "original_path": hash_index[file_hash],
            "sha256": file_hash
        }), 200

    upload_dir = build_dated_path(BASE_UPLOAD_DIR)
    final_name = build_final_filename(f.filename, upload_dir)
    path = os.path.join(upload_dir, final_name)
    f.save(path)

    hash_index[file_hash] = path
    save_hash_index(hash_index)

    return jsonify({
        "status": "saved",
        "filename": final_name,
        "directory": upload_dir,
        "sha256": file_hash
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
