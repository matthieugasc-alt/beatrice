# Archive — snapshots historiques de `app.py`

Ce dossier contient les versions successives de `app.py` que tu as conservées
manuellement (`cp app.py app_before_*.py`) avant chaque grosse modification,
avant que le projet ne passe sous git.

**Ne pas modifier ces fichiers.** Ils servent uniquement de référence pour
retrouver une logique métier ancienne, ou comparer avec la version actuelle :

```bash
diff -u archive/app_before_bea_v2_step1.py ../app.py
```

## Chronologie approximative

Reconstruite à partir des noms de fichiers, dans l'ordre supposé :

1. `app_v1_working.py` — premier état stable identifié comme "working"
2. `app_v1_company_routing_working.py` — après ajout du routage par company
3. `app_before_download_step.py` — avant ajout de la route de download
4. `app_before_signed_download.py` — avant signature HMAC des URLs
5. `app_before_receipt_fix.py` — avant correctif sur les justificatifs
6. `app_before_dashboard.py` — avant ajout du dashboard
7. `app_before_backend_mapping.py` — avant refonte du mapping backend
8. `app_before_beatrice_anomalies.py` — avant gestion d'anomalies Beatrice
9. `app_before_beatrice_html.py` — avant refonte HTML de Beatrice
10. `app_before_beatrice_filters.py` — avant filtres Beatrice
11. `app_before_beatrice_filters_v2.py` — itération suivante des filtres
12. `app_before_bea_v2_step1.py` — début migration Beatrice v2
13. `app_before_bea_v2_step2.py` — étape suivante migration

À partir du premier commit git, l'historique vit dans `git log` et plus dans
des copies manuelles. Si tu modifies à nouveau `app.py`, fais un commit, pas
une copie ici.
