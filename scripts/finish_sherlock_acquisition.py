#!/usr/bin/env python3
"""Supervise downloads already running in this task, then verify local archives.

This finite job does not schedule future tasks. It updates the manifest every
minute and fails after 20 minutes without progress on an unfinished archive.
It never reports Phase 1 as complete; full semantic audit is still required.
"""

import json
import time
from datetime import datetime, timezone

from audit_sherlock import ROOT, audit
from probe_sherlock import probe


def main():
    progress = {}
    status_path = ROOT / "data/manifests/acquisition_status.json"
    start = time.monotonic()
    while True:
        manifest = audit(ROOT)
        now = time.monotonic()
        stalled = []
        for item in manifest["archives"]:
            name = item["filename"]
            previous_size, last_progress = progress.get(name, (None, now))
            if item["local_bytes"] != previous_size:
                last_progress = now
            progress[name] = (item["local_bytes"], last_progress)
            if item["status"] != "verified" and now - last_progress > 1200:
                stalled.append(name)
        bad = [a["filename"] for a in manifest["archives"] if a["status"] in ("checksum_mismatch", "size_mismatch")]
        done = manifest["acquisition_complete"]
        status = {"updated_at_utc": datetime.now(timezone.utc).isoformat(),
                  "state": "verified" if done else "failed" if bad or stalled else "downloading",
                  "checksum_or_size_failures": bad, "stalled_archives": stalled,
                  "elapsed_seconds": round(now-start),
                  "downloaded_bytes": sum(a["local_bytes"] for a in manifest["archives"]),
                  "expected_bytes": sum(a["expected_bytes"] for a in manifest["archives"]),
                  "semantic_audit_complete": False}
        status_path.write_text(json.dumps(status, indent=2) + "\n")
        if done:
            probe(ROOT)
            print("All three archives verified. Semantic audit remains pending.", flush=True)
            return 0
        if bad or stalled:
            print(json.dumps(status), flush=True)
            return 1
        time.sleep(60)


if __name__ == "__main__":
    raise SystemExit(main())
