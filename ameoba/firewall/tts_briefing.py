#!/usr/bin/env python3
"""
Ameoba Local TTS Briefing Exporter (v0.4.0 - gTTS Python native)
"""
import json
import sys
from pathlib import Path
from gtts import gTTS


def main():
    report_path = Path("artifacts_out/ameoba_final_audit/ameoba_final_audit_report.json")
    if not report_path.exists():
        print(f"[!] Audit report not found at {report_path}. Run `ameoba-brief` first!")
        sys.exit(1)

    audit_data = json.loads(report_path.read_text())
    script_text = audit_data.get("spoken_investigator_briefing_script")

    if not script_text:
        print("[!] Spoken briefing script not found in audit report.")
        sys.exit(1)

    out_wav = Path("artifacts_out/ameoba_investigator_briefing.mp3")
    out_wav.parent.mkdir(parents=True, exist_ok=True)

    print(f"[*] Synthesizing audio via gTTS...")
    print(f"    Text: \"{script_text}\"")

    # Generate speech and save
    tts = gTTS(text=script_text, lang='en', slow=False)
    tts.save(str(out_wav))

    print(f"\n[✓] Success! Audible briefing securely saved to: {out_wav}")


if __name__ == "__main__":
    main()
