from flask import Flask, request, jsonify, Response, send_file
import os
import re
import json
import csv
import hashlib
import hmac
import time
import unicodedata
from html import escape
from werkzeug.utils import secure_filename
from datetime import datetime

BASE_UPLOAD_DIR = "/app/uploads"
DUPLICATES_DIR = os.path.join(BASE_UPLOAD_DIR, "_duplicates")
HASH_INDEX_FILE = os.path.join(BASE_UPLOAD_DIR, "_hash_index.json")
LOG_FILE = os.path.join(BASE_UPLOAD_DIR, "_log.csv")
API_KEY = os.getenv("API_KEY", "")

os.makedirs(BASE_UPLOAD_DIR, exist_ok=True)
os.makedirs(DUPLICATES_DIR, exist_ok=True)

app = Flask(__name__)

def make_signed_sig(sha256, expires):
    payload = f"{sha256}:{expires}".encode("utf-8")
    return hmac.new(API_KEY.encode("utf-8"), payload, hashlib.sha256).hexdigest()

def is_valid_signed_url(sha256, expires, sig):
    if not API_KEY:
        return False
    try:
        expires = int(expires)
    except Exception:
        return False

    if expires < int(time.time()):
        return False

    expected = make_signed_sig(sha256, expires)
    return hmac.compare_digest(expected, sig)


def require_api_key():
    provided = request.headers.get("X-API-Key", "")
    return bool(API_KEY) and provided == API_KEY

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

def read_log_rows():
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)

def write_log_rows(rows):
    fieldnames = [
        "timestamp",
        "company",
        "document_type",
        "filename",
        "sha256",
        "status",
        "directory",
        "original_path",
        "pennylane_status",
    ]
    with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            normalized = {k: row.get(k, "") for k in fieldnames}
            writer.writerow(normalized)

def append_log(timestamp_iso, company, document_type, filename, sha256, status, directory, original_path="", pennylane_status=""):
    rows = read_log_rows()

    row = {
        "timestamp": timestamp_iso,
        "company": company,
        "document_type": document_type,
        "filename": filename,
        "sha256": sha256,
        "status": status,
        "directory": directory,
        "original_path": original_path,
        "pennylane_status": pennylane_status,
    }
    rows.append(row)
    write_log_rows(rows)

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

def get_company_from_email(email: str) -> str:
    email = (email or "").lower()

    if "drugoptimal" in email:
        return "drugoptimal"
    if "holding1" in email:
        return "holding1"

    return "default"

def get_document_type(filename: str) -> str:
    name = normalize_filename(filename).lower()

    if "devis" in name or "quotation" in name or "quote" in name:
        return "devis"

    if (
        "facture" in name
        or "invoice" in name
        or "avoir" in name
        or "receipt" in name
        or "recu" in name
        or "cotisation" in name
    ):
        return "facture"

    return "autre"

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

def build_public_path(row):
    directory = row.get("directory", "")
    filename = row.get("filename", "")
    return os.path.join(directory, filename)

def build_anomaly(row):
    status = row.get("status", "")
    pennylane_status = row.get("pennylane_status", "")

    if status == "duplicate":
        return "doublon"
    if status == "saved" and pennylane_status == "":
        return "non traite"
    if status == "saved" and pennylane_status == "pending":
        return "en attente envoi"
    if status == "saved" and pennylane_status == "error":
        return "erreur pennylane"
    return ""

def make_signed_sig(sha256, expires):
    payload = f"{sha256}:{expires}".encode("utf-8")
    return hmac.new(API_KEY.encode("utf-8"), payload, hashlib.sha256).hexdigest()

def build_signed_download_url(sha256):
    expires = int(time.time()) + 86400
    sig = make_signed_sig(sha256, expires)
    return f"https://factures.drugoptimal.com/download-signed/{sha256}?expires={expires}&sig={sig}"


def is_anomaly_row(row):
    return build_anomaly(row) != ""



@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}


@app.route("/beatrice", methods=["GET"])
def beatrice():
    rows = read_log_rows()[-300:][::-1]

    html_rows = []
    for row in rows:
        timestamp = escape(row.get("timestamp", ""))
        company = escape(row.get("company", ""))
        document_type = escape(row.get("document_type", ""))
        status = escape(row.get("status", ""))
        pennylane_status = escape(row.get("pennylane_status", ""))
        filename = escape(row.get("filename", ""))
        anomaly = escape(build_anomaly(row))
        sha256 = row.get("sha256", "")

        download_link = ""
        if sha256 and row.get("status") == "saved":
            url = build_signed_download_url(sha256)
            download_link = f'<a href="{escape(url)}" target="_blank">Télécharger</a>'

        html_rows.append(f"""
        <tr>
            <td>{timestamp}</td>
            <td>{company}</td>
            <td>{document_type}</td>
            <td>{status}</td>
            <td>{pennylane_status}</td>
            <td>{anomaly}</td>
            <td>{filename}</td>
            <td>{download_link}</td>
        </tr>
        """)

    body = "".join(html_rows) if html_rows else """
    <tr>
        <td colspan="8">Aucun document pour le moment.</td>
    </tr>
    """

    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <title>Béatrice</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 24px;
                background: #f7f7f7;
                color: #222;
            }}
            h1 {{
                margin-bottom: 8px;
            }}
            .meta {{
                margin-bottom: 20px;
                color: #555;
            }}
            .actions {{
                margin-bottom: 20px;
            }}
            .button {{
                display: inline-block;
                padding: 10px 14px;
                background: #e9ecef;
                color: #222;
                border: 1px solid #ccc;
                border-radius: 6px;
                text-decoration: none;
                margin-right: 8px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 10px;
                text-align: left;
                font-size: 14px;
                vertical-align: top;
            }}
            th {{
                background: #f0f0f0;
            }}
            tr:nth-child(even) {{
                background: #fafafa;
            }}
            a {{
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        <h1>Béatrice</h1>
        <div class="meta">300 derniers documents du pipeline</div>
        <div class="actions">
            <a class="button" href="/beatrice/anomalies">Voir les anomalies</a>
            <a class="button" href="/dashboard">Dashboard technique</a>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Timestamp</th>
                    <th>Société</th>
                    <th>Type</th>
                    <th>Statut</th>
                    <th>Pennylane</th>
                    <th>Anomalie</th>
                    <th>Fichier</th>
                    <th>PDF</th>
                </tr>
            </thead>
            <tbody>
                {body}
            </tbody>
        </table>
    </body>
    </html>
    """
    return Response(html, mimetype="text/html")



@app.route("/beatrice/anomalies", methods=["GET"])
def beatrice_anomalies():
    rows = read_log_rows()[::-1]
    rows = [row for row in rows if is_anomaly_row(row)]
    rows = rows[:300]

    html_rows = []
    for row in rows:
        timestamp = escape(row.get("timestamp", ""))
        company = escape(row.get("company", ""))
        document_type = escape(row.get("document_type", ""))
        status = escape(row.get("status", ""))
        pennylane_status = escape(row.get("pennylane_status", ""))
        filename = escape(row.get("filename", ""))
        anomaly = escape(build_anomaly(row))
        sha256 = row.get("sha256", "")

        download_link = ""
        if sha256 and row.get("status") == "saved":
            url = build_signed_download_url(sha256)
            download_link = f'<a href="{escape(url)}" target="_blank">Télécharger</a>'

        html_rows.append(f"""
        <tr>
            <td>{timestamp}</td>
            <td>{company}</td>
            <td>{document_type}</td>
            <td>{status}</td>
            <td>{pennylane_status}</td>
            <td>{anomaly}</td>
            <td>{filename}</td>
            <td>{download_link}</td>
        </tr>
        """)

    body = "".join(html_rows) if html_rows else """
    <tr>
        <td colspan="8">Aucune anomalie pour le moment.</td>
    </tr>
    """

    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <title>Béatrice — Anomalies</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 24px;
                background: #f7f7f7;
                color: #222;
            }}
            h1 {{
                margin-bottom: 8px;
            }}
            .meta {{
                margin-bottom: 20px;
                color: #555;
            }}
            .actions {{
                margin-bottom: 20px;
            }}
            .button {{
                display: inline-block;
                padding: 10px 14px;
                background: #e9ecef;
                color: #222;
                border: 1px solid #ccc;
                border-radius: 6px;
                text-decoration: none;
                margin-right: 8px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 10px;
                text-align: left;
                font-size: 14px;
                vertical-align: top;
            }}
            th {{
                background: #f0f0f0;
            }}
            tr:nth-child(even) {{
                background: #fafafa;
            }}
            a {{
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        <h1>Béatrice — Anomalies</h1>
        <div class="meta">300 dernières anomalies détectées</div>
        <div class="actions">
            <a class="button" href="/beatrice">Vue complète</a>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Timestamp</th>
                    <th>Société</th>
                    <th>Type</th>
                    <th>Statut</th>
                    <th>Pennylane</th>
                    <th>Anomalie</th>
                    <th>Fichier</th>
                    <th>PDF</th>
                </tr>
            </thead>
            <tbody>
                {body}
            </tbody>
        </table>
    </body>
    </html>
    """
    return Response(html, mimetype="text/html")


@app.route("/dashboard", methods=["GET"])
def dashboard():
    rows = read_log_rows()[-200:][::-1]

    html_rows = []
    for row in rows:
        status = escape(row.get("status", ""))
        company = escape(row.get("company", ""))
        document_type = escape(row.get("document_type", ""))
        filename = escape(row.get("filename", ""))
        timestamp = escape(row.get("timestamp", ""))
        directory = escape(row.get("directory", ""))
        pennylane_status = escape(row.get("pennylane_status", ""))

        html_rows.append(f"""
        <tr>
            <td>{timestamp}</td>
            <td>{company}</td>
            <td>{document_type}</td>
            <td>{status}</td>
            <td>{pennylane_status}</td>
            <td>{filename}</td>
            <td>{directory}</td>
        </tr>
        """)

    body = "".join(html_rows) if html_rows else """
    <tr>
        <td colspan="7">Aucun document pour le moment.</td>
    </tr>
    """

    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <title>Dashboard factures</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 24px;
                background: #f7f7f7;
                color: #222;
            }}
            h1 {{
                margin-bottom: 8px;
            }}
            .meta {{
                margin-bottom: 20px;
                color: #555;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 10px;
                text-align: left;
                font-size: 14px;
                vertical-align: top;
            }}
            th {{
                background: #f0f0f0;
            }}
            tr:nth-child(even) {{
                background: #fafafa;
            }}
        </style>
    </head>
    <body>
        <h1>Dashboard factures</h1>
        <div class="meta">200 derniers événements</div>
        <table>
            <thead>
                <tr>
                    <th>Timestamp</th>
                    <th>Société</th>
                    <th>Type</th>
                    <th>Statut</th>
                    <th>Pennylane</th>
                    <th>Fichier</th>
                    <th>Dossier</th>
                </tr>
            </thead>
            <tbody>
                {body}
            </tbody>
        </table>
    </body>
    </html>
    """
    return Response(html, mimetype="text/html")


@app.route("/download-signed/<sha256>", methods=["GET"])
def download_signed(sha256):
    expires = request.args.get("expires", "")
    sig = request.args.get("sig", "")

    if not is_valid_signed_url(sha256, expires, sig):
        return jsonify({"error": "invalid or expired signed url"}), 401

    rows = read_log_rows()

    for row in rows:
        if row.get("sha256") == sha256 and row.get("status") == "saved":
            directory = row.get("directory", "")
            filename = row.get("filename", "")
            full_path = os.path.join(directory, filename)

            if not os.path.exists(full_path):
                return jsonify({"error": "file not found on disk"}), 404

            if filename.lower().endswith(".pdf"):
                return send_file(
                    full_path,
                    as_attachment=True,
                    download_name=filename,
                    mimetype="application/pdf"
                )

            return send_file(
                full_path,
                as_attachment=True,
                download_name=filename
            )

    return jsonify({"error": "document not found"}), 404

@app.route("/download-by-sha/<sha256>", methods=["GET"])
def download_by_sha(sha256):
    if not require_api_key():
        return jsonify({"error": "unauthorized"}), 401

    rows = read_log_rows()

    for row in rows:
        if row.get("sha256") == sha256 and row.get("status") == "saved":
            directory = row.get("directory", "")
            filename = row.get("filename", "")
            full_path = os.path.join(directory, filename)

            if not os.path.exists(full_path):
                return jsonify({"error": "file not found on disk"}), 404

            if filename.lower().endswith(".pdf"):
                return send_file(
                    full_path,
                    as_attachment=True,
                    download_name=filename,
                    mimetype="application/pdf"
                )

            return send_file(
                full_path,
                as_attachment=True,
                download_name=filename
            )

    return jsonify({"error": "document not found"}), 404

@app.route("/pennylane-pending", methods=["GET"])
def pennylane_pending():
    if not require_api_key():
        return jsonify({"error": "unauthorized"}), 401

    company_filter = request.args.get("company", "").strip().lower()
    limit = request.args.get("limit", "50").strip()

    try:
        limit = max(1, min(int(limit), 500))
    except Exception:
        limit = 50

    rows = read_log_rows()

    pending = []
    seen_sha = set()

    for row in rows:
        if row.get("document_type") != "facture":
            continue
        if row.get("status") != "saved":
            continue
        if row.get("pennylane_status") not in ("", "pending"):
            continue

        company = row.get("company", "").lower()
        if company_filter and company != company_filter:
            continue

        sha = row.get("sha256", "")
        if not sha or sha in seen_sha:
            continue

        seen_sha.add(sha)
        pending.append({
            "timestamp": row.get("timestamp", ""),
            "company": row.get("company", ""),
            "document_type": row.get("document_type", ""),
            "filename": row.get("filename", ""),
            "sha256": sha,
            "status": row.get("status", ""),
            "pennylane_status": row.get("pennylane_status", "pending") or "pending",
            "directory": row.get("directory", ""),
            "path": build_public_path(row),
            "download_url": f"https://factures.drugoptimal.com/download-by-sha/{sha}",
        })

    pending = pending[:limit]
    return jsonify({
        "count": len(pending),
        "items": pending
    })

@app.route("/pennylane-mark-sent", methods=["POST"])
def pennylane_mark_sent():
    if not require_api_key():
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    sha256 = (data.get("sha256") or "").strip()

    if not sha256:
        return jsonify({"error": "sha256 is required"}), 400

    rows = read_log_rows()
    updated = 0

    for row in rows:
        if row.get("sha256") == sha256 and row.get("status") == "saved":
            row["pennylane_status"] = "sent"
            updated += 1

    if updated == 0:
        return jsonify({"error": "no matching saved document found"}), 404

    write_log_rows(rows)

    return jsonify({
        "status": "ok",
        "updated": updated,
        "sha256": sha256
    })

@app.route("/pennylane-mark-error", methods=["POST"])
def pennylane_mark_error():
    if not require_api_key():
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    sha256 = (data.get("sha256") or "").strip()

    if not sha256:
        return jsonify({"error": "sha256 is required"}), 400

    rows = read_log_rows()
    updated = 0

    for row in rows:
        if row.get("sha256") == sha256 and row.get("status") == "saved":
            row["pennylane_status"] = "error"
            updated += 1

    if updated == 0:
        return jsonify({"error": "no matching saved document found"}), 404

    write_log_rows(rows)

    return jsonify({
        "status": "ok",
        "updated": updated,
        "sha256": sha256
    })

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "no file field"}), 400

    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "empty filename"}), 400

    recipient_email = request.form.get("recipient_email", "default")
    company = get_company_from_email(recipient_email)
    document_type = get_document_type(f.filename)
    timestamp_iso = datetime.utcnow().isoformat()

    file_hash = sha256_of_file_storage(f)
    hash_index = load_hash_index()

    if file_hash in hash_index:
        company_dup_base = os.path.join(DUPLICATES_DIR, company, document_type)
        duplicate_dir = build_dated_path(company_dup_base)
        final_name = build_final_filename(f.filename, duplicate_dir)
        path = os.path.join(duplicate_dir, final_name)
        f.save(path)

        append_log(
            timestamp_iso=timestamp_iso,
            company=company,
            document_type=document_type,
            filename=final_name,
            sha256=file_hash,
            status="duplicate",
            directory=duplicate_dir,
            original_path=hash_index[file_hash],
            pennylane_status=""
        )

        return jsonify({
            "status": "duplicate",
            "filename": final_name,
            "directory": duplicate_dir,
            "sha256": file_hash,
            "company": company,
            "document_type": document_type,
            "original_path": hash_index[file_hash]
        }), 200

    company_base = os.path.join(BASE_UPLOAD_DIR, company, document_type)
    upload_dir = build_dated_path(company_base)
    final_name = build_final_filename(f.filename, upload_dir)
    path = os.path.join(upload_dir, final_name)
    f.save(path)

    hash_index[file_hash] = path
    save_hash_index(hash_index)

    pennylane_status = "pending" if document_type == "facture" else ""

    append_log(
        timestamp_iso=timestamp_iso,
        company=company,
        document_type=document_type,
        filename=final_name,
        sha256=file_hash,
        status="saved",
        directory=upload_dir,
        original_path="",
        pennylane_status=pennylane_status
    )

    return jsonify({
        "status": "saved",
        "filename": final_name,
        "directory": upload_dir,
        "sha256": file_hash,
        "company": company,
        "document_type": document_type,
        "pennylane_status": pennylane_status
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
