use icf::{
    build_live_break_fix_ledger, build_live_campaign_ledger, coalgebra_report_markdown,
    distinction_report_markdown, distinction_stig_export_json, distinction_stig_report_markdown,
    evaluate_live_json, maturity_partials_report_markdown, maturity_report_markdown,
    verify_ledger_path,
    verify_maturity_fixture, write_break_fix_demo_ledger, write_p0a_demo_ledger,
};

fn main() {
    if let Err(err) = run() {
        eprintln!("{err}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), String> {
    let args: Vec<String> = std::env::args().collect();
    match args.as_slice() {
        [_bin, command, subcommand] if command == "demo" && subcommand == "p0a" => {
            let path = "ledgers/demo/p0a.jsonl";
            write_p0a_demo_ledger(path)?;
            println!("{path}");
            Ok(())
        }
        [_bin, command, subcommand] if command == "demo" && subcommand == "break-fix" => {
            let path = "ledgers/demo/break_fix.jsonl";
            write_break_fix_demo_ledger(path)?;
            println!("{path}");
            Ok(())
        }
        [_bin, command, subcommand, path] if command == "ledger" && subcommand == "verify" => {
            verify_ledger_path(path)?;
            println!("ok");
            Ok(())
        }
        [_bin, command, subcommand] if command == "coalgebra" && subcommand == "report" => {
            println!("{}", coalgebra_report_markdown(false)?);
            Ok(())
        }
        [_bin, command, subcommand] if command == "distinction" && subcommand == "report" => {
            println!("{}", distinction_report_markdown(false)?);
            Ok(())
        }
        [_bin, command, subcommand, flag]
            if command == "distinction"
                && subcommand == "report"
                && flag == "--fail-on-regression" =>
        {
            println!("{}", distinction_report_markdown(true)?);
            Ok(())
        }
        [_bin, command, subcommand]
            if command == "distinction" && subcommand == "stig-report" =>
        {
            println!("{}", distinction_stig_report_markdown(false)?);
            Ok(())
        }
        [_bin, command, subcommand, flag]
            if command == "distinction"
                && subcommand == "stig-report"
                && flag == "--fail-on-regression" =>
        {
            println!("{}", distinction_stig_report_markdown(true)?);
            Ok(())
        }
        [_bin, command, subcommand]
            if command == "distinction" && subcommand == "stig-export" =>
        {
            println!("{}", distinction_stig_export_json()?);
            Ok(())
        }
        [_bin, command, subcommand, path]
            if command == "distinction" && subcommand == "stig-export" =>
        {
            let json = distinction_stig_export_json()?;
            std::fs::write(path, &json)
                .map_err(|e| format!("failed to write {path}: {e}"))?;
            println!("{path}");
            Ok(())
        }
        [_bin, command, subcommand, path]
            if command == "evaluate" && subcommand == "live" =>
        {
            let request = std::fs::read_to_string(path)
                .map_err(|e| format!("failed to read {path}: {e}"))?;
            println!("{}", evaluate_live_json(&request)?);
            Ok(())
        }
        [_bin, command, subcommand, flag]
            if command == "coalgebra" && subcommand == "report" && flag == "--fail-on-missing-core" =>
        {
            println!("{}", coalgebra_report_markdown(true)?);
            Ok(())
        }
        [_bin, command, subcommand] if command == "maturity" && subcommand == "report" => {
            println!("{}", maturity_report_markdown(false)?);
            Ok(())
        }
        [_bin, command, subcommand, path]
            if command == "maturity" && subcommand == "verify-fixture" =>
        {
            println!("{}", verify_maturity_fixture(path)?);
            Ok(())
        }
        [_bin, command, subcommand, flag]
            if command == "maturity" && subcommand == "report" && flag == "--partials-only" =>
        {
            println!("{}", maturity_partials_report_markdown(false)?);
            Ok(())
        }
        [_bin, command, subcommand, flag]
            if command == "maturity" && subcommand == "report" && flag == "--fail-on-missing-core" =>
        {
            println!("{}", maturity_report_markdown(true)?);
            Ok(())
        }
        [_bin, command, subcommand, flag]
            if command == "maturity" && subcommand == "report" && flag == "--fail-on-partial" =>
        {
            println!("{}", maturity_partials_report_markdown(true)?);
            Ok(())
        }
        [_bin, command, subcommand, manifest_path, out_path]
            if command == "live" && subcommand == "break-fix" =>
        {
            let summary = build_live_break_fix_ledger(manifest_path, out_path)?;
            verify_ledger_path(out_path)?;
            println!("{}", summary.to_markdown());
            println!("verified: {}", summary.out_path);
            Ok(())
        }
        [_bin, command, subcommand, manifest_path, outcome_path, out_path]
            if command == "live" && subcommand == "campaign" =>
        {
            let summary = build_live_campaign_ledger(manifest_path, outcome_path, out_path)?;
            verify_ledger_path(out_path)?;
            println!("{}", summary.to_markdown());
            println!("verified: {}", summary.out_path);
            Ok(())
        }
        _ => Err("usage: icf demo p0a | icf demo break-fix | icf ledger verify <path> | icf coalgebra report [--fail-on-missing-core] | icf distinction report [--fail-on-regression] | icf distinction stig-report [--fail-on-regression] | icf distinction stig-export [<path>] | icf maturity report [--partials-only|--fail-on-missing-core|--fail-on-partial] | icf maturity verify-fixture <path> | icf live break-fix <manifest.json> <out.jsonl> | icf live campaign <manifest.json> <outcomes.json> <out.jsonl>".to_string()),
    }
}
