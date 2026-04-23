# STIG Expert Critic Governed Export

This export is a governed projection layer over backend-produced bundles.

Run:

```powershell
py -3 web_app.py --advisory-only
```

The browser renders typed bundles produced by `web_app.py` and
`live_evaluator.py`. It must not compute canonical STIG judgment or
adjudication semantics from raw evidence.

Core guards:

- Host changes clear all host-scoped truth state.
- Every semantic tab is pinned to the selected V-ID.
- Adjudication renders only after matching validation provenance exists.
- REST remediation remains advisory.
- Merge sequencing is verify -> merge -> save.
- Final truth tables render atomic backend comparison rows only.
- Live support requires replay, live verification, and promotion artifacts.
- Per-control legitimacy records are generated from artifact gates; the export does not infer capability.
- Adapter-family legitimacy records are also generated so promotion work can be tracked by family.
- The export also emits an `ExportProjectionGateRecord` at `/api/export_projection_gate`.
- Evidence backlog records are emitted for both controls and families so missing artifact classes are explicit.
- A `CapabilityConsistencyRecord` is emitted at `/api/capability_consistency` to catch stage/artifact drift.
- An `ArtifactInventoryRecord` is emitted at `/api/artifact_inventory` to enumerate artifact presence by class and family.
- A `PromotionPriorityQueueRecord` is emitted at `/api/promotion_priority_queue` to rank families for next evidence work.
- A `PromotionWorkOrderRecord` is emitted at `/api/promotion_work_order` to turn the queue into a concrete first-family work item.
- A `PromotionWorkPacketRecord` is emitted at `/api/promotion_work_packet` to bundle the first-family work order with template and backlog links.
