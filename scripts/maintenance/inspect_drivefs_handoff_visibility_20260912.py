"""List the cloud children of the two mmWave handoff task folders (read-only).

Purpose: confirm whether the earlier integration-snapshot-v1 handoff actually
reached the cloud task folder, and confirm the estimator-improvement folder is
currently empty before upload.

Read-only: opens the DriveFS metadata sqlite database with mode=ro, never writes,
and never touches account credentials.
"""

import sqlite3
import sys

DB = r"C:\Users\550ACW\AppData\Local\Google\DriveFS\113318503413191277152\metadata_sqlite_db"
TASKS = {
    10620: "2026-09-12_mmwave_estimator_improvement_v1",
    10621: "2026-09-12_mmwave_integration_snapshot_v1",
}


def main() -> int:
    con = sqlite3.connect("file:" + DB.replace("\\", "/") + "?mode=ro", uri=True)
    con.text_factory = bytes
    cur = con.cursor()

    for stable_id, label in TASKS.items():
        rows = cur.execute(
            """select i.stable_id, i.local_title, i.file_size
               from stable_parents p join items i on i.stable_id = p.item_stable_id
               where p.parent_stable_id = ? order by i.local_title""",
            (stable_id,),
        ).fetchall()
        print(f"== {label}: {len(rows)} cloud children ==")
        for child_id, title, size in rows:
            title = title.decode("utf-8", "replace") if isinstance(title, bytes) else title
            print(f"   {child_id}\t{title}\t{size}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
