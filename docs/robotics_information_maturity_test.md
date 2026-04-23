Here is the **single formal design review checklist** for **robotics**, integrating:

* **Coalgebra Production**
* **Pullback / Truth-Seeking Integrity**
* **Maturity**
* **Progressive Error Correction**
* **Anti-Drift (Universal Constructor Stability)**

It is written as a **hard gate artifact** for robot domains such as:

* navigation
* manipulation
* tool use
* feeding / HRI
* inspection
* assembly

---

# **Robot Expert Critic — Unified Design Review Checklist**

| ID     | Category  | Test                   | Required Condition (Robot Context)                                                                                                                                          | Evidence / Artifact Required                                   | Pass/Fail | Notes |
| ------ | --------- | ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- | --------- | ----- |
| **C1** | Coalgebra | State Defined          | Explicit robot-domain state: belief/state estimate, task state, planner state, controller mode, witness registry, survivor rules, open criticisms, safety state, scope axes | `RobotStateSchema.json`, state snapshots                       | ☐         |       |
| **C2** | Coalgebra | Observations Defined   | Outputs explicitly defined: action commands, plan outcomes, execution traces, safety alerts, criticisms, falsifiers, promotions/demotions                                   | JSONL traces, emitted record inventory                         | ☐         |       |
| **C3** | Coalgebra | Inputs Defined         | Inputs explicitly defined: sensor updates, task requests, exogenous events, break injection, fix application, synthesis proposals, hardware/config changes                  | `RobotEventSchema.json`, replay fixtures                       | ☐         |       |
| **C4** | Coalgebra | Behavior Map           | Deterministic or explicitly bounded `step(state,input)` for the kernel/evaluation path                                                                                      | `step()` spec, replay test, bounded nondeterminism declaration | ☐         |       |
| **C5** | Coalgebra | Behavioral Distinction | Two states are behaviorally distinguishable under same input via action trace, safety output, recovery behavior, criticism yield, or judgment difference                    | trace comparison or bisimulation-style test suite              | ☐         |       |
| **C6** | Coalgebra | Falsifier Defined      | Explicit falsifiers exist: missed obstacle, unsafe motion, failed grasp, hidden exogenous process, mismatch between expected and observed effect, replay inconsistency      | falsifier catalog, seeded failing trials                       | ☐         |       |
| **C7** | Coalgebra | Scope Defined          | Explicit robot scope: embodiment, end-effector/tooling, sensor suite, environment class, task family, object class, controller stack, hardware/software version             | `RobotScopeRecord.json`, coverage matrix                       | ☐         |       |

---

## **Pullback / Truth-Seeking Core**

| ID      | Category | Test                | Required Condition                                                                                                       | Evidence / Artifact Required                         | Pass/Fail | Notes |
| ------- | -------- | ------------------- | ------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------- | --------- | ----- |
| **P1**  | Pullback | Declaration–Reality | No task, plan, or success claim accepted without evidence-mediated witness comparison to real or declared replay reality | execution validation trace                           | ☐         |       |
| **P2**  | Pullback | Claim–Evidence      | Task claim, observed sensor evidence, and resulting judgment remain distinct                                             | raw vs normalized evidence records, judgment linkage | ☐         |       |
| **P3**  | Pullback | Witness–Reality     | Witnesses are themselves criticizable under real execution, replay, and adversarial variation                            | witness test suite, witness criticism records        | ☐         |       |
| **P4**  | Pullback | Plan–Execution      | High-level plans do not count as success until mediated by execution witness and observed behavior                       | plan/execution trial corpus                          | ☐         |       |
| **P5**  | Pullback | Synthesis–Behavior  | Synthesized skills, predicates, planners, controllers, or repairs remain hypotheses until behaviorally criticized        | synthesis lifecycle records                          | ☐         |       |
| **P6**  | Pullback | Failure–Survivor    | Promoted robot rules/skills derive from preserved failures, near misses, and recovery outcomes                           | lineage graph, failure-linked promotions             | ☐         |       |
| **P7**  | Pullback | Level–Level         | Contradictions detectable across levels: goal↔plan, plan↔design, design↔controller, controller↔behavior, behavior↔world  | contradiction records, seeded mismatch tests         | ☐         |       |
| **P8**  | Pullback | Revision–Identity   | Changes checked against stable robot task identity and safety envelope                                                   | revision audit, task identity record                 | ☐         |       |
| **P9**  | Pullback | Criticism–Memory    | Criticisms preserved and replayable across refactors, retraining, and promotions                                         | ledger replay, lineage inspection                    | ☐         |       |
| **P10** | Pullback | Optimization–Truth  | Optimization cannot reduce falsifier yield, safety visibility, witness adequacy, or failure preservation                 | WHR reports, regression tests                        | ☐         |       |

---

## **Maturity Tests**

| ID     | Category | Test                | Required Condition                                                                        | Evidence / Artifact Required       | Pass/Fail | Notes |
| ------ | -------- | ------------------- | ----------------------------------------------------------------------------------------- | ---------------------------------- | --------- | ----- |
| **M1** | Maturity | State Growth        | Survivor-state grows while preserving prior criticisms, failures, and safety lineage      | state lineage, promotion ancestry  | ☐         |       |
| **M2** | Maturity | Criticism Retention | Criticism remains durable across revisions, retraining, embodiment changes, and refactors | ledger replay, anti-deletion tests | ☐         |       |
| **M3** | Maturity | Falsifier Vitality  | Nonzero falsifier production sustained over meaningful evaluation windows                 | falsifier yield metric             | ☐         |       |
| **M4** | Maturity | Scope Expansion     | Validity scope expands across environment axes without hidden regressions                 | scope coverage matrix              | ☐         |       |
| **M5** | Maturity | Survivor Strength   | Promotions remain valid over time, across conditions, and under new adversarial trials    | survivor retention metrics         | ☐         |       |
| **M6** | Maturity | Witness Improvement | Witnesses improve under criticism, especially for hidden failures and exogenous dynamics  | witness revision history           | ☐         |       |
| **M7** | Maturity | Efficiency Honesty  | Waste decreases without reducing truth-seeking, safety, or criticism power                | WHR reports, metric diff           | ☐         |       |
| **M8** | Maturity | Recursive Reopening | Promoted skills/rules can be reopened, demoted, or revised under new evidence             | demotion traces, re-open events    | ☐         |       |

---

## **Progressive Error-Correction Tests**

| ID     | Category | Test                     | Required Condition                                                                                            | Evidence / Artifact Required                         | Pass/Fail | Notes |
| ------ | -------- | ------------------------ | ------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- | --------- | ----- |
| **E1** | Error    | Unsafe Success Reduction | Apparent successes that hide unsafe behavior decrease over time                                               | unsafe-success metrics, safety reviews               | ☐         |       |
| **E2** | Error    | False Failure Reduction  | Incorrect failure judgments decrease over time                                                                | FN-style metrics for failed tasks later shown viable | ☐         |       |
| **E3** | Error    | Break Detection          | Seeded breaks and adversarial disturbances are detected at stable or improving rates                          | break detection tests                                | ☐         |       |
| **E4** | Error    | Recovery Validation      | Recovery and compensation quality improves or remains stable without hidden regressions                       | recovery logs, regression reports                    | ☐         |       |
| **E5** | Error    | Synthesis Correction     | Synthesized robot artifacts improve under criticism instead of merely churning proposals                      | synthesis metrics, survivor ratio                    | ☐         |       |
| **E6** | Error    | Witness Miss Reduction   | Failures hidden by coarse witnesses decrease over time                                                        | adversarial witness probes                           | ☐         |       |
| **E7** | Error    | Cross-Level Consistency  | Adjacent-level contradictions are detected earlier and unresolved contradiction backlog shrinks               | contradiction backlog metrics                        | ☐         |       |
| **E8** | Error    | Residual Conversion      | Residual unexplained evidence increasingly becomes explicit criticism, new witnesses, or revised abstractions | residual conversion metrics                          | ☐         |       |

---

## **Embodied / Safety-Specific Tests**

| ID     | Category | Test                          | Required Condition                                                                               | Evidence / Artifact Required                  | Pass/Fail | Notes |
| ------ | -------- | ----------------------------- | ------------------------------------------------------------------------------------------------ | --------------------------------------------- | --------- | ----- |
| **R1** | Embodied | Safety Preservation           | Safety constraints are first-class and cannot be bypassed by performance or synthesis shortcuts  | `SafetyConstraintRecord`, safety replay tests | ☐         |       |
| **R2** | Embodied | Exogenous Process Modeling    | Exogenous processes are explicitly modeled or explicitly declared out of scope                   | exogenous process records, test cases         | ☐         |       |
| **R3** | Embodied | Recovery / Compensation       | Recovery, retry, abort, and fallback behaviors are represented distinctly from nominal execution | recovery state tests, trace inspection        | ☐         |       |
| **R4** | Embodied | Tool / Embodiment Specificity | Tool state and embodiment differences affect state, witness, and scope explicitly                | tool-use schema, embodiment variants          | ☐         |       |
| **R5** | Embodied | Reality Contact Quality       | Real-world, lab, sim, and replay provenance are distinguished and not collapsed                  | provenance records, dataset/source audit      | ☐         |       |
| **R6** | Embodied | Human / User Safety           | If domain includes HRI, user safety, preference, and intervention are explicit and criticizable  | HRI safety records, user-intervention traces  | ☐         |       |

---

## **Anti-Drift (Universal Constructor Stability)**

| ID     | Category | Test                              | Required Condition                                                                             | Evidence / Artifact Required        | Pass/Fail | Notes |
| ------ | -------- | --------------------------------- | ---------------------------------------------------------------------------------------------- | ----------------------------------- | --------- | ----- |
| **D1** | Drift    | Core Pullbacks Preserved          | All 10 core pullbacks remain explicit and enforced                                             | design diff audit                   | ☐         |       |
| **D2** | Drift    | Identity Stability                | Changes preserve robot task identity and constitutional core unless explicitly re-founded      | identity audit, change review       | ☐         |       |
| **D3** | Drift    | Constitutive Changes Declared     | Any change to core pullbacks, witness laws, or promotion law is explicitly marked constitutive | constitutive revision log           | ☐         |       |
| **D4** | Drift    | Stable Maturation Logic           | Same promotion/demotion logic applies across robot subdomains                                  | cross-subdomain test, policy audit  | ☐         |       |
| **D5** | Drift    | Lineage Preservation              | Every promoted expert/skill traces back to criticisms, failures, and predecessors              | lineage graph, replay proof         | ☐         |       |
| **D6** | Drift    | Metric Integrity                  | Metrics are not being gamed; no optimization passes if truth or safety regress                 | metric audit, regression tests      | ☐         |       |
| **D7** | Drift    | No Shortcut Paths                 | No direct comparison bypasses witnesses at any layer                                           | static/dynamic checks, bypass tests | ☐         |       |
| **D8** | Drift    | General vs Specialized Separation | Meta-coalgebra stays stable while navigation/manipulation/tool-use coalgebras specialize       | architecture review, module diff    | ☐         |       |

---

# **Final Gates**

| Gate                                           | Condition       | Pass/Fail |
| ---------------------------------------------- | --------------- | --------- |
| **Gate A — Coalgebra Validity**                | C1–C7 all pass  | ☐         |
| **Gate B — Pullback Integrity**                | P1–P10 all pass | ☐         |
| **Gate C — Maturity**                          | M1–M8 all pass  | ☐         |
| **Gate D — Error Correction**                  | E1–E8 all pass  | ☐         |
| **Gate E — Embodied Safety / Reality Contact** | R1–R6 all pass  | ☐         |
| **Gate F — Anti-Drift**                        | D1–D8 all pass  | ☐         |

---

# **Final Decision**

| Decision                                                            | Status       |
| ------------------------------------------------------------------- | ------------ |
| **System qualifies as Robot Domain Coalgebra**                      | ☐ YES / ☐ NO |
| **System enforces pullback-mediated truth-seeking**                 | ☐ YES / ☐ NO |
| **System is maturing correctly**                                    | ☐ YES / ☐ NO |
| **System is progressively error-correcting**                        | ☐ YES / ☐ NO |
| **System is stable (not drifting)**                                 | ☐ YES / ☐ NO |
| **System is safe enough for embodied deployment in declared scope** | ☐ YES / ☐ NO |
| **Constitutive redesign required?**                                 | ☐ YES / ☐ NO |

---

# **One-Line Anchor**

**No robot expert is accepted unless it produces a valid coalgebra, enforces witness-mediated pullback across levels, improves under criticism, preserves embodied failure and safety semantics, and matures without drifting from the same universal constructor.**
