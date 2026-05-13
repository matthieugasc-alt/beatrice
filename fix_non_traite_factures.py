import csv
import os
import pdfplumber

LOG = "/opt/factures-v1/uploads/_log.csv"

def fix_path(path):
    if path.startswith("/app/uploads"):
        return path.replace("/app/uploads", "/opt/factures-v1/uploads")
    return path

def extract_text(path):
    text = ""
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except Exception:
        return ""
    return text.lower()

def is_real_invoice(text):
    return (
        "facture" in text
        or "invoice" in text
        or "n° de facture" in text
        or "numero de facture" in text
        or "numéro de facture" in text
        or "total ttc" in text
        or "montant ttc" in text
        or "tva" in text
    )

def main():
    with open(LOG, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        fieldnames = rows[0].keys()

    updated = 0

    for row in rows:
        if row.get("document_type") == "facture":
            continue

        path = row.get("original_path") or (row.get("directory", "") + "/" + row.get("filename", ""))
        path = fix_path(path)

        if not os.path.exists(path):
            continue

        text = extract_text(path)
        if not text:
            continue

        if not is_real_invoice(text):
            continue

        row["document_type"] = "facture"
        row["pennylane_status"] = "pending"
        updated += 1

    with open(LOG, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Corrigé : {updated} factures")

if __name__ == "__main__":
    main()
