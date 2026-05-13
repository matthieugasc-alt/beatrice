import csv
import os
from app import analyze_pdf_content

LOG_FILE = "/opt/factures-v1/uploads/_log.csv"

def build_file_path(row):
    directory = row.get("directory", "")
    filename = row.get("filename", "")
    path = os.path.join(directory, filename)

    # FIX: convertir chemin Docker → chemin hôte
    if path.startswith("/app/uploads"):
        path = path.replace("/app/uploads", "/opt/factures-v1/uploads")

    return path

def main():
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    updated = 0

    for row in rows:
        path = build_file_path(row)

        if not os.path.exists(path):
            continue

        try:
            supplier, category = analyze_pdf_content(path)
        except Exception:
            continue

        if row.get("accounting_supplier") != category:
            row["accounting_supplier"] = category
            updated += 1

    with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Recompute terminé : {updated} lignes mises à jour")

if __name__ == "__main__":
    main()

