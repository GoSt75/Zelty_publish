"""
Active ou désactive les plats Zelty selon le semainier Excel.
Usage : python zelty_semainier.py --api-key <CLE_API> [--dry-run]
"""

import argparse
import datetime
import io
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

for pkg in ("openpyxl", "requests"):
    try:
        __import__(pkg)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

import openpyxl
import requests

EXCEL_PATH = "semainier.xlsx"
API_BASE = "https://api.zelty.fr/2.10"

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def load_semainier(path: str) -> dict[str, dict[str, int]]:
    """Retourne {jour: {'paire': id, 'impaire': id}} depuis le fichier Excel."""
    wb = openpyxl.load_workbook(path)
    ws = wb.active
    semainier = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        jour, id_paire, id_impaire = row
        if jour:
            semainier[jour.lower()] = {"paire": id_paire, "impaire": id_impaire}
    return semainier


def get_active_dish_id(semainier: dict, today: datetime.date) -> int:
    """Retourne l'ID du plat actif pour aujourd'hui."""
    jour = JOURS[today.weekday()]
    semaine = "paire" if today.isocalendar()[1] % 2 == 0 else "impaire"
    entry = semainier.get(jour)
    if entry is None:
        raise ValueError(f"Jour '{jour}' introuvable dans le semainier")
    return entry[semaine]


def get_all_dish_ids(semainier: dict) -> set[int]:
    """Retourne tous les IDs de plats présents dans le semainier."""
    ids = set()
    for entry in semainier.values():
        ids.add(entry["paire"])
        ids.add(entry["impaire"])
    return ids


def upsert_dishes(api_key: str, payload: list[dict], dry_run: bool) -> None:
    """Envoie un seul POST avec tous les plats à mettre à jour."""
    if dry_run:
        for item in payload:
            action = "ACTIVER" if item["visible"] else "DÉSACTIVER"
            print(f"  [dry-run] {action} plat {item['id']}")
        return

    import json
    print(f"  Payload envoyé : {json.dumps(payload, ensure_ascii=False)}")

    resp = requests.post(
        f"{API_BASE}/catalog/dishes",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
    )
    print(f"  HTTP {resp.status_code} : {resp.text[:500]}")
    resp.raise_for_status()
    data = resp.json()
    if data.get("errno", 0) != 0:
        print(f"  [ERREUR API] errno={data['errno']}", file=sys.stderr)
    else:
        for item in payload:
            print(f"  OK : plat {item['id']} {'activé' if item['visible'] else 'désactivé'}")


def main():
    parser = argparse.ArgumentParser(description="Semainier Zelty")
    parser.add_argument("--api-key", required=True, help="Clé API Zelty (Bearer token)")
    parser.add_argument("--dry-run", action="store_true", help="Simule sans appeler l'API")
    args = parser.parse_args()

    today = datetime.date.today()
    jour = JOURS[today.weekday()]
    semaine_num = today.isocalendar()[1]
    semaine = "paire" if semaine_num % 2 == 0 else "impaire"

    print(f"Date     : {today.strftime('%A %d/%m/%Y')} (semaine {semaine_num} => {semaine})")
    print(f"Jour     : {jour}")
    print()

    semainier = load_semainier(EXCEL_PATH)
    active_id = get_active_dish_id(semainier, today)
    all_ids = get_all_dish_ids(semainier)
    inactive_ids = all_ids - {active_id}

    print(f"Plat à activer   : {active_id}")
    print(f"Plats à désactiver: {sorted(inactive_ids)}")
    print()

    payload = [{"id": dish_id, "visible": False} for dish_id in sorted(inactive_ids)]
    payload.append({"id": active_id, "visible": True})

    print("Envoi en un seul appel API...")
    upsert_dishes(args.api_key, payload, dry_run=args.dry_run)

    print("\nTerminé.")


if __name__ == "__main__":
    main()
