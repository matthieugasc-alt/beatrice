# beatrice

API Flask d'ingestion et de stockage de factures (PDF) avec déduplication, classification automatique et journal d'audit. Composant **Beatrice** = couche de classification post-upload (anomalies, filtres, dashboard).

Tourne en production sur `serveur1` sous Docker, exposée derrière un reverse proxy. Le déploiement sur le serveur (`/opt/factures-v1/`) est un checkout de ce repo + un dossier `uploads/` persistant.

---

## Vue d'ensemble

Pipeline pour une facture entrante :

```
POST /upload (X-API-Key)
  ↓
  calcul SHA-256
    ↓
    check _hash_index.json     ── déjà vu ? → _duplicates/
      ↓
      classification automatique :
        • company           ← extraite de l'email expéditeur
          • document_type     ← extrait du nom de fichier (facture / devis / justificatif)
            • accounting_supplier ← mapping du nom de fichier (Stripe, OpenAI, AWS…)
              ↓
              écriture dans /app/uploads/{company}/{document_type}/{supplier}/
                ↓
                journal _log.csv + index _hash_index.json
                ```

                Lien partageable signé : HMAC-SHA256 sur `{sha256}:{expires}`, vérification temps-constant. URLs expirent.

                ---

                ## Stack

                - Python 3.12 / Flask
                - `pdfplumber` pour l'analyse PDF
                - Docker (image basée sur python:3.12-slim)
                - Stockage : système de fichiers + CSV/JSON (pas de SGBD)

                ---

                ## Installation locale (dev)

                ```bash
                python3 -m venv venv
                source venv/bin/activate
                pip install -r requirements.txt
                cp .env.example .env       # puis remplir API_KEY
                python app.py
                ```

                ## Production (Docker)

                ```bash
                docker build -t factures-v1 .
                docker run -d \
                  --name factures-v1 \
                    --restart unless-stopped \
                      -p 9000:8080 \
                        -v /opt/factures-v1/uploads:/app/uploads \
                          --env-file /opt/factures-v1/.env \
                            factures-v1
                            ```

                            ---

                            ## Variables d'environnement

                            Voir `.env.example` pour la liste complète. Principales :

                            - `API_KEY` (obligatoire) — clé X-API-Key pour upload + signature HMAC des URLs
                            - `PORT` (8080)
                            - `FLASK_ENV=production` en prod
                            - `PENNYLANE_API_TOKEN` (optionnel)

                            ---

                            ## API

                            ### `POST /upload`
                            Headers : `X-API-Key`. Body : multipart avec `file` (PDF) + `email` optionnel.
                            Réponse : `{ status, sha256, filename, directory, document_type, accounting_supplier }`.

                            ### `GET /file?sha256=...&expires=...&sig=...`
                            Téléchargement signé. Signature HMAC-SHA256 + expiration.

                            Voir `app.py` pour la liste exhaustive.

                            ---

                            ## Classification

                            Tout est en matière de string matching sur l'email et le filename :

                            - **Company** : substring sur l'email (drugoptimal / holding1 / default)
                            - **Document type** : substring sur le filename (devis / justificatif / facture / autre)
                            - **Accounting supplier** : Stripe, OpenAI, AWS, OVH, Notion + catégories (Hotel, Peage, Transport, Restaurant)

                            Limite connue : classification 100% basée sur le nom du fichier. Les scripts `recompute_*` permettent de re-tagger l'historique.

                            ---

                            ## Scripts opérationnels

                            - `monitor.sh` — cron de supervision
                            - `recompute_accounting_suppliers.py` — retag des suppliers
                            - `recompute_bea_v2.py` — migration Beatrice v1 → v2
                            - `fix_non_traite_factures.py` — cleanup des factures `non_traite`
                            - `test_pdf_analysis.py` — banc de test (dev only)

                            ---

                            ## Sécurité

                            - `.env` jamais versionné (voir `.gitignore`)
                            - API key obligatoire sur `POST /upload`
                            - URLs signées HMAC + expiration
                            - `hmac.compare_digest` (temps-constant)
                            - Filenames slugifiés ASCII via `secure_filename`

                            ---

                            ## Journal d'audit

                            `_log.csv` 10 colonnes : `timestamp, company, document_type, filename, sha256, status, directory, original_path, pennylane_status, accounting_supplier`.

                            ---

                            ## Archive

                            `archive/` contient les snapshots `app_before_*.py` et `app_v1_*.py` antérieurs au passage sous git. À garder en référence, ne pas modifier.

                            ---

                            ## Connecteur OpenAI (WIP)

                            `connectors/openai/openai_connector.py` est un prototype non déployé. Si tu le reprends, isole-le derrière un feature flag avant prod.

                            ---

                            ## Limitations connues

                            - Classification regex sur filename → fragile
                            - `_log.csv` lu/écrit en entier à chaque upload (à surveiller > 100k lignes)
                            - Pas de tests automatisés
                            - Pas de migration Pennylane structurée
                            
