import os
import shutil
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app.db")
BACKUP_DIR = os.path.join(os.path.dirname(__file__), "..", "backups")

def backup_database():
    if not os.path.exists(DB_PATH):
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"app_backup_{timestamp}.db")

    shutil.copy2(DB_PATH, backup_file)

    # Keep only last 5 backups
    backups = sorted(os.listdir(BACKUP_DIR))
    if len(backups) > 5:
        for old in backups[:-5]:
            os.remove(os.path.join(BACKUP_DIR, old))