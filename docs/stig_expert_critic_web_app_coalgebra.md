STATUS: SUPERSEDED BY docs/canonical/CANONICAL_ARCHITECTURE.md
DO NOT USE AS BUILD AUTHORITY

---

Below is a **handoff-grade rebuild package** you can give to a software agent so it can rebuild the STIG web app from the HTML you supplied **without drifting into vibe code**.

This is based on the structure already present in the page: host/session bar, gate badge, sidebar with STIG controls, contract/validate/adjudication/remediate/local-repair/tmsh/rest/merge tabs, pinned V-ID behavior, evidence/provenance panels, proof chain, advisory-only remediation, and verify→merge→save workflow. 

---

# 1. Product boundary

## 1.1 What this web app is

The web app is **not** a second implementation of the STIG factory.

It is:

## **a governed projection layer over factory artifacts**

It may:

* render
* filter
* sort
* group
* expand/collapse
* request deeper explanation
* request replay
* request controlled actions already authorized by the factory

It may **not**:

* invent judgments
* infer canonical truth from partial UI state
* recompute adjudication independently
* widen scope
* erase uncertainty
* turn advice into applied truth
* bypass gates

---

# 2. Non-negotiable laws for the rebuild

These are hard rules the agent must follow.

## L1 — No frontend judgment authority

No browser code may create a canonical validation or adjudication outcome.

All canonical outcomes must arrive from backend bundles tied to source records.

## L2 — No direct comparison

The UI must never compare expected and observed values on its own unless the backend explicitly sends a render-safe atomic comparison row.

## L3 — No advice/execution collapse

Advice is advice. Execution is execution. The UI must always preserve that distinction.

## L4 — No host cross-contamination

Changing host must clear all host-scoped truth state.

## L5 — No vulnerability drift

Every vuln-scoped tab must visibly carry the currently pinned V-ID.

## L6 — No hidden gate bypass

If gate state is degraded, only explicitly allowed actions may remain available.

## L7 — No silent merge shortcut

Merge flow must remain:
`edit -> verify -> merge -> save`

## L8 — No evidence erasure

Raw evidence provenance must remain accessible from any rendered validation/adjudication state.

---

# 3. UI coalgebra

Implement the page as a single top-level UI coalgebra with nested sub-coalgebras.

[
step_{ui} : X \times I \to O \times X
]

## 3.1 Top-level UI state `X`

```ts
type UIState = {
  appMode: "booting" | "ready" | "error";

  connection: ConnectionState;
  gate: GateState;
  selection: SelectionState;

  contractView: ContractViewState;
  validationView: ValidationViewState;
  adjudicationView: AdjudicationViewState;
  remediationView: RemediationViewState;
  localRepairView: LocalRepairViewState;
  tmshQueryView: QueryViewState;
  restQueryView: QueryViewState;
  mergeView: MergeViewState;

  caches: {
    contractsByVid: Record<string, ContractBundle>;
    latestValidationByVid: Record<string, ValidationViewBundle>;
    latestAdjudicationByVid: Record<string, AdjudicationViewBundle>;
    latestRemediationByVid: Record<string, RemediationViewBundle>;
    latestLocalRepairByVid: Record<string, LocalRepairViewBundle>;
    vulnStatusByVid: Record<string, VStatus>;
  };
};
```

## 3.2 Nested state types

```ts
type ConnectionState = {
  hostId: string | null;
  username: string;
  connected: boolean;
  sessionLabel: string;
};

type GateState = {
  status: "checking" | "healthy" | "advisory_only" | "tampered" | "unreachable";
  summary: string;
  detailLines: string[];
  allowValidate: boolean;
  allowAdvice: boolean;
  allowResidualCapture: boolean;
  allowExecution: boolean;
  allowPromotion: boolean;
};

type SelectionState = {
  currentVid: string | null;
  currentTab:
    | "contract"
    | "validate"
    | "adjudication"
    | "remediate"
    | "local-repair"
    | "tmsh-query"
    | "rest-query"
    | "merge";
};

type ContractViewState = {
  hydrated: boolean;
};

type ValidationViewState = {
  status:
    | "empty"
    | "loading"
    | "ready"
    | "insufficient_evidence"
    | "error";
  activeBundleId: string | null;
};

type AdjudicationViewState = {
  status: "empty" | "ready" | "error";
  activeBundleId: string | null;
  showFiberTable: boolean;
};

type RemediationViewState = {
  status: "empty" | "ready";
  activeBundleId: string | null;
  lastTmshExecution:
    | null
    | { outcome: "ok" | "fail"; consoleText: string };
  lastRestReview:
    | null
    | { outcome: "ok" | "fail"; consoleText: string };
};

type LocalRepairViewState = {
  status: "empty" | "ready";
  activeBundleId: string | null;
  lastCapture:
    | null
    | { outcome: "ok" | "fail"; message: string };
  lastRepairExecution:
    | null
    | { outcome: "ok" | "fail"; consoleText: string };
};

type QueryViewState = {
  input: string;
  output: string | null;
  status: "idle" | "running" | "ok" | "fail";
};

type MergeViewState = {
  snippet: string;
  step: "edit" | "verified" | "merged" | "saved";
  verifyResult: null | { outcome: "ok" | "fail"; consoleText: string };
  mergeResult: null | { outcome: "ok" | "fail"; consoleText: string };
  saveResult: null | { outcome: "ok" | "fail"; consoleText: string };
};
```

## 3.3 Input alphabet `I`

```ts
type UIEvent =
  | { type: "BOOT" }
  | { type: "HOST_SELECTED"; hostId: string }
  | { type: "USERNAME_CHANGED"; username: string }
  | { type: "PASSWORD_CHANGED"; password: string }
  | { type: "CONNECT_REQUESTED" }
  | { type: "DISCONNECT_REQUESTED" }
  | { type: "GATE_REFRESHED"; bundle: GateSnapshotBundle }
  | { type: "GATE_DETAIL_REQUESTED" }
  | { type: "VID_SELECTED"; vid: string }
  | { type: "TAB_SELECTED"; tab: SelectionState["currentTab"] }
  | { type: "CONTRACT_HYDRATED"; bundle: ContractBundle }
  | { type: "VALIDATE_REQUESTED"; vid: string }
  | { type: "VALIDATE_ALL_REQUESTED" }
  | { type: "VALIDATION_RECEIVED"; bundle: ValidationViewBundle }
  | { type: "ADJUDICATION_RECEIVED"; bundle: AdjudicationViewBundle }
  | { type: "REMEDIATION_RECEIVED"; bundle: RemediationViewBundle }
  | { type: "LOCAL_REPAIR_RECEIVED"; bundle: LocalRepairViewBundle }
  | { type: "FIBER_TABLE_TOGGLED" }
  | { type: "LOCAL_RESIDUAL_CAPTURE_REQUESTED"; vid: string }
  | { type: "LOCAL_REPAIR_EXECUTE_REQUESTED"; vid: string }
  | { type: "TMSH_QUERY_CHANGED"; value: string }
  | { type: "TMSH_QUERY_REQUESTED"; command: string }
  | { type: "REST_QUERY_CHANGED"; value: string }
  | { type: "REST_QUERY_REQUESTED"; endpoint: string }
  | { type: "SNIPPET_LOADED"; snippet: string }
  | { type: "SNIPPET_CHANGED"; snippet: string }
  | { type: "VERIFY_REQUESTED" }
  | { type: "MERGE_REQUESTED" }
  | { type: "SAVE_CONFIG_REQUESTED" }
  | { type: "ERROR_OCCURRED"; message: string };
```

## 3.4 Observations `O`

These are renderable view outputs:

* header session badge
* gate badge and gate detail dialog
* contract banner
* selected tab + pinned V-ID
* validation table/provenance/log
* adjudication banner/proof/fiber table
* remediation textareas/status
* local repair table/status
* query logs
* merge stepper + result consoles

---

# 4. Canonical backend bundles

The frontend may only render canonical bundles like these.

## 4.1 `ContractBundle`

```ts
type ContractBundle = {
  kind: "ContractBundle";
  bundleId: string;
  hostId: string;
  vid: string;
  title: string;
  severity: "high" | "medium" | "low";
  remediationMethod: string;
  evidenceRequired: string[];
  criteriaJson: unknown;
  tmshCommands: string[];
  restEndpoints: string[];
  organizationPolicy?: unknown;
  maturityStage?: string;
  blockedBy?: string | null;

  provenance: {
    contractRecordHash: string;
    sourceDocRef: string;
    scope: ScopeInfo;
  };
};
```

## 4.2 `ValidationViewBundle`

```ts
type ValidationViewBundle = {
  kind: "ValidationViewBundle";
  bundleId: string;
  hostId: string;
  vid: string;
  status:
    | "not_a_finding"
    | "open"
    | "insufficient_evidence"
    | "error"
    | "unresolved";

  provenancePanel: {
    gateStatus: string;
    trustRoot: string;
    witnessRef: string;
    pullbackRef: string;
    evidenceRefs: string[];
    scope: ScopeInfo;
    note?: string;
  };

  evidenceTable: AtomicComparisonRow[];
  pullbackSummary: {
    text: string;
    criticismNote?: string;
  };

  rawEvidenceLinks: RawEvidenceLink[];
  logText?: string;

  falsifierRefs: string[];
  criticismRefs: string[];

  provenance: {
    validationRecordHash: string;
    pullbackRecordHash: string;
  };
};

type AtomicComparisonRow = {
  measurableId: string;
  requiredAtomic: string | number | boolean | null;
  observedAtomic: string | number | boolean | null;
  operator: string;
  verdict: "pass" | "fail" | "unresolved";
  evidenceSource: string;
  evidencePreview?: string;
};
```

## 4.3 `AdjudicationViewBundle`

```ts
type AdjudicationViewBundle = {
  kind: "AdjudicationViewBundle";
  bundleId: string;
  hostId: string;
  vid: string;
  status:
    | "not_a_finding"
    | "open"
    | "insufficient_evidence"
    | "error"
    | "unresolved";

  rationale: string;
  criteriaDetail?: string;

  counts: {
    pass: number;
    fail: number;
    unresolved: number;
  };

  proofChain: ProofStep[];
  matchedPairs?: FiberPairRow[];
  validationIssues?: string[];

  falsifierRefs: string[];
  criticismRefs: string[];

  provenance: {
    adjudicationRecordHash: string;
    validationBundleId: string;
  };
};

type ProofStep = {
  phase: "observe" | "pullback" | "compare" | "criteria" | "criticism" | "evidence";
  title: string;
  detail: string;
  verdict?: "pass" | "fail" | "unresolved";
};
```

## 4.4 `RemediationViewBundle`

```ts
type RemediationViewBundle = {
  kind: "RemediationViewBundle";
  bundleId: string;
  hostId: string;
  vid: string;

  generalExplanation: string;
  vulnSpecificExplanation?: string;
  precisionSummary?: string;

  remediationMethod: string;

  tmshRecommendation: {
    advisoryOnly: false;
    command: string;
    enabled: boolean;
    expectedPostFixChecks: string[];
  };

  restRecommendation: {
    advisoryOnly: true;
    command: string;
    enabled: boolean;
    expectedPostFixChecks: string[];
  };

  note?: string;
  manualTag?: boolean;

  provenance: {
    remediationRecordHash: string;
    sourceValidationBundleId: string;
  };
};
```

## 4.5 `LocalRepairViewBundle`

```ts
type LocalRepairViewBundle = {
  kind: "LocalRepairViewBundle";
  bundleId: string;
  hostId: string;
  vid: string;

  summary: string;
  residualRows: AtomicComparisonRow[];
  localRepairTmshCommand?: string;

  captureEnabled: boolean;
  executeEnabled: boolean;

  provenance: {
    localRepairRecordHash: string;
    sourceValidationBundleId: string;
  };
};
```

## 4.6 `GateSnapshotBundle`

```ts
type GateSnapshotBundle = {
  kind: "GateSnapshotBundle";
  bundleId: string;
  status: GateState["status"];
  summary: string;
  detailLines: string[];
  permissions: {
    allowValidate: boolean;
    allowAdvice: boolean;
    allowResidualCapture: boolean;
    allowExecution: boolean;
    allowPromotion: boolean;
  };
  provenance: {
    gateRecordHash: string;
    trustRootHash: string;
  };
};
```

---

# 5. Rendering rule

The browser must implement this rule:

## **Only render from bundles. Never infer canonical semantics from ad hoc UI state.**

Local UI state may only control:

* visibility
* expansion/collapse
* current tab
* form input draft values
* spinners
* toast visibility

It may not control:

* official adjudication status
* official validation status
* promotion-like semantics
* scope widening
* evidence interpretation

---

# 6. Distinction-preserving web app gates

These are mandatory.

## WG-1 No host-cross contamination

Changing host must clear:

* `vulnStatusByVid`
* latest validation/adjudication/remediation/local-repair bundles
* merge step state
* ad hoc query outputs

Expected result:

* all prior host-scoped outcomes become unresolved/empty

## WG-2 No vuln-free scoped actions

The following actions are illegal without `currentVid`:

* Validate
* Validate All item hydration per current selection
* Remediation display
* Local repair capture
* Load snippet for selected vuln
* Merge snippet from vuln-specific source

UI response:

* action rejected
* no state mutation except error/status message

## WG-3 No gate-blind actions

If gate status is:

* `advisory_only`
* `tampered`
* `unreachable`

then execution-capable actions must be disabled or blocked:

* merge
* save
* direct execution paths
* promotion-like actions if any

Validation, evidence review, residual capture, and advice display may remain allowed only if `permissions` says so.

## WG-4 No adjudication without validation provenance

Adjudication panel must stay empty unless a matching `AdjudicationViewBundle` exists and references a validation bundle.

## WG-5 No success display without falsifier visibility

Any `not_a_finding` display must show:

* falsifier reference count or link
* provenance path
* scope note

## WG-6 No advice/execution collapse

REST recommendation must remain explicitly advisory-only.
TMSH/merge execution must require explicit action and later revalidation.

## WG-7 No residual loss

If validation has failed/unresolved rows, those rows must remain capturable into a local repair/residual bundle.

## WG-8 No merge without verify

The UI must not permit:

* merge before successful verify
* save before successful merge

## WG-9 No pin drift

All vuln-scoped tabs must show the same pinned V-ID.

## WG-10 No non-atomic projection

The UI may only render atomic comparison rows as the final truth surface.
Raw/noisy evidence may be displayed only as expandable provenance, never as the adjudicative comparison surface.

## WG-11 No frontend-only judgment logic

No JS/TS module may contain code that maps raw evidence directly to canonical STIG pass/fail/open semantics except rendering of server-returned bundle status.

## WG-12 No stale-bundle rendering

When host or V-ID changes, the UI must refuse to display bundles whose `(hostId, vid)` do not match current selection state.

---

# 7. Matching distinction-preserving tests

These are the tests the agent must implement.

## Test class A — Scope and identity

### T-A1 Host reset

1. Validate host A / V-ID X.
2. Switch to host B.
3. Assert:

   * old result panels cleared
   * statuses unresolved
   * query outputs scrubbed
   * merge state reset

### T-A2 Pinned V-ID consistency

1. Select V-ID X.
2. Visit every tab.
3. Assert same pinned V-ID visible.
4. Select V-ID Y.
5. Assert no stale X remains.

### T-A3 Stale bundle rejection

1. Load bundle for host A, V-ID X.
2. Switch to host B or V-ID Y.
3. Assert old bundle cannot render as active semantic state.

---

## Test class B — Gate integrity

### T-B1 Advisory-only degradation

1. Inject `GateSnapshotBundle.status = advisory_only`.
2. Assert execution buttons disabled.
3. Assert validation/advice/residual capture only if allowed.

### T-B2 Tampered gate

1. Inject `tampered`.
2. Assert gate warning visible.
3. Assert no execution path available.

### T-B3 Unreachable gate

1. Inject `unreachable`.
2. Assert only safe review actions survive.

---

## Test class C — Pullback truthfulness

### T-C1 No adjudication without validation

1. Open adjudication tab without validation bundle.
2. Assert placeholder only.

### T-C2 Atomic comparison preservation

1. Feed noisy evidence bundle plus atomic comparison rows.
2. Assert final table shows only atomic rows.
3. Assert noisy payload remains provenance-only.

### T-C3 Falsifier visibility

1. Render pass bundle.
2. Assert falsifier link/count shown.

### T-C4 Unresolved honesty

1. Feed validation bundle with unresolved rows.
2. Assert UI shows unresolved, not collapsed pass/fail.

---

## Test class D — Advice / execution distinction

### T-D1 Advisory-only REST

1. Load remediation bundle with REST advisory.
2. Assert UI labels advisory-only.
3. Assert no execution semantics are implied.

### T-D2 TMSH execute then revalidate

1. Execute TMSH remediation.
2. Assert no truth state changes until new validation bundle arrives.

### T-D3 Local residual capture

1. Feed failed/unresolved validation.
2. Capture residuals.
3. Assert residual bundle records same failed/unresolved rows.

---

## Test class E — Merge workflow

### T-E1 Verify gate

1. Enter snippet.
2. Try Merge before Verify.
3. Assert blocked.

### T-E2 Merge gate

1. Verify fails.
2. Assert Merge remains blocked.

### T-E3 Save gate

1. Verify passes, Merge passes.
2. Save allowed.
3. Assert save blocked in all earlier states.

### T-E4 Reset merge

1. Reach merged state.
2. Reset.
3. Assert stepper returns to `edit`.

---

## Test class F — Projection, not invention

### T-F1 No frontend judgment constructors

Static test:

* grep/lint for code constructing canonical statuses from raw evidence outside render adapters

### T-F2 Bundle-only render

Component tests:

* each semantic component requires bundle props
* missing bundle -> placeholder, not invented state

### T-F3 Derived UI state restriction

Type/lint rule:

* `status` fields in semantic panels are readonly from bundle sources

---

# 8. Component architecture

The agent should build these modules.

## 8.1 Core shell

* `AppShell`
* `HeaderSessionBar`
* `GateBadge`
* `SidebarHostPanel`
* `SidebarStigList`
* `ContractBanner`
* `TabBar`

## 8.2 Semantic view modules

* `ContractTab`
* `ValidateTab`
* `AdjudicationTab`
* `RemediateTab`
* `LocalRepairTab`
* `TmshQueryTab`
* `RestQueryTab`
* `MergeTab`

## 8.3 Projection adapters

* `renderContractBundle(bundle)`
* `renderValidationBundle(bundle)`
* `renderAdjudicationBundle(bundle)`
* `renderRemediationBundle(bundle)`
* `renderLocalRepairBundle(bundle)`
* `renderGateSnapshot(bundle)`

These are pure mapping layers from bundle -> view model.

## 8.4 State/event layer

* `uiReducer(state, event)`
* `uiSelectors.ts`
* `uiGuards.ts`

## 8.5 Safety / guard layer

* `assertVidSelected()`
* `assertGateAllows(action)`
* `assertBundleMatchesSelection(bundle, state)`
* `assertMergePreconditions(state)`

---

# 9. Types of UI-local state that are allowed

Allowed:

* current tab
* accordion open/closed
* textarea draft before submit
* spinner/loading
* last copied-to-clipboard state
* scroll position
* selected row highlight

Forbidden as canonical sources:

* validation pass/fail/open
* adjudication rationale
* final comparison semantics
* current scope interpretation
* promotion-like trust state

---

# 10. Exact implementation rules for the agent

Give the agent these commands.

## Build rules

1. Build in TypeScript.
2. Use a single reducer/state machine for semantic state transitions.
3. All canonical semantic panels must render from backend bundles.
4. All action handlers must dispatch typed events first, not mutate DOM directly.
5. No semantic component may read global mutable variables for truth state.
6. No component may infer canonical status from CSS classes, badge text, or table row colors.
7. Every vulnerable action must pass through `uiGuards.ts`.
8. All gate states must be exhaustively handled.
9. V-ID and host mismatch must fail closed.
10. Merge flow must be typed as a closed state machine.

## Don’t do this

* Don’t parse meaning from previously rendered HTML.
* Don’t keep “shadow truth” in component state.
* Don’t duplicate backend judgment logic.
* Don’t silently coerce unresolved into pass/fail.
* Don’t render stale bundles after host/V-ID change.
* Don’t make REST advisory actions look executable.
* Don’t enable merge/save from cosmetic state only.

---

# 11. Minimal API surface expected by the UI

The agent should assume or ask for these endpoints/bundle providers:

* `GET /api/hosts`
* `GET /api/contracts`
* `GET /api/gate_snapshot?host=...`
* `POST /api/connect`
* `POST /api/disconnect`
* `POST /api/validate`
* `POST /api/validate_all`
* `GET /api/adjudication?host=...&vid=...`
* `GET /api/remediation?host=...&vid=...`
* `POST /api/local_residual_capture`
* `POST /api/local_repair_tmsh`
* `POST /api/tmsh_query`
* `POST /api/rest_query`
* `GET /api/snippet?vid=...`
* `POST /api/verify_merge`
* `POST /api/apply_merge`
* `POST /api/save_config`

Each semantic endpoint must return a typed bundle, not ad hoc HTML text.

---

# 12. Promotion-quality UI review checklist

Use this before accepting the rebuild.

| ID  | Gate                               | Pass condition                                   |
| --- | ---------------------------------- | ------------------------------------------------ |
| W1  | Bundle-only render                 | All semantic panels render from typed bundles    |
| W2  | No host contamination              | Host change clears host-scoped truth state       |
| W3  | No V-ID drift                      | Every scoped tab shows correct pinned V-ID       |
| W4  | Gate integrity                     | Degraded gate states constrain actions correctly |
| W5  | No adjudication without validation | Empty adjudication without bundle                |
| W6  | Advice/execution split             | Advisory outputs remain advisory                 |
| W7  | Residual preservation              | Failed/unresolved rows capturable                |
| W8  | Merge ordering                     | Verify→Merge→Save enforced                       |
| W9  | Atomic truth surface               | Final comparison rows are atomic only            |
| W10 | No frontend semantic invention     | Static + runtime tests pass                      |
| W11 | Falsifier visibility               | Pass displays link/count/scope                   |
| W12 | Replay-safe rendering              | Same bundle renders same semantic view state     |

---

# 13. Short handoff statement for the software agent

Use this verbatim if useful:

> Rebuild this STIG web app as a governed projection of backend artifacts, not as an independently interpreted frontend. Model it as a top-level UI coalgebra with typed state, typed events, pure render adapters over canonical bundles, and hard guards for host scoping, vulnerability pinning, gate health, provenance-before-adjudication, advisory/execution separation, residual preservation, and verify→merge→save sequencing. No canonical judgment or adjudication semantics may be computed in the browser except rendering of bundle status already produced by the factory.

---

