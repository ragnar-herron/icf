//! Hermetic replay of a captured live F5 break/fix run.
//!
//! This test never touches the network. It consumes the artifacts produced
//! by `scripts/live_break_fix.py` (which DID touch the real device):
//!
//!   - `live_state/ledger_input.json`      (flat manifest)
//!   - `live_state/manifest.json`          (nested human manifest)
//!   - `live_state/preflight.json`         (full sys/global-settings snapshot)
//!   - `blobstore/live/sha256/<aa>/<..>`   (baseline / break / post-fix blobs)
//!   - `ledgers/live/break_fix.jsonl`      (the 13-record live ledger)
//!
//! If any of the following properties is ever broken, this test fails,
//! which in turn fails CI:
//!
//!   - baseline blob and post-fix blob are byte-identical
//!   - break blob differs from baseline blob
//!   - the recorded blob SHA-256 values match the actual file contents
//!   - `build_live_break_fix_ledger` reproduces the committed ledger
//!     byte-for-byte from the manifest + blobs (no hidden state)
//!   - the independent offline verifier replays the ledger end-to-end

use std::fs;
use std::path::PathBuf;

use icf::{build_live_break_fix_ledger, sha256_hex, verify_ledger_path};

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

#[test]
fn live_replay_reproduces_ledger_and_invariants_hold() {
    let root = repo_root();
    let manifest = root.join("live_state").join("ledger_input.json");
    let committed_ledger = root.join("ledgers").join("live").join("break_fix.jsonl");

    let manifest_text = fs::read_to_string(&manifest).expect(
        "live_state/ledger_input.json must be present; run scripts/live_break_fix.py first",
    );
    let committed = fs::read_to_string(&committed_ledger)
        .expect("ledgers/live/break_fix.jsonl must be present");

    let baseline_rel = extract(&manifest_text, "baseline_blob_path");
    let baseline_hash = extract(&manifest_text, "baseline_blob_sha256");
    let break_rel = extract(&manifest_text, "break_blob_path");
    let break_hash = extract(&manifest_text, "break_blob_sha256");
    let post_fix_rel = extract(&manifest_text, "post_fix_blob_path");
    let post_fix_hash = extract(&manifest_text, "post_fix_blob_sha256");

    let baseline_bytes = fs::read(root.join(&baseline_rel)).expect("baseline blob present");
    let break_bytes = fs::read(root.join(&break_rel)).expect("break blob present");
    let post_fix_bytes = fs::read(root.join(&post_fix_rel)).expect("post-fix blob present");

    assert_eq!(
        sha256_hex(&baseline_bytes),
        baseline_hash,
        "baseline blob bytes must match recorded sha256"
    );
    assert_eq!(
        sha256_hex(&break_bytes),
        break_hash,
        "break blob bytes must match recorded sha256"
    );
    assert_eq!(
        sha256_hex(&post_fix_bytes),
        post_fix_hash,
        "post-fix blob bytes must match recorded sha256"
    );
    assert_eq!(
        baseline_bytes, post_fix_bytes,
        "post-fix blob MUST be byte-identical to baseline (device restored)"
    );
    assert_ne!(
        baseline_bytes, break_bytes,
        "break blob MUST differ from baseline"
    );

    let temp_out = std::env::temp_dir().join("icf_live_replay.jsonl");
    let summary = build_live_break_fix_ledger(&manifest, &temp_out).expect("replay must succeed");
    assert_eq!(summary.record_count, 13);
    assert_eq!(summary.baseline_blob_sha256, baseline_hash);
    assert_eq!(summary.break_blob_sha256, break_hash);
    assert_eq!(summary.post_fix_blob_sha256, post_fix_hash);

    let replayed = fs::read_to_string(&temp_out).expect("replayed ledger readable");
    assert_eq!(
        replayed, committed,
        "replay of captured manifest + blobs must reproduce the committed live ledger byte-for-byte"
    );

    verify_ledger_path(
        committed_ledger
            .to_str()
            .expect("committed ledger path is utf-8"),
    )
    .expect("independent offline verifier must accept the live ledger");

    let _ = fs::remove_file(&temp_out);
}

fn extract(text: &str, key: &str) -> String {
    let needle = format!("\"{key}\"");
    let start = text
        .find(&needle)
        .unwrap_or_else(|| panic!("manifest missing `{key}`"));
    let after = &text[start + needle.len()..];
    let colon = after.find(':').expect("colon");
    let rest = after[colon + 1..].trim_start();
    let body = rest.strip_prefix('"').expect("string value");
    let end = body.find('"').expect("closing quote");
    body[..end].to_string()
}
