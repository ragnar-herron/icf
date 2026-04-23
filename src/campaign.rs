use std::fs;
use std::path::Path;

use serde_json::Value;

use crate::ledger::write_ledger;
use crate::model::{BatchRecord, ControlDispositionRecord, Record, ScopeRecord};

pub fn build_live_campaign_ledger(
    manifest_path: impl AsRef<Path>,
    outcome_matrix_path: impl AsRef<Path>,
    out_path: impl AsRef<Path>,
) -> Result<CampaignRunSummary, String> {
    let manifest: Value =
        serde_json::from_str(&fs::read_to_string(manifest_path.as_ref()).map_err(|err| {
            format!("failed to read {}: {err}", manifest_path.as_ref().display())
        })?)
        .map_err(|err| {
            format!(
                "failed to parse {}: {err}",
                manifest_path.as_ref().display()
            )
        })?;
    let outcomes: Value = serde_json::from_str(
        &fs::read_to_string(outcome_matrix_path.as_ref()).map_err(|err| {
            format!(
                "failed to read {}: {err}",
                outcome_matrix_path.as_ref().display()
            )
        })?,
    )
    .map_err(|err| {
        format!(
            "failed to parse {}: {err}",
            outcome_matrix_path.as_ref().display()
        )
    })?;

    let host = required_json_string(&manifest, "host")?;
    let hostname = required_json_string(&manifest, "hostname")?;
    let tmos_version = required_json_string(&manifest, "tmos_version")?;
    let snapshots = required_json_array(&manifest, "snapshots")?;
    let controls = required_json_array(&outcomes, "outcomes")?;

    let scope = ScopeRecord {
        record_id: "live-campaign-scope-1".to_string(),
        platform: "F5 BIG-IP".to_string(),
        tmos_version: tmos_version.clone(),
        module: "MULTI".to_string(),
        topology: "standalone".to_string(),
        credential_scope: format!(
            "admin over iControl REST (live campaign) | host={host} hostname={hostname}"
        ),
    };

    let mut records = vec![Record::Scope(scope)];
    let mut counts = CampaignCounts::default();

    for (index, control) in controls.iter().enumerate() {
        let vuln_id = required_json_string(control, "vuln_id")?;
        let disposition = required_json_string(control, "disposition")?;
        let rationale = required_json_string(control, "rationale")?;
        let evidence_names = required_json_string_array(control, "evidence")?;
        let mut evidence_blob_paths = Vec::new();
        let mut evidence_blob_sha256s = Vec::new();
        for evidence_name in evidence_names {
            let snapshot = find_snapshot(&snapshots, &evidence_name).ok_or_else(|| {
                format!(
                    "control {vuln_id}: evidence reference `{evidence_name}` missing from manifest"
                )
            })?;
            evidence_blob_paths.push(required_json_string(snapshot, "blob_path")?);
            evidence_blob_sha256s.push(required_json_string(snapshot, "blob_sha256")?);
        }
        counts.bump(&disposition);
        records.push(Record::ControlDisposition(ControlDispositionRecord {
            record_id: format!("live-control-disposition-{:03}", index + 1),
            control_id: vuln_id,
            disposition,
            rationale,
            evidence_blob_paths,
            evidence_blob_sha256s,
        }));
    }

    records.push(Record::Batch(BatchRecord {
        record_id: "live-campaign-batch-1".to_string(),
        batch_id: format!("live-full-campaign-{tmos_version}"),
        committed: true,
    }));

    write_ledger(out_path.as_ref(), &records)?;

    Ok(CampaignRunSummary {
        out_path: out_path.as_ref().display().to_string(),
        host,
        hostname,
        tmos_version,
        control_count: controls.len(),
        pass: counts.pass,
        fail: counts.fail,
        not_applicable: counts.not_applicable,
        blocked_external: counts.blocked_external,
    })
}

#[derive(Debug, Default)]
struct CampaignCounts {
    pass: usize,
    fail: usize,
    not_applicable: usize,
    blocked_external: usize,
}

impl CampaignCounts {
    fn bump(&mut self, disposition: &str) {
        match disposition {
            "pass" => self.pass += 1,
            "fail" => self.fail += 1,
            "not-applicable" => self.not_applicable += 1,
            "blocked-external" => self.blocked_external += 1,
            _ => {}
        }
    }
}

#[derive(Debug)]
pub struct CampaignRunSummary {
    pub out_path: String,
    pub host: String,
    pub hostname: String,
    pub tmos_version: String,
    pub control_count: usize,
    pub pass: usize,
    pub fail: usize,
    pub not_applicable: usize,
    pub blocked_external: usize,
}

impl CampaignRunSummary {
    pub fn to_markdown(&self) -> String {
        let mut output = String::new();
        output.push_str("# Live F5 full STIG campaign summary\n\n");
        output.push_str(&format!("- host: `{}`\n", self.host));
        output.push_str(&format!("- hostname: `{}`\n", self.hostname));
        output.push_str(&format!("- tmos_version: `{}`\n", self.tmos_version));
        output.push_str(&format!("- controls: {}\n", self.control_count));
        output.push_str(&format!("- pass: {}\n", self.pass));
        output.push_str(&format!("- fail: {}\n", self.fail));
        output.push_str(&format!("- not-applicable: {}\n", self.not_applicable));
        output.push_str(&format!("- blocked-external: {}\n", self.blocked_external));
        output.push_str(&format!("- ledger: `{}`\n", self.out_path));
        output
    }
}

fn required_json_string(value: &Value, key: &str) -> Result<String, String> {
    value
        .get(key)
        .and_then(Value::as_str)
        .map(ToString::to_string)
        .ok_or_else(|| format!("missing or invalid string key `{key}`"))
}

fn required_json_array<'a>(value: &'a Value, key: &str) -> Result<&'a [Value], String> {
    value
        .get(key)
        .and_then(Value::as_array)
        .map(Vec::as_slice)
        .ok_or_else(|| format!("missing or invalid array key `{key}`"))
}

fn required_json_string_array(value: &Value, key: &str) -> Result<Vec<String>, String> {
    required_json_array(value, key)?
        .iter()
        .map(|item| {
            item.as_str()
                .map(ToString::to_string)
                .ok_or_else(|| format!("key `{key}` must contain only strings"))
        })
        .collect()
}

fn find_snapshot<'a>(snapshots: &'a [Value], name: &str) -> Option<&'a Value> {
    snapshots
        .iter()
        .find(|snapshot| snapshot.get("name").and_then(Value::as_str) == Some(name))
}
