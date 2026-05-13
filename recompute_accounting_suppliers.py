import csv
import os
import re
import unicodedata

LOG_FILE = "/opt/factures-v1/uploads/_log.csv"

def normalize_filename(filename: str) -> str:
    filename = filename or "document"

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

def get_accounting_supplier(filename: str, document_type: str) -> str:
    name = normalize_filename(filename).lower()

    # SaaS / fournisseurs individuels
    if "stripe" in name:
        return "Stripe"
    if "openai" in name or "chatgpt" in name:
        return "OpenAI"
    if "aws" in name or "amazon-web-services" in name:
        return "AWS"
    if "ovh" in name:
        return "OVH"
    if "notion" in name:
        return "Notion"

    # Conteneurs métier
    if any(x in name for x in ["airbnb", "booking", "hotel", "hotels", "bnb"]):
        return "Hotel"

    if any(x in name for x in ["vinci", "area", "peage", "parking", "autoroute", "autoroutes"]):
        return "Peage"

    if any(x in name for x in ["uber", "bolt", "easyjet", "sncf", "train", "flight", "avion", "taxi"]):
        return "Transport"

    if any(x in name for x in ["restaurant", "resto", "diner", "lunch", "dejeuner", "dinner", "food"]):
        return "Restaurant"

    if document_type == "facture":
        return "Autre"

    if document_type == "justificatif":
        return "Justificatif"

    if document_type == "devis":
        return "Devis"

    return "Autre"

def main():
    if not os.path.exists(LOG_FILE):
        raise SystemExit("Log file not found")

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    if "accounting_supplier" not in fieldnames:
        fieldnames.append("accounting_supplier")

    updated = 0

    for row in rows:
        filename = row.get("filename", "")
        document_type = row.get("document_type", "")
        new_value = get_accounting_supplier(filename, document_type)

        if row.get("accounting_supplier", "") != new_value:
            row["accounting_supplier"] = new_value
            updated += 1

    with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Recompute done. {updated} rows updated.")

if __name__ == "__main__":
    main()
