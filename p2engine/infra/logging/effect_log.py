import json
from datetime import datetime
from pathlib import Path

LOG_DIR = Path("logs/effects")


def append_effect_log(conversation_id: str, entry: dict):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"{conversation_id}.log"
    with open(log_file, "a") as f:
        entry["ts"] = datetime.utcnow().isoformat() + "Z"
        f.write(json.dumps(entry) + "\n")
