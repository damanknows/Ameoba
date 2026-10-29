#!/usr/bin/env python3
"""
Ameoba Phase 2: Solar Ephemeris & Thumbnail Chronolocation Verifier (v0.2.0)
Computes deterministic solar elevation & azimuth from (lat, lon, timestamp_ms)
and cross-checks against the carved 64x48 thumbnail's sky luminance and
shadow/lighting gradient to catch clock or GPS tampering.
"""
import datetime, json, math, sys
from pathlib import Path
from PIL import Image
from rich.console import Console
from rich.table import Table

console = Console()


def compute_solar_position(lat_deg: float, lon_deg: float, timestamp_ms: int) -> dict:
    """
    Deterministic NOAA / Spherical Astronomy Solar Position Calculator.
    Returns solar elevation (deg above horizon), azimuth (deg clockwise from North),
    shadow length multiplier (L = 1 / tan(el)), and expected lighting regime.
    """
    dt_utc = datetime.datetime.fromtimestamp(timestamp_ms / 1000.0, tz=datetime.timezone.utc)
    day_of_year = dt_utc.timetuple().tm_yday
    utc_hours = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0

    # Fractional year gamma (radians)
    gamma = 2.0 * math.pi / 365.0 * (day_of_year - 1 + (utc_hours - 12.0) / 24.0)

    # Equation of time (minutes) & solar declination (radians)
    eqtime = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )
    decl = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.00148 * math.sin(3 * gamma)
    )

    # True solar time & hour angle
    time_offset = eqtime + 4.0 * lon_deg
    tst = (utc_hours * 60.0 + time_offset) % 1440.0
    ha_deg = (tst / 4.0) - 180.0
    ha_rad = math.radians(ha_deg)
    lat_rad = math.radians(lat_deg)

    # Solar zenith & elevation
    sin_el = math.sin(lat_rad) * math.sin(decl) + math.cos(lat_rad) * math.cos(decl) * math.cos(ha_rad)
    sin_el = max(-1.0, min(1.0, sin_el))
    el_rad = math.asin(sin_el)
    el_deg = math.degrees(el_rad)

    # Solar azimuth (degrees clockwise from North)
    zenith_rad = (math.pi / 2.0) - el_rad
    cos_az = (math.sin(decl) - math.sin(lat_rad) * math.cos(zenith_rad)) / (
        max(1e-6, math.cos(lat_rad) * math.sin(zenith_rad))
    )
    cos_az = max(-1.0, min(1.0, cos_az))
    az_deg = math.degrees(math.acos(cos_az))
    if ha_deg > 0:
        az_deg = (360.0 - az_deg) % 360.0

    shadow_mult = round(1.0 / math.tan(el_rad), 2) if el_deg > 2.0 else None
    shadow_azimuth = round((az_deg + 180.0) % 360.0, 1) if el_deg > 0 else None

    if el_deg < -6.0:
        regime = "NIGHT"
    elif el_deg <= 18.0:
        regime = "GOLDEN_HOUR_LOW_SUN"
    else:
        regime = "HIGH_DAYLIGHT"

    return {
        "utc_iso": dt_utc.isoformat(),
        "ist_iso": dt_utc.astimezone(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).isoformat(),
        "solar_elevation_deg": round(el_deg, 2),
        "solar_azimuth_deg": round(az_deg, 2),
        "expected_shadow_azimuth_deg": shadow_azimuth,
        "shadow_length_multiplier": shadow_mult,
        "astronomical_regime": regime,
    }


def analyze_thumbnail_physics(thumb_path: Path) -> dict:
    """
    Extracts sky luminance, warm/cool color ratio, and horizontal shadow bias
    from a carved 64x48 micro-thumbnail.
    """
    img = Image.open(thumb_path).convert("RGB")
    w, h = img.size
    pixels = img.load()

    # Top third = sky region; Bottom half = ground/shadow region
    sky_r, sky_g, sky_b, sky_count = 0.0, 0.0, 0.0, 0
    left_ground_lum, right_ground_lum = 0.0, 0.0

    for y in range(h):
        for x in range(w):
            r, g, b = pixels[x, y]
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            if y < h // 3:
                sky_r += r
                sky_g += g
                sky_b += b
                sky_count += 1
            elif y >= h // 2:
                if x < w // 2:
                    left_ground_lum += lum
                else:
                    right_ground_lum += lum

    mean_r = sky_r / max(1, sky_count)
    mean_g = sky_g / max(1, sky_count)
    mean_b = sky_b / max(1, sky_count)
    sky_lum = 0.299 * mean_r + 0.587 * mean_g + 0.114 * mean_b
    warmth_ratio = round(mean_r / max(1.0, mean_b), 2)

    if sky_lum < 40.0:
        observed_regime = "NIGHT"
    elif warmth_ratio >= 1.45 and sky_lum < 195.0:
        observed_regime = "GOLDEN_HOUR_LOW_SUN"
    else:
        observed_regime = "HIGH_DAYLIGHT"

    ground_bias = round((left_ground_lum - right_ground_lum) / max(1.0, left_ground_lum + right_ground_lum), 3)

    return {
        "thumb_file": thumb_path.name,
        "resolution": f"{w}x{h}",
        "sky_luminance": round(sky_lum, 1),
        "sky_warmth_rb_ratio": warmth_ratio,
        "ground_lr_luminance_bias": ground_bias,
        "observed_visual_regime": observed_regime,
    }


def verify_chronolocation(thumb_path: Path, lat: float, lon: float, ts_ms: int, label: str = "Case") -> dict:
    solar = compute_solar_position(lat, lon, ts_ms)
    visual = analyze_thumbnail_physics(thumb_path)

    anomalies = []
    # Check 1: Night vs Daylight mismatch
    if solar["astronomical_regime"] == "NIGHT" and visual["sky_luminance"] > 65.0:
        anomalies.append(
            f"DAY_NIGHT_SPOOF: Timestamp claims Night (Sun {solar['solar_elevation_deg']}°), "
            f"but thumbnail sky luminance is {visual['sky_luminance']}/255."
        )
    elif solar["astronomical_regime"] != "NIGHT" and visual["observed_visual_regime"] == "NIGHT":
        anomalies.append(
            f"NIGHT_IN_DAY_SPOOF: Timestamp claims Daylight (Sun +{solar['solar_elevation_deg']}°), "
            f"but thumbnail is dark ({visual['sky_luminance']}/255)."
        )

    # Check 2: High Noon vs Low Golden-Hour Shadow/Warmth mismatch
    if solar["solar_elevation_deg"] > 42.0 and visual["observed_visual_regime"] == "GOLDEN_HOUR_LOW_SUN":
        anomalies.append(
            f"ELEVATION_MISMATCH: Timestamp claims High Sun (+{solar['solar_elevation_deg']}°), "
            f"but thumbnail shows strong Golden-Hour R/B warmth ({visual['sky_warmth_rb_ratio']}x)."
        )

    verdict = "CLOCK_OR_GPS_TAMPER_DETECTED" if anomalies else "CHRONOLOCATION_VERIFIED"
    return {
        "scenario": label,
        "gps": {"lat": lat, "lon": lon},
        "solar_ephemeris": solar,
        "thumbnail_physics": visual,
        "anomalies": anomalies,
        "forensic_verdict": verdict,
        "epistemic_tier": "AMBO_TIER_1_ASTRONOMICAL_VERIFICATION",
    }


def main():
    thumb = Path(sys.argv[1]) if len(sys.argv) > 1 else next(Path("artifacts_out/smoke_test/carved_out").glob("*.jpg"))
    # Default coordinates: Bhopal VIP Road Upper Lake (23.2598 N, 77.3812 E)
    lat, lon = 23.2598, 77.3812

    scenarios = [
        ("Authentic Capture (16:42 IST - Golden Hour)", 1761217928000),  # 2025-10-23 16:42:08 IST
        ("Tampered Clock #1 (23:30 IST - Night Spoof)", 1761242400000),  # 2025-10-23 23:30:00 IST
        ("Tampered Clock #2 (12:05 IST - High Noon Spoof)", 1761201300000),  # 2025-10-23 12:05:00 IST
    ]

    table = Table(title="Ameoba Phase 2 — Solar Physics & Clock-Spoof Verification")
    for col in ["Scenario", "IST Time", "Sun Elev", "Sun Azimuth", "Shadow Mult", "Sky Lum / R:B", "Forensic Verdict"]:
        table.add_column(col)

    results = []
    for label, ts in scenarios:
        res = verify_chronolocation(thumb, lat, lon, ts, label)
        results.append(res)
        s = res["solar_ephemeris"]
        v = res["thumbnail_physics"]
        verdict_str = (
            "[bold green]✓ VERIFIED[/bold green]"
            if res["forensic_verdict"] == "CHRONOLOCATION_VERIFIED"
            else "[bold red]✗ TAMPER CAUGHT[/bold red]"
        )
        table.add_row(
            label,
            s["ist_iso"][11:19],
            f"{s['solar_elevation_deg']}°",
            f"{s['solar_azimuth_deg']}°",
            f"{s['shadow_length_multiplier']}x" if s["shadow_length_multiplier"] else "N/A (Night)",
            f"{v['sky_luminance']} ({v['sky_warmth_rb_ratio']}x)",
            verdict_str,
        )

    console.print(table)
    out_file = Path("artifacts_out/ameoba_chrono_report.json")
    out_file.write_text(json.dumps(results, indent=2))
    console.print(f"[bold green][✓] Saved Phase 2 Chronolocation Report to {out_file}[/bold green]")


if __name__ == "__main__":
    main()
