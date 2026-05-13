import csv
import os
import hmac
import time
import hashlib

LOG_FILE = "/opt/factures-v1/uploads/_log.csv"
OUTPUT_FILE = "/opt/factures-v1/beatrice_output.csv"
API_KEY = ""

with open("/opt/factures-v1/.env", "r", encoding="utf-8") as f:
    for line in f:
        if line.startswith("API_KEY="):
            API_KEY = line.strip().split("=", 1)[1]

def make_signed_sig(sha256, expires):
    payload = f"{sha256}:{expires}".encode("utf-8")
    return hmac.new(API_KEY.encode("utf-8"), payload, hashlib.sha256).hexdigest()

rows = []

with open(LOG_FILE, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for r in reader:
        anomaly = ""

        if r["status"] == "saved" and r["pennylane_status"] == "":
            anomaly = "non traite"

        if r["status"] == "saved" and r["pennylane_status"] == "pending":
            anomaly = "en attente envoi"

        if r["status"] == "duplicate":
            anomaly = "doublon"

        expires = int(time.time()) + 86400
        sig = make_signed_sig(r["sha256"], expires)
        download_url = f"https://factures.drugoptimal.com/download-signed/{r['sha256']}?expires={expires}&sig={sig}"

        rows.append({
            "timestamp": r["timestamp"],
            "filename": r["filename"],
            "company": r["company"],
            "document_type": r["document_type"],
            "status": r["status"],
            "pennylane_status": r["pennylane_status"],
            "anomaly": anomaly,
            "sha256": r["sha256"],
            "download_url": download_url
        })

rows = sorted(rows, key=lambda x: x["timestamp"], reverse=True)

with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print(f"CSV generated: {OUTPUT_FILE}")
print(f"{len(rows)} rows exported")
