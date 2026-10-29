#!/usr/bin/env python3
"""
Ameoba Master Pipeline Orchestrator
Executes Phase 1 through Phase 4 sequentially with live Rich console formatting.
"""
import subprocess
import sys
from rich.console import Console
from rich.panel import Panel

console = Console()

def run_step(title: str, cmd: list[str]):
    console.print(Panel(f"[bold cyan]Running {title}...[/bold cyan]", expand=False))
    res = subprocess.run(cmd)
    if res.returncode != 0:
        console.print(f"[bold red][!] {title} failed with exit code {res.returncode}[/bold red]")
        sys.exit(res.returncode)
    console.print(f"[bold green][✓] {title} completed successfully![/bold green]\n")

def main():
    console.print(Panel("[bold magenta]AMEOBA: End-to-End Digital Forensics Simulation[/bold magenta]\n"
                        "Bridging Low-Level WAL Carving & High-Level Physical Verification", expand=False))

    # Phase 1: Corpus Scan & WAL Carving
    run_step("Phase 1: Binary WAL Scanning & Carving", ["ameoba-scan", "artifacts_out/smoke_test"])
    run_step("Phase 1: WAL Frame Offset Extraction", [
        "ameoba-carve", 
        "artifacts_out/smoke_test/smoke_external.db-wal", 
        "artifacts_out/smoke_test/carved_out"
    ])

    # Phase 2: Solar Chronolocation Verification
    run_step("Phase 2: Solar Ephemeris & Clock-Tamper Analysis", ["ameoba-chrono"])

    # Phase 3: 6-DoF Pose Matching & Evidence Hunting
    run_step("Phase 3A: 6-DoF Compass Heading Localization", ["ameoba-pose"])
    run_step("Phase 3B: Dual-Stage Perceptual & SHA-256 Evidence Hunter", ["ameoba-hunt"])

    # Phase 4: Epistemic Firewall Audit & Local TTS Briefing Audio
    run_step("Phase 4: SWGDE Epistemic Firewall Audit Report", ["ameoba-brief"])
    run_step("Phase 4: Local Audio Briefing Synthesis (gTTS)", ["ameoba-audio"])

    console.print(Panel(
        "[bold green]Full Ameoba Simulation Completed Successfully![/bold green]\n\n"
        "Generated Artifacts:\n"
        " • Carved Thumbnails & Manifests : artifacts_out/smoke_test/carved_out/\n"
        " • Solar Chronology Report       : artifacts_out/ameoba_chrono_report.json\n"
        " • 6-DoF Pose Benchmark          : artifacts_out/ameoba_pose_results/\n"
        " • Evidence Hunt Report          : artifacts_out/ameoba_hunt_report.json\n"
        " • SWGDE Final Audit Report      : artifacts_out/ameoba_final_audit/ameoba_final_audit_report.json\n"
        " • Investigator Audio Briefing   : artifacts_out/ameoba_investigator_briefing.mp3",
        title="Simulation Complete",
        expand=False
    ))

if __name__ == "__main__":
    main()
