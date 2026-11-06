"""Comprueba que los IDs de datasets existen y muestra sus columnas."""
import requests
from config import DATASETS, SOCRATA_URL
for nombre, ds in DATASETS.items():
    try:
        r = requests.get(f"{SOCRATA_URL}{ds}.json", params={"$limit": 1}, timeout=60)
        r.raise_for_status()
        print(f"[OK] {nombre} ({ds}) columnas:", list(r.json()[0].keys()))
    except Exception as e:
        print(f"[ERROR] {nombre} ({ds}): {e}  -> busca el ID correcto en datos.gov.co")
