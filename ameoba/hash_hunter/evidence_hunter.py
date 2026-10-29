#!/usr/bin/env python3
"""
Ameoba Phase 3B: Dual-Stage Cryptographic (SHA-256) + Perceptual (dHash/Spatial) Hunter (v0.3.0)
Scans external folders (seized cloud backups, recipient WhatsApp Media) against
a carved WAL record:
- Stage 1: Exact SHA-256 bit-for-bit match -> TIER_1_COURT_VERIFIED
- Stage 2: Perceptual 64-bit dHash + Spatial Cosine match -> TIER_2_RECOMPRESSED_OR_CROPPED_MATCH
"""
import hashlib, io, json, sys
from pathlib import Path
from PIL import Image, ImageEnhance
from rich.console import Console
from rich.table import Table
from ameoba.spatial_pose.pose_matcher import extract_spatial_descriptor, cosine_sim, generate_reference_360_panorama, crop_heading_view

console = Console()


def compute_dhash_64(img: Image.Image) -> int:
    """Computes a 64-bit Difference Hash (9x8 grayscale horizontal gradient)."""
    gray = img.convert("L").resize((9, 8), Image.Resampling.BILINEAR)
    px = gray.load()
    bits = 0
    for y in range(8):
        for x in range(8):
            bits = (bits << 1) | (1 if px[x, y] > px[x + 1, y] else 0)
    return bits


def hamming_distance(h1: int, h2: int) -> int:
    return (h1 ^ h2).bit_count()


def main():
    suspect_dir = Path("artifacts_out/seized_external_media")
    suspect_dir.mkdir(parents=True, exist_ok=True)

    # Create ground-truth original 640x480 image & its carved 64x48 WAL remnant
    pano = generate_reference_360_panorama()
    orig_img = crop_heading_view(pano, 285.0, fov_deg=60.0).resize((640, 480), Image.Resampling.BILINEAR)
    orig_buf = io.BytesIO()
    orig_img.save(orig_buf, format="JPEG", quality=92)
    orig_bytes = orig_buf.getvalue()
    carved_wal_sha256 = hashlib.sha256(orig_bytes).hexdigest()

    # Carved 64x48 micro-thumbnail from suspect's purged SQLite WAL
    carved_thumb = orig_img.resize((64, 48), Image.Resampling.BILINEAR)
    carved_dhash = compute_dhash_64(carved_thumb)
    carved_vec = extract_spatial_descriptor(carved_thumb)

    # Populate seized external folder with 4 realistic test files:
    # 1. Untouched Google Drive Backup Copy (Exact SHA-256 Match)
    (suspect_dir / "cloud_backup_PXL_20261023.jpg").write_bytes(orig_bytes)

    # 2. Recipient's WhatsApp Forwarded Copy (Re-compressed Q45 + resized -> SHA-256 changes!)
    wa_buf = io.BytesIO()
    orig_img.resize((480, 360), Image.Resampling.BILINEAR).save(wa_buf, format="JPEG", quality=45)
    (suspect_dir / "IMG-20261023-WA0019_recompressed.jpg").write_bytes(wa_buf.getvalue())

    # 3. Cropped & Brightness-Edited Screenshot (12% border crop -> SHA-256 changes!)
    crop_img = orig_img.crop((38, 28, 602, 452)).resize((640, 480), Image.Resampling.BILINEAR)
    crop_img = ImageEnhance.Brightness(crop_img).enhance(1.08)
    crop_buf = io.BytesIO()
    crop_img.save(crop_buf, format="JPEG", quality=75)
    (suspect_dir / "screenshot_cropped_edit.jpg").write_bytes(crop_buf.getvalue())

    # 4. Unrelated Innocent Photo (Different angle 90° East)
    other_img = crop_heading_view(pano, 90.0, fov_deg=60.0).resize((640, 480), Image.Resampling.BILINEAR)
    other_buf = io.BytesIO()
    other_img.save(other_buf, format="JPEG", quality=85)
    (suspect_dir / "unrelated_park_photo.jpg").write_bytes(other_buf.getvalue())

    table = Table(title="Ameoba Phase 3B — Dual-Stage Evidence Hunter (SHA-256 Oracle + Perceptual Vector)")
    for col in ["External File", "SHA-256 Match", "dHash Dist", "Spatial Sim", "Match Verdict", "Epistemic Tier"]:
        table.add_column(col)

    hunt_results = []
    for fpath in sorted(suspect_dir.glob("*.jpg")):
        fbytes = fpath.read_bytes()
        f_sha = hashlib.sha256(fbytes).hexdigest()
        sha_exact = (f_sha == carved_wal_sha256)

        img = Image.open(io.BytesIO(fbytes))
        d_dist = hamming_distance(carved_dhash, compute_dhash_64(img))
        s_sim = cosine_sim(carved_vec, extract_spatial_descriptor(img))

        if sha_exact:
            verdict = "[bold green]✓ EXACT BIT-FOR-BIT MATCH[/bold green]"
            tier = "AMBO_TIER_1_CRYPTOGRAPHIC_CERTAINTY"
        elif d_dist <= 14 and s_sim >= 0.92:
            verdict = "[bold yellow]~ PERCEPTUAL MATCH (Recompressed/Cropped)[/bold yellow]"
            tier = "AMBO_TIER_2_PERCEPTUAL_CORROBORATION"
        else:
            verdict = "[dim]✗ NO MATCH (Unrelated Media)[/dim]"
            tier = "UNRELATED"

        hunt_results.append({
            "candidate_file": fpath.name,
            "sha256": f_sha,
            "exact_sha256_match": sha_exact,
            "dhash_hamming_distance": d_dist,
            "spatial_cosine_similarity": round(s_sim, 4),
            "epistemic_tier": tier,
        })

        table.add_row(
            fpath.name,
            "[bold green]YES (100%)[/bold green]" if sha_exact else "NO (Altered)",
            f"{d_dist}/64 bits",
            f"{s_sim:.4f}",
            verdict,
            tier.replace("AMBO_", ""),
        )

    console.print(table)
    out_file = Path("artifacts_out/ameoba_hunt_report.json")
    out_file.write_text(json.dumps(hunt_results, indent=2))
    console.print(f"[bold green][✓] Saved Phase 3B Dual-Stage Hunt Report to {out_file}[/bold green]")


if __name__ == "__main__":
    main()
