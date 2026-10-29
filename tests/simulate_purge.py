#!/usr/bin/env python3
"""Ameoba fixture: MediaStore-like DB in WAL mode, insert -> trash -> purge, WAL kept uncheckpointed."""
import hashlib, io, json, os, shutil, sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path("artifacts_out/sim_case_001")
IST = timezone(timedelta(hours=5, minutes=30))

def thumb():
    img = Image.new("RGB", (64, 48))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 63, 22], fill=(235, 130, 65))
    d.rectangle([0, 23, 30, 47], fill=(35, 65, 95))
    d.rectangle([31, 23, 63, 47], fill=(80, 82, 88))
    d.rectangle([42, 26, 58, 36], fill=(240, 242, 245))
    buf = io.BytesIO(); img.save(buf, "JPEG", quality=75)
    return buf.getvalue()

def main():
    shutil.rmtree(OUT, ignore_errors=True); OUT.mkdir(parents=True)
    db = OUT / "external.db"
    taken = datetime(2026, 10, 23, 16, 42, 8, tzinfo=IST)
    ts_ms = int(taken.timestamp() * 1000)
    name = "PXL_20261023_111208.jpg"
    payload = b"SIMULATED_JPEG_" + os.urandom(4096)
    sha = hashlib.sha256(payload).hexdigest()
    tb = thumb()

    # keep a second connection open so close() cannot checkpoint/delete the WAL
    keeper = sqlite3.connect(db)
    keeper.execute("PRAGMA journal_mode=WAL"); keeper.execute("PRAGMA wal_autocheckpoint=0")
    keeper.execute("CREATE TABLE IF NOT EXISTS t(x)"); keeper.commit()
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA wal_autocheckpoint=0")
    conn.execute("""CREATE TABLE media(_id INTEGER PRIMARY KEY, _data TEXT, _size INTEGER,
        datetaken INTEGER, latitude REAL, longitude REAL, is_trashed INTEGER,
        sha256 TEXT, jpeg_thumbnail BLOB)""")
    conn.commit()
    path = f"/storage/emulated/0/DCIM/Camera/{name}"
    conn.execute("INSERT INTO media VALUES(101,?,?,?,?,?,0,?,?)",
                 (path, len(payload), ts_ms, 23.2598, 77.3812, sha, tb)); conn.commit()
    trashed = f"/storage/emulated/0/DCIM/Camera/.trashed-{ts_ms//1000+86400*30}-{name}"
    conn.execute("UPDATE media SET is_trashed=1,_data=? WHERE _id=101", (trashed,)); conn.commit()
    conn.execute("DELETE FROM media WHERE _id=101"); conn.commit()

    live = conn.execute("SELECT COUNT(*) FROM media").fetchone()[0]
    ev = OUT / "evidence"; ev.mkdir()                      # snapshot before anything closes
    shutil.copyfile(f"{db}-wal", ev / "external.db-wal")
    shutil.copyfile(db, ev / "external.db")
    conn.close(); keeper.close()

    truth = {"id": 101, "path": path, "trashed_path": trashed, "sha256": sha,
             "datetaken_ms": ts_ms, "datetaken_iso": taken.isoformat(),
             "lat": 23.2598, "lon": 77.3812, "thumb_bytes": len(tb),
             "thumb_sha256": hashlib.sha256(tb).hexdigest()}
    (OUT / "ground_truth.json").write_text(json.dumps(truth, indent=2))
    print(f"live rows: {live} | wal: {(ev/'external.db-wal').stat().st_size} bytes | {taken.isoformat()} = {ts_ms}")

if __name__ == "__main__":
    main()
