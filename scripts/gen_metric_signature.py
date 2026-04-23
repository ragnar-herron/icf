#!/usr/bin/env python3
"""
Produce MetricSignature.json and metric_checkpoint.jsonl for gate D6.

Signature envelope (demo-grade):
- Every file in the curated metric set is hashed with SHA-256 over its raw
  bytes (no canonicalisation; files are static JSON/Markdown committed to
  the repo).
- A digest_of_digests is SHA-256 over the joined "<path>\t<hex>\n" lines.
- CheckpointRecord references this digest_of_digests and the signer_id.

Production note: this commits the integrity surface but uses SHA-256 only.
Production MUST upgrade to Ed25519 signatures from the trust root (the
policy is declared in docs/BUILD_SPEC.md §6 CheckpointRecord).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import List

REPO = Path(__file__).resolve().parent.parent
METRIC_FILES: List[str] = [
    "fixtures/maturity/revision_0/metrics.json",
    "fixtures/maturity/revision_1/metrics.json",
    "coalgebra/stig_expert_critic/MaturationLogicStability.json",
    "coalgebra/stig_expert_critic/ScopeCoverageMatrix.json",
    "coalgebra/stig_expert_critic/PullbackBaseline.json",
    "coalgebra/stig_expert_critic/WHRReport.md",
]
OUT_SIG = REPO / "coalgebra" / "stig_expert_critic" / "MetricSignature.json"
OUT_CHECKPOINT = REPO / "ledgers" / "demo" / "metric_checkpoint.jsonl"


def sha256_hex_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    entries = []
    for rel in METRIC_FILES:
        full = REPO / rel
        data = full.read_bytes()
        entries.append({"path": rel, "sha256": sha256_hex_of_bytes(data), "bytes": len(data)})

    transcript = "".join(f"{e['path']}\t{e['sha256']}\n" for e in entries)
    digest_of_digests = sha256_hex_of_bytes(transcript.encode("utf-8"))

    signature = {
        "record_kind": "MetricSignature",
        "subject": "stig_expert_critic_p0a",
        "signer_id": "demo-attestor",
        "signature_algorithm": "sha256-commit",
        "signature_algorithm_note": (
            "Demo-grade content commitment. Production must replace this with an "
            "Ed25519 signature by the trust root; the key rotation policy is "
            "specified in docs/BUILD_SPEC.md §6 KeySetRecord."
        ),
        "digest_of_digests": digest_of_digests,
        "files": entries,
    }

    OUT_SIG.parent.mkdir(parents=True, exist_ok=True)
    OUT_SIG.write_text(json.dumps(signature, indent=2) + "\n", encoding="utf-8")

    checkpoint = {
        "record_kind": "CheckpointRecord",
        "record_id": "metric-checkpoint-1",
        "anchor_target": "coalgebra/stig_expert_critic/MetricSignature.json",
        "digest_of_digests": digest_of_digests,
        "signer_id": "demo-attestor",
        "external_anchor_note": (
            "In demo mode this checkpoint is committed alongside the signed manifest. "
            "In production it MUST be cross-posted to an external append-only notary "
            "so that silent edits to metrics in this repo are detectable."
        ),
    }

    OUT_CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    OUT_CHECKPOINT.write_text(json.dumps(checkpoint) + "\n", encoding="utf-8")

    print(f"wrote {OUT_SIG}")
    print(f"wrote {OUT_CHECKPOINT}")
    print(f"digest_of_digests={digest_of_digests}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
