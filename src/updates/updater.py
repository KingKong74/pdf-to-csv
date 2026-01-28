import json
import urllib.request

UPDATE_JSON_URL = "https://raw.githubusercontent.com/KingKong74/pdf-to-csv/main/update.json"

def _vtuple(v: str):
    return tuple(int(x) for x in v.strip().split("."))

def check_for_update(current_version: str, timeout_s: int = 5) -> dict | None:
    """
    Returns dict with keys: latest, notes, download_url if update exists, else None.
    """
    with urllib.request.urlopen(UPDATE_JSON_URL, timeout=timeout_s) as r:
        data = json.loads(r.read().decode("utf-8"))

    latest = data.get("latest", "").strip()
    if not latest:
        return None

    if _vtuple(latest) > _vtuple(current_version):
        return data

    return None
