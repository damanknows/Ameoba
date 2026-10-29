#!/usr/bin/env python3
import hashlib, json, re, sqlite3, sys
from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()
JPEG_RE = re.compile(b"\xff\xd8\xff[\xe0-\xef].*?\xff\xd9", re.DOTALL)
PATH_RE = re.compile(rb"(/storage/emulated/0/[^\x00-\x1f\"'<>]+?\.(?:jpg|jpeg|png|heic|mp4|opus|m4a|wav))", re.I)
TRASH_RE = re.compile(rb"(\.trashed-[0-9]+-[^\x00-\x1f\"'<>]+)")

def scan_file(fp: Path, out_thumbs: Path) -> dict:
    raw = fp.read_bytes()
    paths = sorted(set(m.group(1).decode("utf-8", "ignore") for m in PATH_RE.finditer(raw)))
    trashed = sorted(set(m.group(1).decode("utf-8", "ignore") for m in TRASH_RE.finditer(raw)))
    thumbs = []
    for jm in JPEG_RE.finditer(raw):
        b = jm.group(0)
        if 200 <= len(b) <= 250000:
            h = hashlib.sha256(b).hexdigest()[:12]
            name = f"{fp.name}_off_{jm.start()}_{h}.jpg"
            (out_thumbs / name).write_bytes(b)
            thumbs.append({"file": name, "offset": jm.start(), "size": len(b)})
    return {"artifact": fp.name, "size_kb": len(raw)//1024, "paths": len(paths), "trashed": len(trashed), "thumbs": len(thumbs)}

def main():
    c_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("artifacts_out/smoke_test")
    out_dir = Path("artifacts_out/ameoba_corpus_scan")
    out_thumbs = out_dir / "carved_thumbnails"
    out_thumbs.mkdir(parents=True, exist_ok=True)
    t = Table(title="Ameoba Phase 1 — Corpus Scan Summary")
    for col in ["Artifact", "Size (KB)", "Media Paths", ".trashed Hits", "Carved Thumbs"]:
        t.add_column(col)
    res = []
    for p in sorted(c_root.rglob("*")):
        if p.is_file() and p.name.endswith((".db", ".db-wal", ".db-journal")):
            r = scan_file(p, out_thumbs)
            res.append(r)
            t.add_row(r["artifact"], str(r["size_kb"]), str(r["paths"]), str(r["trashed"]), str(r["thumbs"]))
    console.print(t)
    (out_dir / "ameoba_scan_report.json").write_text(json.dumps(res, indent=2))
    console.print(f"[bold green][✓] Saved scan report to {out_dir / 'ameoba_scan_report.json'}[/bold green]")

if __name__ == "__main__":
    main()
