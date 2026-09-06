# SkillFoundry

> **Agents that learn the tools, not just the task.**

SkillFoundry is a trajectory-based agent-learning system for tool-using agents.

Instead of simply remembering past conversations, SkillFoundry learns from **execution experience**:

**FAIL → UNDERSTAND → LEARN → REPLAY → MEASURE → PROMOTE**

---

## What SkillFoundry Does

Given a task, available tools, and an evaluator, SkillFoundry:

1. Executes the task.
2. Records the complete execution trajectory.
3. Evaluates the result.
4. Analyzes what failed and why.
5. Synthesizes a reusable skill from the evidence.
6. Replays that skill on a fresh trajectory.
7. Measures the improvement.
8. Promotes the skill only when it passes the promotion gate.

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
The learning loop
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
Why This Is Different

A conventional agent memory system mostly stores:

"What happened before?"

SkillFoundry stores:

"What failed?"
"Why did it fail?"
"What tool-use procedure should change?"
"Which parameters can be recovered from evidence?"
"Did the change actually improve the next run?"

A skill is therefore evidence-backed and replay-validated, rather than simply generated and remembered.

Benchmark

The repository includes a deterministic GitHub CI investigation benchmark:

demos/github_ci_learning_demo.py

The benchmark demonstrates a complete learning cycle.

Run 1 — Baseline

The agent investigates a failed CI run using:

list_workflow_runs
→ inspect_job_logs
→ inspect_commit

The final commit inspection fails because the baseline contains an invalid commit SHA.

Baseline score: 0.6250
Tool calls:      3
Failure type:    tool_failure
Learning

SkillFoundry analyzes the recorded trajectory.

It learns the reusable procedure:

list_workflow_runs
→ inspect_job_logs
→ inspect_commit

It also extracts actionable parameters from successful evidence in the same trajectory:

inspect_job_logs.run_id  = 2
inspect_job_logs.job_name = test
inspect_commit.sha       = def456ghi789

The learned information retains provenance back to the source trajectory.

Run 2 — Replay

The synthesized skill is replayed on a new trajectory using the learned procedure and parameters.

Replay score:     1.0000
Tool calls:       3

The measurable improvement is:

0.6250  →  1.0000

Score delta:     +0.3750
Tool-call delta:  0
Promotion

The Promotion Gate accepts the skill only when:

Replay score > Baseline score
AND
Replay tool calls <= Baseline tool calls

For the benchmark:

Improved:   True
Promoted:   True

This means the skill improved quality without increasing tool usage.

Technical Components
Core Execution Layer
src/syndicate/core/

Contains:

Task and tool models
Agent Executor
Deterministic GitHub Simulator
Trajectory Recorder
Trajectory Evaluator
Learning Layer
src/syndicate/learning/

Contains:

failure_analyzer.py
skill.py
skill_synthesizer.py
replay_engine.py
promotion_gate.py
learning_loop.py

Together these implement:

trajectory
→ failure analysis
→ skill synthesis
→ replay
→ measurable comparison
→ promotion
AO / OpenCode / TensorMux

AO is used as the agent orchestration environment.

The project is configured to use:

AO
 ↓
OpenCode
 ↓
TensorMux
 ↓
GLM-4.7-Flash

The deterministic benchmark remains offline and reproducible so that the learning result can be independently verified.

Reliability

The repository currently contains:

113 passing tests
0 failing tests

Run the test suite:

python -m pytest -q

Run the benchmark:

python demos/github_ci_learning_demo.py
Repository Structure
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
Design Principles
Evidence over memory

Skills are derived from real execution trajectories.

Replay over assumption

A generated skill must be tested on a fresh run.

Promotion over optimism

A skill is promoted only when measurable evidence shows improvement.

Determinism over demo magic

The benchmark uses a deterministic simulator and avoids hidden fallbacks.

Minimal architecture

The project focuses on the agent-learning loop instead of unrelated infrastructure.

Track 1

SkillFoundry targets Automated Agent Engineering by focusing on:

tool-use learning
execution trajectories
failure analysis
reusable skills
replay
measurable improvement
promotion gates
AO-based agent orchestration
The Core Insight

Agents should learn how to use the environment, not just remember the conversation.

SkillFoundry turns an execution failure into a testable skill and then asks the only question that matters:

Did the next run actually get better?
License

This project is part of the Syndicate Track 1 implementation for SkillFoundry.
