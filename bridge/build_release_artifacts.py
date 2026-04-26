import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent.parent
SOURCE_FILES = [
    ROOT / "bridge" / "ExportBundle.json",
    ROOT / "bridge" / "ProjectionBundle.json",
    ROOT / "bridge" / "LegitimacyRecords.json",
    ROOT / "export" / "stig_expert_critic.html",
    ROOT / "factory_exports" / "stig_expert_critic" / "stig_expert_critic.html",
    ROOT / "factory_exports" / "stig_expert_critic" / "data" / "ProjectionBundle.json",
]
OUTPUT_ROOT = ROOT / "output" / "releases"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def main():
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    release_dir = OUTPUT_ROOT / f"stig_export_release_{timestamp}"
    release_dir.mkdir(parents=True, exist_ok=True)

    manifest_entries = []
    for source in SOURCE_FILES:
        if not source.exists():
            raise FileNotFoundError(f"missing release artifact: {source}")
        target = release_dir / source.name
        shutil.copyfile(source, target)
        manifest_entries.append(
            {
                "name": source.name,
                "source_path": str(source.relative_to(ROOT)),
                "release_path": str(target.relative_to(ROOT)),
                "sha256": sha256_file(target),
                "size_bytes": target.stat().st_size,
            }
        )

    manifest = {
        "record_kind": "StigExportReleaseManifest",
        "generated_at": timestamp,
        "release_dir": str(release_dir.relative_to(ROOT)),
        "artifacts": manifest_entries,
    }
    manifest_path = release_dir / "release_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"RELEASE ARTIFACTS WRITTEN: {release_dir}")
    print(f"RELEASE MANIFEST: {manifest_path}")


if __name__ == "__main__":
    main()
