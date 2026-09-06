# SkillFoundry

> **Agents that learn the tools, not just the task.**

SkillFoundry is a trajectory-based agent-learning system for tool-using agents.

Instead of simply remembering past conversations, SkillFoundry learns from **execution experience**:

**FAIL → UNDERSTAND → LEARN → REPLAY → MEASURE → PROMOTE**

| Metric | Run 1 (Baseline) | Run 2 (Guided Replay) | Delta | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Score** | `0.6250` | `1.0000` | `+0.3750` | **Improved** |
| **Tool Calls** | `3` | `3` | `0` | **Zero Overhead** |
| **Promotion Gate** | — | **Passed** | — | **PROMOTED** |
| **Test Suite** | 113 passed / 0 failed | 113 passed / 0 failed | — | **100% Reliable** |

---

## What is SkillFoundry?

Given a task, available tools, and an evaluator, SkillFoundry:

1. **Executes** the task.
2. **Records** the complete execution trajectory.
3. **Evaluates** the result.
4. **Analyzes** what failed and why.
5. **Synthesizes** a reusable skill from the evidence.
6. **Replays** that skill on a fresh trajectory.
7. **Measures** the improvement.
8. **Promotes** the skill only when it passes the promotion gate.

---

## Architecture

```text
                         SKILLFOUNDRY
                              │
                              ▼
                            GOAL
                              │
                              ▼
                            AGENT
                              │
                              ▼
                            TOOLS
                              │
                              ▼
                         TRAJECTORY
                              │
                              ▼
                          EVALUATOR
                              │
                              ▼
                     FAILURE ANALYZER
                              │
                              ▼
                     SKILL SYNTHESIZER
                              │
                              ▼
                            SKILL
                              │
                              ▼
                           REPLAY
                              │
                              ▼
                       PROMOTION GATE
                              │
                              ▼
                       VERIFIED SKILL
                              │
                              ▼
                       BETTER NEXT RUN
```

### The Learning Cycle

```text
Run 1
  ↓
Failure
  ↓
Failure Analysis
  ↓
Skill Synthesis
  ↓
Learned Procedure + Parameters
  ↓
Fresh Replay
  ↓
Evaluation
  ↓
Promotion / Rejection
```

---

## Why SkillFoundry?

A conventional agent memory system mostly stores:
- *"What happened before?"*

SkillFoundry stores and verifies:
- **What failed?**
- **Why did it fail?**
- **What tool-use procedure should change?**
- **Which parameters can be recovered from evidence?**
- **Did the change actually improve the next run?**

A skill is therefore **evidence-backed and replay-validated**, rather than simply generated and remembered.

---

## Why This Matters

- **Evidence over memory**: Skills are derived from real execution trajectories, not hallucinated context.
- **Replay over assumption**: A generated skill must be tested and proven on a fresh execution run.
- **Promotion over optimism**: A skill is promoted only when measurable evidence shows concrete quality improvement.
- **Zero bloat**: Skills must improve performance without increasing unnecessary tool call overhead.

---

## Deterministic Benchmark

The repository includes a deterministic GitHub CI investigation benchmark:
`demos/github_ci_learning_demo.py`

The benchmark demonstrates a complete closed learning cycle.

### Run 1 — Baseline

The agent investigates a failed CI run using:
```text
list_workflow_runs → inspect_job_logs → inspect_commit
```

The final commit inspection fails because the baseline contains an invalid commit SHA.

- **Baseline score**: `0.6250`
- **Tool calls**: `3`
- **Failure type**: `tool_failure`

### Learning

SkillFoundry analyzes the recorded trajectory:
- **Learned procedure**:
  ```text
  list_workflow_runs → inspect_job_logs → inspect_commit
  ```
- **Learned parameters** (extracted from successful prior evidence):
  - `inspect_job_logs.run_id = 2`
  - `inspect_job_logs.job_name = test`
  - `inspect_commit.sha = def456ghi789`

The learned information retains provenance back to the source trajectory.

### Run 2 — Guided Replay

The synthesized skill is replayed on a new trajectory using the learned procedure and recovered parameters.

- **Replay score**: `1.0000`
- **Tool calls**: `3`

### Promotion Gate

The Promotion Gate accepts the skill only when:
```text
Replay score > Baseline score
AND
Replay tool calls <= Baseline tool calls
```

For the benchmark:
- **Improved**: `True`
- **Promoted**: `True`
- **Promotion Verdict**: The skill improved quality (`0.6250` → `1.0000`, `+0.3750`) without increasing tool usage (`3` → `3`).

### Results

```text
=== SKILLFOUNDRY LEARNING DEMO ===

BASELINE / RUN 1
- trajectory id:          trajectory-20260906-200136-3a36e9b768a0
- evaluation score:       0.6250
- failure type:           tool_failure
- observed tool sequence: ['list_workflow_runs', 'inspect_job_logs', 'inspect_commit']
- tool call count:        3

LEARNING
- synthesized skill id:   tool-failure-list-workflow-runs-i-ceb12f-v1
- skill name:             Recovery for tool_failure
- skill trigger:          Failure: tool_failure
- skill procedure:        ['list_workflow_runs', 'inspect_job_logs', 'inspect_commit']
- learned parameters:
  inspect_commit.sha = def456ghi789
  inspect_job_logs.run_id = 2
  inspect_job_logs.job_name = test
- provenance:             source_trajectory_id = trajectory-20260906-200136-3a36e9b768a0

REPLAY / RUN 2
- replay trajectory id:   trajectory-20260906-200136-ee0d2f94d79c
- replay score:           1.0000
- replay tool sequence:   ['list_workflow_runs', 'inspect_job_logs', 'inspect_commit']
- replay tool call count: 3

PROMOTION
- score delta:            +0.3750
- tool call delta:        +0
- improved:               True
- promoted:               True
- promotion reason:       Skill promoted: replay score improved by +0.3750 (0.6250 -> 1.0000) without increasing tool usage (3 -> 3).
```

---

## System Components

### Core Execution Layer (`src/syndicate/core/`)
- **Task & Tool Models**: Standardized task definitions, tool calls, and results.
- **Agent Executor**: Coordinates execution loop and dispatches actions.
- **Deterministic GitHub Simulator**: Offline, mockable GitHub environment for reproducible testing.
- **Trajectory Recorder**: Records full step-by-step execution history and states.
- **Trajectory Evaluator**: Computes objective quality and efficiency scores.

### Learning Layer (`src/syndicate/learning/`)
- **`failure_analyzer.py`**: Diagnoses failure categories, root causes, and broken tool calls.
- **`skill.py`**: Immutable schema for executable skills with parameter mappings and provenance.
- **`skill_synthesizer.py`**: Extracts reusable procedures and binds evidence-backed arguments.
- **`replay_engine.py`**: Replays synthesized skills against new task trajectories.
- **`promotion_gate.py`**: Validates whether replay demonstrates measurable quality improvement.
- **`learning_loop.py`**: Orchestrates the complete end-to-end learning lifecycle.

---

## AO + OpenCode + TensorMux

SkillFoundry is designed for modern agent orchestration workflows:

```text
AO
 ↓
OpenCode
 ↓
TensorMux
 ↓
GLM-4.7-Flash
```

- **AO**: Orchestration environment coordinating agent runs and task lifecycles.
- **OpenCode & TensorMux**: Model routing and high-throughput inference layer.
- **GLM-4.7-Flash**: Reasoning engine configured for planning and synthesis.
- The deterministic benchmark remains offline and reproducible so that the learning result can be independently verified.

---

## Repository Structure

```text
my-syndicate-project/
│
├── README.md
├── opencode.json
├── pytest.ini
│
├── demos/
│   └── github_ci_learning_demo.py
│
├── docs/
│   └── CORE_ENGINE.md
│
├── src/
│   └── syndicate/
│       ├── core/
│       │   ├── models/
│       │   ├── simulator/
│       │   ├── executor/
│       │   ├── recorder/
│       │   └── evaluator/
│       │
│       └── learning/
│           ├── failure_analyzer.py
│           ├── skill.py
│           ├── skill_synthesizer.py
│           ├── replay_engine.py
│           ├── promotion_gate.py
│           └── learning_loop.py
│
└── tests/
```

---

## Quick Start

### Run the Test Suite
The repository includes comprehensive unit and integration tests (113 passing tests, 0 failing tests):

```powershell
python -m pytest -q
```

### Run the Benchmark
Execute the end-to-end learning loop demo:

```powershell
python demos/github_ci_learning_demo.py
```

---

## Hackathon Demo

To run the live hackathon demonstration showing full failure recovery and promotion:

```powershell
python demos/github_ci_learning_demo.py
```

Observe the live transition from **Baseline Failure (0.6250)** to **Synthesized Skill Promotion (1.0000)**.

---

## Track 1 — Automated Agent Engineering

SkillFoundry directly addresses the Track 1 goals by providing:
- **Tool-use learning**: Learning operational tool procedures from execution feedback.
- **Execution trajectories**: Comprehensive recording of tool calls, inputs, and outputs.
- **Failure analysis**: Root-cause diagnostic engine for broken execution paths.
- **Reusable skills**: Parameterized, evidence-grounded skill schemas.
- **Replay & Verification**: Deterministic validation on fresh trajectories.
- **Measurable improvement**: Strict promotion gates requiring higher score without tool call inflation.
- **AO-based agent orchestration**: Seamless integration with AO, OpenCode, and TensorMux.

---

## Key Insight

> **Agents should learn how to use the environment, not just remember the conversation.**

SkillFoundry turns an execution failure into a testable skill and then answers the only question that matters:  
**Did the next run actually get better?**

---

## Future Direction

1. Multi-step skill composition across diverse tool domains.
2. Cross-agent skill sharing with persistent vector memory storage.
3. Automated regression testing for promoted skill libraries.

---

## License

This project is part of the Syndicate Track 1 implementation for SkillFoundry.
