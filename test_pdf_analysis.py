import pdfplumber

def analyze_pdf(path):
    text = ""

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""

    text_lower = text.lower()
    # Extraction fournisseur (ligne haute)
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    supplier_detected = lines[0] if lines else "Inconnu"
    supplier_clean = supplier_detected

    prefixes = ["SARL ", "SAS ", "SASU ", "EURL ", "SCI ", "SA ", "SELPARL ", "SELARL "]

    for prefix in prefixes:
        if supplier_clean.upper().startswith(prefix):
            supplier_clean = supplier_clean[len(prefix):]
            break

    print("Fournisseur détecté (brut):", supplier_detected)
    print("Fournisseur détecté (clean):", supplier_clean)
    # DEBUG : afficher début du document
    print("\n--- TEXTE EXTRAIT (début) ---")
    print(text[:500])
    print("-----------------------------\n")

    # Détection type
    score_facture = sum([
        "facture" in text_lower,
        "invoice" in text_lower,
        "total" in text_lower,
        "tva" in text_lower,
        "amount" in text_lower,
    ])

    if score_facture >= 2:
        doc_type = "facture"
    elif "receipt" in text_lower or "recu" in text_lower:
        doc_type = "justificatif"
    elif "devis" in text_lower or "quote" in text_lower:
        doc_type = "devis"
    else:
        doc_type = "autre"

       # Détection catégorie comptable
    score_hotel = sum([
        "hotel" in text_lower,
        "chambre" in text_lower,
        "nuit" in text_lower,
        "sejour" in text_lower,
        "séjour" in text_lower,
        "reservation" in text_lower,
        "check-in" in text_lower,
        "check-out" in text_lower,
        "taxe de sejour" in text_lower,
        "taxe de séjour" in text_lower,
        "hebergement" in text_lower,
        "hébergement" in text_lower,
    ])

    score_peage = sum([
        "peage" in text_lower,
        "péage" in text_lower,
        "autoroute" in text_lower,
        "parking" in text_lower,
        "stationnement" in text_lower,
        "ticket" in text_lower,
        "sortie" in text_lower,
        "entree" in text_lower,
        "entrée" in text_lower,
        "plaque" in text_lower,
        "vinci" in text_lower,
        "area" in text_lower,
    ])

    score_transport = sum([
        "trajet" in text_lower,
        "voyage" in text_lower,
        "billet" in text_lower,
        "train" in text_lower,
        "avion" in text_lower,
        "taxi" in text_lower,
        "ride" in text_lower,
        "trip" in text_lower,
        "departure" in text_lower,
        "arrival" in text_lower,
        "sncf" in text_lower,
        "uber" in text_lower,
        "easyjet" in text_lower,
        "bolt" in text_lower,
    ])

    score_restaurant = sum([
        "restaurant" in text_lower,
        "repas" in text_lower,
        "dejeuner" in text_lower,
        "déjeuner" in text_lower,
        "diner" in text_lower,
        "dîner" in text_lower,
        "lunch" in text_lower,
        "dinner" in text_lower,
        "menu" in text_lower,
        "couverts" in text_lower,
        "food" in text_lower,
    ])

    category_scores = {
        "Hotel": score_hotel,
        "Peage": score_peage,
        "Transport": score_transport,
        "Restaurant": score_restaurant,
    }

    best_category = max(category_scores, key=category_scores.get)
    best_score = category_scores[best_category]

    if best_score >= 2:
        accounting_category = best_category
    else:
        accounting_category = "Autre"

    # Score confiance
    if score_facture >= 3:
        confidence = "élevé"
    elif score_facture == 2:
        confidence = "moyen"
    else:
        confidence = "faible"

    print("----- RESULT -----")
    print("Type:", doc_type)
    print("Fournisseur réel (clean):", supplier_clean)
    print("Categorie comptable:", accounting_category)
    print("Confiance:", confidence)
    print("------------------")


if __name__ == "__main__":
    path = input("Chemin du PDF: ")
    analyze_pdf(path)
