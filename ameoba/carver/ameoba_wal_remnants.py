"""ALEAPP v2 Artifact Plugin for Ameoba Post-Purge WAL Media Remnants."""
__artifacts_v2__ = {
    "get_ameoba_wal_remnants": {
        "name": "Ameoba Post-Purge WAL Media Remnants",
        "description": "Carves deleted MediaStore and messaging WAL frames, micro-thumbnails, and SHA-256 hashes",
        "author": "Damanlovedeep Singh",
        "creation_date": "2026-10-29",
        "last_update_date": "2026-10-29",
        "requirements": "none",
        "category": "Ameoba Forensic Reconstruction",
        "notes": "Epistemic Tier 1 Deterministic WAL Frame Carver",
        "paths": (
            "*/com.google.android.providers.media.module/databases/external.db-wal",
            "*/com.google.android.apps.photos/databases/gphotos0.db-wal",
            "*/com.whatsapp/databases/msgstore.db-wal",
        ),
        "output_types": "standard",
        "artifact_icon": "database",
    }
}
