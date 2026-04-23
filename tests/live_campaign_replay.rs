use std::fs;
use std::path::PathBuf;

use icf::{build_live_campaign_ledger, verify_ledger_path};

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

#[test]
fn live_campaign_replay_reproduces_ledger_and_verifies() {
    let root = repo_root();
    let manifest = root
        .join("live_state")
        .join("full_campaign")
        .join("manifest.json");
    let outcomes = root
        .join("coalgebra")
        .join("stig_expert_critic")
        .join("LiveControlOutcomeMatrix.json");
    let committed_ledger = root
        .join("ledgers")
        .join("live")
        .join("full_campaign.jsonl");

    let committed = fs::read_to_string(&committed_ledger)
        .expect("ledgers/live/full_campaign.jsonl must be present");
    let temp_out = std::env::temp_dir().join("icf_live_campaign_replay.jsonl");

    let summary = build_live_campaign_ledger(&manifest, &outcomes, &temp_out)
        .expect("campaign replay must succeed");
    assert_eq!(summary.control_count, 67);
    assert_eq!(summary.pass, 55);
    assert_eq!(summary.fail, 2);
    assert_eq!(summary.not_applicable, 5);
    assert_eq!(summary.blocked_external, 5);

    let replayed = fs::read_to_string(&temp_out).expect("replayed campaign ledger readable");
    assert_eq!(
        replayed, committed,
        "replay of campaign manifest + outcomes must reproduce the committed campaign ledger byte-for-byte"
    );

    verify_ledger_path(
        committed_ledger
            .to_str()
            .expect("committed campaign ledger path is utf-8"),
    )
    .expect("independent offline verifier must accept the campaign ledger");

    let _ = fs::remove_file(&temp_out);
}
