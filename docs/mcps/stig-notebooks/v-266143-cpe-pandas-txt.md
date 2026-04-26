
{
"cells": [
{
"cell_type": "markdown",
"metadata": {},
"source": [
"# V-266143 SQL-to-Pandas CPE Lifecycle\n",
"\n",
"Requirement: Enforce identity-, role-, or attribute-based authorization policies in APM access policy\n",
"\n",
"This notebook reconstructs the carrier-law-comparison-pressure path from the validator artifacts.\n"
]
},
{
"cell_type": "code",
"execution_count": null,
"metadata": {},
"outputs": [],
"source": [
"from pathlib import Path\n",
"import json\n",
"import pandas as pd\n",
"\n",
"VULN_ID = \"V-266143\"\n",
"TARGET_HOSTNAME = None\n",
"TARGET_IP_ADDRESS = None\n",
"OUTPUT_DIR = None\n",
"for candidate in [Path.cwd().resolve(), Path.cwd().resolve().parent, Path(\"..\").resolve()]:\n",
" if (candidate / \"domain_observations.jsonl\").exists():\n",
" OUTPUT_DIR = candidate\n",
" break\n",
"if OUTPUT_DIR is None:\n",
" raise FileNotFoundError(\"Could not locate domain_observations.jsonl\")\n",
"\n",
"domain_observations_df = pd.read_json(OUTPUT_DIR / \"domain_observations.jsonl\", lines=True)\n",
"status_report_df = pd.read_csv(OUTPUT_DIR / \"stig_status_report.csv\")\n",
"formal_adjudications_df = pd.read_json(OUTPUT_DIR / \"formal_adjudications.jsonl\", lines=True)\n",
"execution_trace_df = pd.read_json(OUTPUT_DIR / \"execution_trace.jsonl\", lines=True)\n",
"with (OUTPUT_DIR / \"resolved_contracts.json\").open(\"r\", encoding=\"utf-8\") as handle:\n",
" contracts_df = pd.DataFrame(json.load(handle).get(\"contracts\", []))\n",
"\n",
"def _scope(frame):\n",
" scoped = frame[frame[\"vuln_id\"] == VULN_ID].copy()\n",
" if TARGET_HOSTNAME:\n",
" scoped = scoped[scoped[\"hostname\"] == TARGET_HOSTNAME].copy()\n",
" if TARGET_IP_ADDRESS:\n",
" scoped = scoped[scoped[\"ip_address\"] == TARGET_IP_ADDRESS].copy()\n",
" if scoped.empty:\n",
" raise ValueError(\"No scoped rows found\")\n",
" return scoped.sort_values([column for column in [\"hostname\", \"ip_address\", \"run_timestamp\"] if column in scoped.columns], kind=\"stable\")\n",
"\n",
"obs_row = _scope(domain_observations_df).iloc[0].to_dict()\n",
"contract_row = contracts_df[contracts_df[\"vuln_id\"] == VULN_ID].iloc[0].to_dict()\n",
"structured_evidence = dict(obs_row.get(\"structured_evidence\") or {})\n",
"print(\"Selected host context:\", {\"hostname\": obs_row.get(\"hostname\"), \"ip_address\": obs_row.get(\"ip_address\"), \"run_timestamp\": obs_row.get(\"run_timestamp\")})\n",
"\n",
"def _rest_tables(row):\n",
" tables = {}\n",
" for endpoint, payload in (row.get(\"rest\") or {}).items():\n",
" if isinstance(payload, dict) and isinstance(payload.get(\"items\"), list):\n",
" tables[endpoint] = pd.DataFrame(payload.get(\"items\", []))\n",
" elif isinstance(payload, dict):\n",
" tables[endpoint] = pd.DataFrame([payload]) if payload else pd.DataFrame()\n",
" else:\n",
" tables[endpoint] = pd.DataFrame()\n",
" return tables\n",
"\n",
"def _tmsh_tables(row):\n",
" tables = {}\n",
" for command, payload in (row.get(\"tmsh\") or {}).items():\n",
" if isinstance(payload, list):\n",
" tables[command] = pd.DataFrame(payload)\n",
" elif isinstance(payload, dict):\n",
" tables[command] = pd.DataFrame([payload])\n",
" elif payload in [None, \"\"]:\n",
" tables[command] = pd.DataFrame()\n",
" else:\n",
" tables[command] = pd.DataFrame([{\"raw\": str(payload)}])\n",
" return tables\n",
"\n",
"def _trace_scope(frame):\n",
" scoped = frame[frame[\"vuln_id\"] == VULN_ID].copy()\n",
" if TARGET_HOSTNAME:\n",
" scoped = scoped[scoped[\"hostname\"] == TARGET_HOSTNAME].copy()\n",
" if TARGET_IP_ADDRESS:\n",
" scoped = scoped[scoped[\"ip_address\"] == TARGET_IP_ADDRESS].copy()\n",
" return scoped.sort_values([column for column in [\"hostname\", \"ip_address\", \"run_timestamp\"] if column in scoped.columns], kind=\"stable\")\n",
"\n",
"def _artifact_frame(artifact_name):\n",
" scoped = _trace_scope(execution_trace_df)\n",
" scoped = scoped[scoped[\"artifact\"] == artifact_name].copy()\n",
" rows = []\n",
" for row in scoped.get(\"row\", []):\n",
" rows.append(row if isinstance(row, dict) else {})\n",
" return pd.DataFrame(rows)\n",
"\n",
"REST_TABLES = _rest_tables(obs_row)\n",
"TMSH_TABLES = _tmsh_tables(obs_row)\n",
"\n",
"def _all_source_tables():\n",
" rows = []\n",
" for endpoint, frame in REST_TABLES.items():\n",
" if frame.empty:\n",
" rows.append(pd.DataFrame([{\"source_endpoint\": endpoint, \"carrier_coordinate\": f\"{endpoint}::empty\"}]))\n",
" continue\n",
" local = frame.copy()\n",
" local[\"source_endpoint\"] = endpoint\n",
" if \"carrier_coordinate\" not in local.columns:\n",
" if \"fullPath\" in local.columns:\n",
" local[\"carrier_coordinate\"] = local[\"fullPath\"].astype(str)\n",
" elif \"name\" in local.columns:\n",
" local[\"carrier_coordinate\"] = local[\"name\"].astype(str)\n",
" else:\n",
" local[\"carrier_coordinate\"] = [f\"{endpoint}::row:{i}\" for i in range(len(local))]\n",
" rows.append(local)\n",
" for command, frame in TMSH_TABLES.items():\n",
" if frame.empty:\n",
" rows.append(pd.DataFrame([{\"source_endpoint\": command, \"carrier_coordinate\": f\"{command}::empty\"}]))\n",
" continue\n",
" local = frame.copy()\n",
" local[\"source_endpoint\"] = command\n",
" if \"carrier_coordinate\" not in local.columns:\n",
" if \"fullPath\" in local.columns:\n",
" local[\"carrier_coordinate\"] = local[\"fullPath\"].astype(str)\n",
" elif \"name\" in local.columns:\n",
" local[\"carrier_coordinate\"] = local[\"name\"].astype(str)\n",
" else:\n",
" local[\"carrier_coordinate\"] = [f\"{command}::row:{i}\" for i in range(len(local))]\n",
" rows.append(local)\n",
" return pd.concat(rows, ignore_index=True, sort=False) if rows else pd.DataFrame()\n",
"\n",
"def _source_frame_for(lawful_source):\n",
" if lawful_source in REST_TABLES:\n",
" return REST_TABLES[lawful_source].copy()\n",
" if lawful_source in TMSH_TABLES:\n",
" return TMSH_TABLES[lawful_source].copy()\n",
" for candidate in [part.strip() for part in str(lawful_source).split(\"+\")]:\n",
" if candidate in REST_TABLES:\n",
" return REST_TABLES[candidate].copy()\n",
" if candidate in TMSH_TABLES:\n",
" return TMSH_TABLES[candidate].copy()\n",
" return pd.DataFrame()\n",
"\n",
"PROPERTY_ALIASES = {\n",
" \"options\": [\"options\", \"tmOptions\"],\n",
" \"tmOptions\": [\"tmOptions\", \"options\"],\n",
" \"destination_port\": [\"destination_port\", \"destination\"],\n",
" \"minimumLength\": [\"minimumLength\", \"minLength\"],\n",
" \"statusAge\": [\"statusAge\", \"maxAge\"],\n",
" \"partitionAccess\": [\"partitionAccess\", \"partition-access\"],\n",
" \"partition-access\": [\"partitionAccess\", \"partition-access\"],\n",
" \"guiSecurityBanner\": [\"guiSecurityBanner\"],\n",
" \"guiSecurityBannerText\": [\"guiSecurityBannerText\"],\n",
" \"value\": [\"value\", \"raw\"],\n",
" \"include\": [\"include\", \"raw\"],\n",
" \"logSettings\": [\"logSettings\", \"logSetting\", \"logSettingsReference\", \"logSettingReference\"],\n",
" \"fwEnforcedPolicy\": [\"fwEnforcedPolicy\", \"fwEnforcedPolicyReference\"],\n",
" \"addressSpaceExcludeSubnet\": [\"addressSpaceExcludeSubnet\", \"addressSpaceExcludeReference\"],\n",
" \"addressSpaceExcludeDnsName\": [\"addressSpaceExcludeDnsName\", \"addressSpaceExcludeReference\"],\n",
" \"ipv6AddressSpaceExcludeSubnet\": [\"ipv6AddressSpaceExcludeSubnet\", \"addressSpaceExcludeReference\"],\n",
" \"asm_policies_active\": [\"active\"],\n",
" \"virtual_server_security_policy\": [\"virtualServers\"],\n",
" \"auto_update_check\": [\"autoCheck\"],\n",
" \"live_update_realtime\": [\"frequency\"],\n",
" \"classification\": [\"classification\", \"raw\"],\n",
" \"publisher\": [\"publisher\", \"raw\"],\n",
"}\n",
"\n",
"def _candidate_properties(lawful_property):\n",
" return PROPERTY_ALIASES.get(str(lawful_property), [str(lawful_property)])\n",
"\n",
"def _materialize_carrier_frame(frame, source_name):\n",
" local = frame.copy()\n",
" if local.empty:\n",
" return pd.DataFrame([{\"source_endpoint\": source_name, \"carrier_coordinate\": f\"{source_name}::empty\"}])\n",
" if \"source_endpoint\" not in local.columns:\n",
" local[\"source_endpoint\"] = source_name\n",
" if \"carrier_coordinate\" not in local.columns:\n",
" if \"fullPath\" in local.columns:\n",
" local[\"carrier_coordinate\"] = local[\"fullPath\"].astype(str)\n",
" elif \"name\" in local.columns:\n",
" local[\"carrier_coordinate\"] = local[\"name\"].astype(str)\n",
" else:\n",
" local[\"carrier_coordinate\"] = [f\"{source_name}::row:{i}\" for i in range(len(local))]\n",
" return local\n",
"\n",
"def _derive_observed_values(frame, lawful_property):\n",
" local = _materialize_carrier_frame(frame, \"derived\")\n",
" candidates = _candidate_properties(lawful_property)\n",
" for candidate in candidates:\n",
" if candidate in local.columns:\n",
" return local[[\"carrier_coordinate\"]].assign(observed_value=local[candidate], observed_property=candidate)\n",
" if \"destination\" in local.columns and lawful_property == \"destination_port\":\n",
" derived = local[\"destination\"].astype(str).str.extract(r\":(\\d+)$\")[0].astype(\"Int64\")\n",
" return local[[\"carrier_coordinate\"]].assign(observed_value=derived, observed_property=\"destination -> destination_port\")\n",
" return pd.DataFrame(columns=[\"carrier_coordinate\", \"observed_value\", \"observed_property\"])\n"
]
},
{
"cell_type": "markdown",
"metadata": {},
"source": [
"## 1) O - Observation\n",
"\n",
"Pull back carrier rows and observed property values.\n"
]
},
{
"cell_type": "code",
"execution_count": null,
"metadata": {},
"outputs": [],
"source": [
"carrier_df = _artifact_frame(\"carrier_df\")\n",
"if carrier_df.empty:\n",
" carrier_df = _all_source_tables()\n",
"display(carrier_df)\n",
"carrier_df\n"
]
},
{
"cell_type": "markdown",
"metadata": {},
"source": [
"## 2) K - Schema\n",
"\n",
"Express the law as carrier object, lawful property, and admissible constraint.\n"
]
},
{
"cell_type": "markdown",
"metadata": {},
"source": [
"## 2a) K Preview - Embedded Law Rows\n",
"\n",
"Static law preview embedded by the generator so the lawful structure is visible even before notebook execution.\n",
"\n",
"| carrier_object | lawful_property | admissible_constraint | lawful_source |\n",
"|---|---|---|---|\n",
"| virtual server access boundary | source | must not remain '0.0.0.0/0' without narrower authorization controls | /mgmt/tm/ltm/virtual |\n",
"| virtual server access boundary | fwEnforcedPolicy | must be present when source is unrestricted to enforce identity/role/attribute authorization policy | /mgmt/tm/security/firewall/policy + /mgmt/tm/ltm/virtual |\n"
]
},
{
"cell_type": "code",
"execution_count": null,
"metadata": {},
"outputs": [],
"source": [
"lawful_structure_df = _artifact_frame(\"schema_df\")\n",
"if lawful_structure_df.empty:\n",
" lawful_structure_df = pd.DataFrame([{'carrier_object': 'virtual server access boundary', 'lawful_property': 'source', 'admissible_constraint': \"must not remain '0.0.0.0/0' without narrower authorization controls\", 'expected_value': None, 'lawful_source': '/mgmt/tm/ltm/virtual'}, {'carrier_object': 'virtual server access boundary', 'lawful_property': 'fwEnforcedPolicy', 'admissible_constraint': 'must be present when source is unrestricted to enforce identity/role/attribute authorization policy', 'expected_value': None, 'lawful_source': '/mgmt/tm/security/firewall/policy + /mgmt/tm/ltm/virtual'}])\n",
"lawful_structure_df\n"
]
},
{
"cell_type": "markdown",
"metadata": {},
"source": [
"## 3) C - Comparison\n"
]
},
{
"cell_type": "code",
"execution_count": null,
"metadata": {},
"outputs": [],
"source": [
"comparison_df = _artifact_frame(\"comparison_df\")\n",
"comparison_df\n"
]
},
{
"cell_type": "markdown",
"metadata": {},
"source": [
"## 4) Lambda - Pressure\n"
]
},
{
"cell_type": "code",
"execution_count": null,
"metadata": {},
"outputs": [],
"source": [
"pressure_df = _artifact_frame(\"pressure_df\")\n",
"if pressure_df.empty and not comparison_df.empty:\n",
" pressure_df = comparison_df[[\"carrier_coordinate\",\"measurable\"]].copy()\n",
" pressure_df[\"pressure_magnitude\"] = (~comparison_df[\"match\"]).astype(float)\n",
" pressure_df[\"pressure_cause\"] = comparison_df[\"match\"].apply(lambda ok: \"carrier value satisfies admissible constraint\" if ok else \"carrier value violates admissible constraint\")\n",
"pressure_df\n"
]
},
{
"cell_type": "markdown",
"metadata": {},
"source": [
"## 5) Sigma - Strategy\n"
]
},
{
"cell_type": "code",
"execution_count": null,
"metadata": {},
"outputs": [],
"source": [
"strategy_df = _artifact_frame(\"strategy_df\")\n",
"if strategy_df.empty and not pressure_df.empty:\n",
" strategy_df = pressure_df.copy()\n",
" strategy_df[\"candidate_interventions\"] = strategy_df[\"pressure_magnitude\"].apply(lambda value: [\"REMEDIATE\", \"DEFER_AND_RECOLLECT\"] if value > 0 else [\"NO_OP\", \"MONITOR\"])\n",
" strategy_df[\"selected_intervention\"] = strategy_df[\"pressure_magnitude\"].apply(lambda value: \"REMEDIATE\" if value > 0 else \"NO_OP\")\n",
" strategy_df[\"selection_rationale\"] = strategy_df[\"pressure_cause\"]\n",
"strategy_df\n"
]
},
{
"cell_type": "markdown",
"metadata": {},
"source": [
"## 6) M - Realization\n"
]
},
{
"cell_type": "code",
"execution_count": null,
"metadata": {},
"outputs": [],
"source": [
"realization_df = _artifact_frame(\"realization_df\")\n",
"if realization_df.empty and not strategy_df.empty:\n",
" realization_df = strategy_df[[\"carrier_coordinate\",\"selected_intervention\"]].copy()\n",
" realization_df[\"lawful_channel\"] = contract_row.get(\"runtime_family\")\n",
" realization_df[\"verification_plan\"] = \"re-observe carrier and rebuild comparison/pressure\"\n",
"realization_df\n"
]
},
{
"cell_type": "markdown",
"metadata": {},
"source": [
"## 7) W - Work\n"
]
},
{
"cell_type": "code",
"execution_count": null,
"metadata": {},
"outputs": [],
"source": [
"work_df = _artifact_frame(\"work_df\")\n",
"if work_df.empty:\n",
" work_df = pd.DataFrame([{\"inspection_work_units\": len(locals().get(\"carrier_df\", pd.DataFrame())), \"comparison_work_units\": len(comparison_df), \"mutation_work_units\": int((strategy_df[\"selected_intervention\"] != \"NO_OP\").sum()), \"verification_work_units\": len(pressure_df)}])\n",
"work_df\n"
]
},
{
"cell_type": "markdown",
"metadata": {},
"source": [
"## 8) V - Value\n"
]
},
{
"cell_type": "code",
"execution_count": null,
"metadata": {},
"outputs": [],
"source": [
"value_df = _artifact_frame(\"value_df\")\n",
"if value_df.empty:\n",
" value_df = pd.DataFrame([{\"computed_status\": \"NOT_A_FINDING\" if float(pressure_df[\"pressure_magnitude\"].sum()) == 0.0 else \"OPEN\", \"residual_pressure\": float(pressure_df[\"pressure_magnitude\"].sum())}])\n",
"value_df\n"
]
},
{
"cell_type": "markdown",
"metadata": {},
"source": [
"## 9) P - Persistence\n"
]
},
{
"cell_type": "code",
"execution_count": null,
"metadata": {},
"outputs": [],
"source": [
"persistence_df = _artifact_frame(\"persistence_df\")\n",
"if persistence_df.empty and not pressure_df.empty:\n",
" persistence_df = pressure_df.copy()\n",
" persistence_df[\"lineage_path\"] = \"carrier_df -> schema_df -> comparison_df -> pressure_df\"\n",
"persistence_df\n"
]
},
{
"cell_type": "markdown",
"metadata": {},
"source": [
"## 10) J - Self-Index\n"
]
},
{
"cell_type": "code",
"execution_count": null,
"metadata": {},
"outputs": [],
"source": [
"self_index_df = _artifact_frame(\"self_index_df\")\n",
"if self_index_df.empty and not pressure_df.empty:\n",
" self_index_df = pressure_df.copy()\n",
" self_index_df[\"discrepancy_motif\"] = self_index_df[\"pressure_cause\"]\n",
" self_index_df[\"next_cycle_hint\"] = self_index_df[\"pressure_magnitude\"].apply(lambda value: \"prioritize this coordinate\" if value > 0 else \"monitor only\")\n",
"self_index_df\n"
]
},
{
"cell_type": "markdown",
"metadata": {},
"source": [
"## 11) E - Error\n"
]
},
{
"cell_type": "code",
"execution_count": null,
"metadata": {},
"outputs": [],
"source": [
"error_df = _artifact_frame(\"error_df\")\n",
"if error_df.empty and not pressure_df.empty:\n",
" error_df = pressure_df.copy()\n",
" error_df[\"resolution_state\"] = error_df[\"pressure_magnitude\"].apply(lambda value: \"deficit_cleared\" if value == 0 else \"residual_pressure_present\")\n",
" error_df[\"next_corrective_action\"] = error_df[\"resolution_state\"].apply(lambda value: \"no residual mismatch\" if value == \"deficit_cleared\" else \"retry realization or challenge law/runtime assumptions\")\n",
"error_df\n"
]
}
],
"metadata": {
"kernelspec": {
"display_name": "Python 3",
"language": "python",
"name": "python3"
},
"language_info": {
"name": "python",
"version": "3.x"
}
},
"nbformat": 4,
"nbformat_minor": 5
}