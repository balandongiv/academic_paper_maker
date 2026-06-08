"""Keep running screen_abstracts.py --batch-size 20 until all candidates are processed."""
import subprocess
import sys
import time
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "setting" / "chatgpt_ui" / "config_fatigue_eeg.yaml"


def get_pending(db_path: Path, keyword_filter: str) -> int:
    if not db_path.exists():
        return -1
    conn = sqlite3.connect(db_path)
    try:
        sql = f"""
            SELECT COUNT(*) FROM articles
            WHERE status IN ('Yet To Process', 'Failed', 'Already Processing', 'In Progress')
            AND ({keyword_filter})
        """
        row = conn.execute(sql).fetchone()
        return row[0] if row else 0
    finally:
        conn.close()


def get_completed(db_path: Path, keyword_filter: str) -> int:
    if not db_path.exists():
        return 0
    conn = sqlite3.connect(db_path)
    try:
        sql = f"SELECT COUNT(*) FROM articles WHERE status='Completed' AND ({keyword_filter})"
        row = conn.execute(sql).fetchone()
        return row[0] if row else 0
    finally:
        conn.close()


def load_db_path_and_filter():
    import yaml
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    root = Path(cfg["project_root"])
    db_path = root / cfg["output"]["db_file"]
    kf = cfg["processing"].get("keyword_filter", "1=1")
    return db_path, kf


def main():
    db_path, keyword_filter = load_db_path_and_filter()
    batch = 0

    while True:
        pending = get_pending(db_path, keyword_filter)
        completed = get_completed(db_path, keyword_filter)
        print(f"\n[loop] Batch {batch} done. Completed={completed}, Pending={pending}", flush=True)

        if pending == 0:
            print("[loop] All candidates processed. Done!", flush=True)
            break

        batch += 1
        print(f"[loop] Starting batch {batch} ...", flush=True)
        result = subprocess.run(
            [sys.executable, str(HERE / "screen_abstracts.py"), "--batch-size", "20"],
            cwd=str(HERE),
        )

        # Kill any leftover Chrome instances before next batch
        subprocess.run(
            ["taskkill", "/F", "/IM", "chrome.exe"],
            capture_output=True,
        )
        time.sleep(5)

        if result.returncode not in (0, 1):
            print(f"[loop] Non-zero exit {result.returncode} — stopping.", flush=True)
            break

    print("[loop] Finished.", flush=True)


if __name__ == "__main__":
    main()
