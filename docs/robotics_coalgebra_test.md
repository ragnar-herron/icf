Here’s the **formal, build-ready checklist table** for the **Coalgebra Production Test applied to robot domains**. I’ve written it so it works for a robot learner / planner / manipulator expert critic, while still supporting specialization for navigation, manipulation, tool use, feeding, inspection, and other embodied tasks.

# Coalgebra Production Test — Robot Domains

| ID      | Test Dimension                               | Required Definition (Robot Context)                                                                                                                                                                    | Evidence / Artifact Required                                                       | Pass/Fail | Notes |
| ------- | -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------- | --------- | ----- |
| **C1**  | **State (`X`)**                              | Explicit robot-domain state schema: task state, belief/state estimate, planner state, controller mode, witness registry, survivor rules, open criticisms, safety state, scope axes                     | `RobotStateSchema.json`, example serialized state snapshots                        | ☐         |       |
| **C2**  | **Observation (`O`)**                        | Explicit outputs: action commands, plan statuses, execution traces, safety alerts, criticisms, falsifiers, promotions/demotions, audit records                                                         | List of emitted record types + example JSONL traces                                | ☐         |       |
| **C3**  | **Event/Input (`I`)**                        | Defined input space: sensor updates, task requests, exogenous events, break injection, fix application, synthesis proposal, scope change, hardware/config change                                       | `RobotEventSchema.json` + replay fixtures                                          | ☐         |       |
| **C4**  | **Behavior Map (`step`)**                    | Deterministic or explicitly scoped step function from `(state, input)` to `(observations, next_state)` for the kernel portion; any nondeterminism must be declared and isolated                        | `step()` implementation spec + replay test under frozen seeds                      | ☐         |       |
| **C5**  | **Behavioral Distinction**                   | Clear rule for when two robot states differ behaviorally: different plans under same goal, different safety outputs, different action traces, different recovery behavior, different criticism yield   | Trace-difference or bisimulation-style test suite with distinguishable state pairs | ☐         |       |
| **C6**  | **Falsifier**                                | Explicit falsifiers for the coalgebra claim: missed obstacle, unsafe action, failed grasp, witness hides exogenous disturbance, mismatch between predicted and observed effect, replay inconsistency   | `RobotFalsifierCatalog.md` + seeded failing trials                                 | ☐         |       |
| **C7**  | **Scope**                                    | Declared validity axes: robot embodiment, end-effector/tooling, sensor suite, environment class, task family, object class, controller stack, hardware/software version                                | `RobotScopeRecord.json` + coverage matrix                                          | ☐         |       |
| **C8**  | **Witness Presence (Pullback)**              | Every claim or plan is mediated by an explicit witness: task witness, behavior witness, safety witness, manipulation witness, navigation witness, etc. No direct plan→world or spec→success comparison | `WitnessSpec.json` per task/boundary; proof that execution checking uses witnesses | ☐         |       |
| **C9**  | **Witness Testability (Recursive Adequacy)** | Witnesses are themselves attacked: hidden-failure probes, exogenous-process probes, coarseness probes, version-drift probes, sim-to-real mismatch probes                                               | `WitnessTestSuite` + witness criticism/demotion records                            | ☐         |       |
| **C10** | **Plan–Execution Pullback**                  | High-level plan success is never assumed; execution must mediate it. The system must compare intended subgoals to realized behavior through a witness                                                  | `PlanExecutionTrialRecord` corpus linking plan, execution, witness, and result     | ☐         |       |
| **C11** | **Synthesis Demotion**                       | Synthesized skills, predicates, planners, controllers, or repairs are proposals only until they survive criticism                                                                                      | `SynthesizedArtifactRecord` lifecycle for robot artifacts                          | ☐         |       |
| **C12** | **Failure Preservation**                     | Raw sensor data, actuator outcomes, execution failures, near misses, and safety interventions are preserved and linked to later promotions/demotions                                                   | Raw logs, trace blobs, failure records, ledger linkage                             | ☐         |       |
| **C13** | **Safety Preservation**                      | Safety outputs are first-class; no promoted artifact may hide or erase safety-relevant failure semantics                                                                                               | `SafetyViolationRecord`, `SafetyConstraintRecord`, safety replay tests             | ☐         |       |
| **C14** | **Deterministic Replay / Bounded Replay**    | For the kernel and evaluation components, replay is deterministic under frozen seeds and captured inputs; any unavoidable nondeterminism is declared and bounded                                       | Replay harness + frozen-seed reports + declared nondeterminism docs                | ☐         |       |
| **C15** | **Promotion Gate (Survivor)**                | Promotion requires survival over repeated trials across varied environment axes: object sets, lighting, terrain, clutter, sensor noise, tool variants, etc.                                            | `PromotionPolicy.md` + `PromotionRecord` examples with ancestry                    | ☐         |       |
| **C16** | **Criticism Durability**                     | Criticisms are append-only, replayable, and reused for later trials, refactors, and retraining                                                                                                         | Ledger inspection + anti-deletion tests                                            | ☐         |       |
| **C17** | **Optimization Guardrail**                   | Efficiency gains (planning speed, execution speed, model size, energy use) cannot reduce falsifier yield, safety detection, or witness adequacy                                                        | `RobotWHRReport` + regression tests                                                | ☐         |       |
| **C18** | **No Direct Alignment**                      | System forbids direct “plan succeeded because final label says success” or “controller is correct because command executed”; all success claims must pass through witnesses                            | Static checks / lint rules / failing bypass tests                                  | ☐         |       |
| **C19** | **Multi-Level Consistency**                  | Contradictions across levels are detectable: goal↔plan, plan↔design, design↔controller, controller↔behavior, behavior↔world                                                                            | `ContradictionRecord` examples + seeded mismatch tests                             | ☐         |       |
| **C20** | **Governance Consistency**                   | Promotion authority is explicit and consistent for robot experts: machine policy, human sign-off, or hybrid, with no ambiguity                                                                         | Governance doc + signed `PromotionRecord` verification                             | ☐         |       |
| **C21** | **Exogenous Process Modeling**               | The coalgebra explicitly handles exogenous changes not controlled by the robot: moving humans, falling objects, fluid fill, heating, slips, timing drift, etc.                                         | `ExogenousProcessRecord` or equivalent + tests showing detection/handling          | ☐         |       |
| **C22** | **Recovery / Compensation Behavior**         | The coalgebra distinguishes nominal execution from recovery, retry, fallback, abort, and compensation behavior                                                                                         | Recovery traces + state transition tests                                           | ☐         |       |
| **C23** | **Tool-Use / Embodiment Specificity**        | If the domain includes tools or manipulators, the coalgebra declares how tool state and embodiment differences affect state, observation, and scope                                                    | Tool-use schema, embodiment variants, cross-tool trial set                         | ☐         |       |
| **C24** | **Abstraction Library Governance**           | Learned predicates, skills, and abstractions are explicitly versioned, scoped, and criticizable; refactoring cannot erase criticism lineage                                                            | `AbstractionRecord`, `RefactorLineageRecord`, lineage-preservation tests           | ☐         |       |
| **C25** | **Reality Contact Quality**                  | The system proves that training/evaluation data actually contact embodied reality or declared replay sources, not just synthetic proxies mislabeled as real                                            | provenance records for sim, replay, lab, field trials                              | ☐         |       |

## Domain-specific witness examples

You will likely want witness families like these:

| Robot Subdomain | Example Witness                                                           |
| --------------- | ------------------------------------------------------------------------- |
| Navigation      | occupancy/safety witness, route-feasibility witness, arrival witness      |
| Manipulation    | grasp-success witness, contact-stability witness, placement witness       |
| Tool use        | tool-affordance witness, force/torque witness, task-effect witness        |
| Feeding / HRI   | safety-distance witness, user-preference witness, task-completion witness |
| Inspection      | coverage witness, anomaly-detection witness, evidence adequacy witness    |
| Assembly        | alignment witness, fastening witness, sequence-consistency witness        |

## Pass criteria

* **Pass**: All items C1–C25 are checked with concrete artifacts.
* **Conditional Pass**: C1–C9 and C10–C13 must be checked for a valid coalgebraic robot expert candidate.
* **Fail**: Any of C1–C7 is unchecked → **no valid coalgebra**.
* **Fail**: C8 or C18 is unchecked → **no valid pullback system**.
* **Fail**: C13, C21, or C22 is unchecked in embodied domains → **unsafe or incomplete robot coalgebra**.

## How to use this recursively

Use this checklist at three levels:

1. **Object coalgebra**

   * robot planner
   * manipulation expert
   * tool-use expert
   * safety monitor

2. **Expert bundle**

   * promoted robot navigation expert
   * promoted robot feeding expert
   * promoted robot assembly expert

3. **Meta-coalgebra**

   * the system that matures robot coalgebras through break/fix, criticism, replay, and promotion

A robot meta-coalgebra should not promote any object coalgebra unless that object coalgebra passes this checklist first.

## Short anchor

**No robot expert promotion without a passed coalgebra test; no robot coalgebra without explicit state, observations, events, step map, distinction test, falsifier, scope, witness-mediated execution checks, preserved failures, and safety-bound embodied reality contact.**
