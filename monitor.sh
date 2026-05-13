#!/bin/bash

echo "=== MONITORING FACTURES-V1 ==="
echo

echo "[1] Statut du conteneur"
docker ps --filter "name=factures-v1" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo

echo "[2] Test de l'API"
curl -s http://127.0.0.1:8000/health || echo "API KO"
echo
echo

echo "[3] Dernières lignes des logs Docker"
docker logs factures-v1 --tail 20 2>&1
echo
echo

echo "[4] Dernières lignes du log applicatif"
tail -n 10 /opt/factures-v1/uploads/_log.csv 2>/dev/null || echo "Pas encore de _log.csv"
echo
