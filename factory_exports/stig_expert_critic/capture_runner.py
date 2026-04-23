from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from f5_client import F5Client


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
FACTORY_BUNDLE = DATA / "FactoryDistinctionBundle.json"

_bundle_cache: dict[str, Any] | None = None


def load_factory_bundle() -> dict[str, Any]:
    global _bundle_cache
    if _bundle_cache is None:
        _bundle_cache = json.loads(FACTORY_BUNDLE.read_text(encoding="utf-8"))
    return _bundle_cache


def recipe_for_vid(vid: str) -> dict[str, Any] | None:
    bundle = load_factory_bundle()
    for recipe in bundle.get("captureRecipes", []):
        if recipe.get("measurable_id") == vid:
            return recipe
    return None


def capture_raw_evidence(client: F5Client, control: dict[str, Any]) -> dict[str, str]:
    recipe = recipe_for_vid(str(control.get("vuln_id") or ""))
    evidence: dict[str, str] = {}
    seen: set[str] = set()
    sources = list((recipe or {}).get("sources") or [])
    if not sources:
        for command in control.get("tmsh_commands") or []:
            sources.append(
                {
                    "source_id": f"tmsh:{command}",
                    "kind": "Tmsh",
                    "locator": command,
                }
            )
        for endpoint in control.get("rest_endpoints") or []:
            sources.append(
                {
                    "source_id": f"rest:{endpoint}",
                    "kind": "Rest",
                    "locator": endpoint,
                }
            )
    for source in sources:
        locator = str(source.get("locator") or "").strip()
        if not locator or locator in seen:
            continue
        seen.add(locator)
        kind = str(source.get("kind") or "")
        try:
            if kind.lower() == "rest":
                evidence[locator] = json.dumps(client.get(locator))
            else:
                evidence[locator] = client.run_tmsh(locator)
        except Exception as exc:  # noqa: BLE001
            evidence[locator] = json.dumps({"available": False, "error": str(exc)})
    return evidence


def normalize_with_recipe(control: dict[str, Any], evidence: dict[str, str]) -> dict[str, Any]:
    vid = str(control.get("vuln_id") or "")
    recipe = recipe_for_vid(vid)
    if not recipe:
        return {
            "recipe": None,
            "fieldMap": {},
            "missingFields": list(control.get("evidence_required") or []),
        }
    field_map: dict[str, str] = {}
    missing_fields: list[str] = []
    for rule in recipe.get("extraction_rules", []):
        value = extract_rule_value(rule, recipe.get("sources") or [], evidence)
        field = str(rule.get("field") or "")
        if value is None:
            missing_fields.append(field)
        else:
            field_map[field] = value
    return {
        "recipe": recipe,
        "fieldMap": field_map,
        "missingFields": missing_fields,
    }


def extract_rule_value(
    rule: dict[str, Any],
    sources: list[dict[str, Any]],
    evidence: dict[str, str],
) -> str | None:
    source_ids = set(rule.get("source_ids") or [])
    for source in sources:
        source_id = str(source.get("source_id") or "")
        locator = str(source.get("locator") or "")
        if source_ids and source_id not in source_ids:
            continue
        raw = evidence.get(locator) or evidence.get(source_id) or ""
        if not raw:
            continue
        kind = str(source.get("kind") or "")
        if kind.lower() == "rest":
            value = extract_from_json(raw, rule)
        else:
            value = extract_from_tmsh(raw, rule)
        if value is not None:
            return value
    return None


def extract_from_tmsh(raw: str, rule: dict[str, Any]) -> str | None:
    props = sorted(
        {str(v) for v in rule.get("tmsh_property_candidates") or [] if str(v).strip()},
        key=len,
        reverse=True,
    )
    for prop in props:
        escaped = re.escape(prop)
        patterns = [
            rf"(?im)^\s*{escaped}\s+(.+?)\s*$",
            rf"(?im)\b{escaped}\s+([^\s\}}]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, raw)
            if match:
                return match.group(1).strip().strip('"')
    return None


def extract_from_json(raw: str, rule: dict[str, Any]) -> str | None:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    flat = flatten_json(payload)
    candidates = [str(v) for v in rule.get("json_pointer_candidates") or []]
    candidate_keys = {normalize_key(v) for v in candidates}
    alias_keys = {normalize_key(v) for v in rule.get("aliases") or []}
    for path, value in flat.items():
        if normalize_key(path) in candidate_keys:
            return value
        leaf = path.rsplit("/", 1)[-1]
        if normalize_key(leaf) in alias_keys:
            return value
    return None


def flatten_json(value: Any, path: str = "") -> dict[str, str]:
    flattened: dict[str, str] = {}
    if isinstance(value, dict):
        for key, inner in value.items():
            child = f"{path}/{key}" if path else f"/{key}"
            flattened.update(flatten_json(inner, child))
        return flattened
    if isinstance(value, list):
        for index, inner in enumerate(value):
            child = f"{path}/{index}" if path else f"/{index}"
            flattened.update(flatten_json(inner, child))
        return flattened
    flattened[path or "/"] = scalar_to_str(value)
    return flattened


def scalar_to_str(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return ""
    return str(value)


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())
