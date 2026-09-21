#!/usr/bin/env python3
"""Verify locally acquired Sherlock archives and inventory their members.

Standard library only. Never executes archive content or blindly extracts paths.
Remote MD5 is an integrity reference; SHA256 is computed from the local bytes.
Incomplete files remain .part until size and MD5 both match pinned metadata.
"""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    hashes = {name: hashlib.new(name) for name in ("md5", "sha256")}
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            for value in hashes.values():
                value.update(chunk)
    return {name: value.hexdigest() for name, value in hashes.items()}


def category(name):
    lower = name.lower()
    if lower.endswith((".pcap", ".pcap.gz", ".pcapng", ".pcapng.gz")):
        return "network_capture"
    if "physical" in lower:
        return "evaluator_physical_truth"
    if "event" in lower:
        return "evaluator_event_metadata"
    if "state" in lower:
        return "process_state_requires_lineage_audit"
    if "map" in lower or "rules" in lower:
        return "mapping_or_transformation"
    if "config" in lower:
        return "configuration_requires_visibility_audit"
    return "other"


def audit(root):
    metadata_path = root / "data/manifests/zenodo_18467070.json"
    metadata = json.loads(metadata_path.read_text())
    if metadata["id"] != 18467070:
        raise ValueError("Unexpected Zenodo record; refusing to mix releases")
    output = root / "data/manifests"
    manifest = {
        "schema_version": 1,
        "dataset": "Sherlock",
        "release": "v3",
        "release_evidence": "Pinned Zenodo record page and changelog; API metadata.version is absent",
        "zenodo_record": 18467070,
        "doi": metadata["metadata"]["doi"],
        "source_url": "https://zenodo.org/records/18467070",
        "metadata_sha256": hashlib.sha256(metadata_path.read_bytes()).hexdigest(),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "phase1_complete": False,
        "event_counts": None,
        "event_count_note": "Not inferred from publications; semantic audit is separate from archive inventory.",
        "archives": [],
    }
    for remote in sorted(metadata["files"], key=lambda item: item["key"]):
        name = remote["key"]
        if not name.endswith(".zip"):
            continue
        if PurePosixPath(name).name != name:
            raise ValueError("Unsafe filename in metadata")
        archive = root / "data/raw/sherlock/v3" / name
        part = archive.with_suffix(".zip.part")
        path = archive if archive.exists() else part
        item = {
            "filename": name,
            "source_url": remote["links"]["self"],
            "expected_bytes": remote["size"],
            "expected_checksum": remote["checksum"],
            "local_path": str(path.relative_to(root)),
            "local_bytes": path.stat().st_size if path.exists() else 0,
            "status": "missing",
        }
        manifest["archives"].append(item)
        if not path.exists():
            continue
        if item["local_bytes"] != remote["size"]:
            item["status"] = "incomplete" if item["local_bytes"] < remote["size"] else "size_mismatch"
            print(f"{name}: {item['status']} ({item['local_bytes']}/{remote['size']} bytes)", flush=True)
            continue
        cache_path = output / (name + ".verified.json")
        stat = path.stat()
        fingerprint = {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
        cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
        if cache.get("fingerprint") == fingerprint and cache.get("expected_checksum") == remote["checksum"]:
            hashes = cache["hashes"]
        else:
            print(f"{name}: computing MD5 and SHA256", flush=True)
            hashes = digest(path)
        item.update(hashes)
        if "md5:" + hashes["md5"] != remote["checksum"]:
            item["status"] = "checksum_mismatch"
            continue
        # Cache only successful full-file verification; renaming preserves mtime.
        cache_path.write_text(json.dumps({"fingerprint": fingerprint, "hashes": hashes,
                                          "expected_checksum": remote["checksum"]}, indent=2) + "\n")
        if path == part:
            part.rename(archive)
        item["local_path"] = str(archive.relative_to(root))
        with zipfile.ZipFile(archive) as zipped:
            members = []
            for member in zipped.infolist():
                p = PurePosixPath(member.filename)
                if p.is_absolute() or ".." in p.parts:
                    raise ValueError(f"Unsafe archive path: {member.filename}")
                members.append({"path": member.filename, "bytes": member.file_size,
                                "compressed_bytes": member.compress_size,
                                "crc32": f"{member.CRC:08x}", "directory": member.is_dir(),
                                "provisional_category": category(member.filename)})
        inventory_path = output / (name + ".members.json")
        inventory_path.write_text(json.dumps(members, indent=2) + "\n")
        item.update(status="verified", member_count=len(members),
                    uncompressed_bytes=sum(m["bytes"] for m in members),
                    member_inventory=str(inventory_path.relative_to(root)))
        print(f"{name}: verified; {len(members)} members", flush=True)
    manifest["acquisition_complete"] = all(a["status"] == "verified" for a in manifest["archives"])
    # Preserve completed content-audit status only while report/archive hashes match.
    summary_path = output / "content_audit/summary.json"
    if manifest["acquisition_complete"] and summary_path.exists():
        summary = json.loads(summary_path.read_text())
        valid = summary.get("status") == "complete_with_documented_limitations"
        by_hash = {r["archive_sha256"]: r for r in summary.get("reports", [])}
        valid = valid and len(by_hash) == len(manifest["archives"]) == 3
        for item in manifest["archives"]:
            report = by_hash.get(item["sha256"])
            if report is None:
                valid = False
                continue
            report_path = root / report["path"]
            if not report_path.is_file() or hashlib.sha256(report_path.read_bytes()).hexdigest() != report["sha256"]:
                valid = False
        if valid:
            manifest["phase1_complete"] = True
            manifest["event_counts"] = [{k: r[k] for k in ("scenario", "recording", "events", "cyber", "benign")} for r in summary["recordings"]]
            manifest["event_count_note"] = "All local IPAL events cross-checked at exact raw procedure start timestamps and malicious flags."
            manifest["content_audit"] = {"summary": str(summary_path.relative_to(root)),
                                         "summary_sha256": hashlib.sha256(summary_path.read_bytes()).hexdigest(),
                                         "scope": summary["coverage"], "unknowns": summary["unknowns"]}
    target = output / "sherlock_manifest.json"
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, indent=2) + "\n")
    temporary.replace(target)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = audit(args.root)
    raise SystemExit(0 if result["acquisition_complete"] else 2)
