# Core Engine Architecture

Syndicate Track 1: Core Engine Architecture Documentation

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Component Design](#component-design)
3. [Data Flow](#data-flow)
4. [Design Decisions](#design-decisions)
5. [Testing Strategy](#testing-strategy)
6. [Future Enhancements](#future-enhancements)

## Architecture Overview

### High-Level Structure

```
┌─────────────────────────────────────────────────────────────┐
│                      Agent Executor                         │
│  (Task Planning, Tool Selection, Sequential Execution)      │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
┌────────▼─────────┐   ┌────────▼───────────┐
│   Tool Registry  │   │  GitHub Simulator  │
│ (Tool Manager)   │   │  (Deterministic)   │
└────────┬─────────┘   └────────┬───────────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
            ┌─────────────────┐
            │   Trajectory    │
            │    Recorder     │
            │ (Persistence)   │
            └────────┬────────┘
                     │
                     ▼
            ┌─────────────────┐
            │ Trajectory      │
            │   Evaluator     │
            │ (Scoring)       │
            └─────────────────┘
```

### Layered Architecture

The core engine follows a layered architecture:

1. **Model Layer**: Data structures (Task, Tool, ToolResult, etc.)
2. **Tool Layer**: Tool interfaces and implementations
3. **Execution Layer**: Task planning and execution
4. **Recording Layer**: Trajectory persistence
5. **Evaluation Layer**: Scoring and analysis

## Component Design

### 1. Core Models (`models/`)

#### Task Model

**Purpose**: Represents a task that can be executed by the agent.

**Data Structures**:
- `Task`: Main task entity
- `TaskStatus`: Task state enum
- `ToolInputSchema`: JSON Schema for tool inputs
- `ToolCall`: Represents a tool invocation
- `ToolResult`: Result of a tool execution

**Key Features**:
- Timestamp tracking (created_at, started_at, completed_at)
- Tool availability specification
- Success criteria definition
- Execution history

**Code Example**:
```python
from syndicate.core.models.task import Task, TaskStatus

task = Task(
    task_id="task-001",
    description="List GitHub workflow runs for main branch",
    available_tool_names=["github"],
    success_criteria="Should return non-empty list of workflow runs"
)

print(f"Status: {task.status.value}")  # pending
print(f"Created at: {task.created_at}")
print(f"Available tools: {task.available_tool_names}")
```

#### Tool Model

**Purpose**: Abstraction for tools that can be executed by the agent.

**Interface**:
- `name`: Unique identifier
- `description`: Human-readable description
- `input_schema`: JSON Schema defining expected inputs
- `execute(input_data: dict) -> dict`: Execute the tool

**Implementation**:
- Abstract base class `Tool`
- Concrete implementations for specific tools

**Code Example**:
```python
from syndicate.core.models.tool import Tool, ToolInputSchema

class MyTool(Tool):
    @property
    def name(self) -> str:
        return "my_tool"

    @property
    def description(self) -> str:
        return "A sample tool for demonstration."

    @property
    def input_schema(self) -> ToolInputSchema:
        return ToolInputSchema(
            type="object",
            description="Tool input schema",
            required=["message"],
            properties={
                "message": {
                    "type": "string",
                    "description": "Message to process"
                }
            }
        )

    def execute(self, input_data: dict) -> dict:
        return {
            "success": True,
            "output": f"Processed: {input_data['message']}"
        }

tool = MyTool()
result = tool.execute({"message": "hello"})
# {"success": True, "output": "Processed: hello"}
```

### 2. GitHub Simulator (`simulator/github_simulator.py`)

**Purpose**: Deterministic GitHub CI/CD simulator for testing.

**Scope**:
- Simulates GitHub repository operations
- Provides CI failure scenarios
- Deterministic behavior for reproducibility

**Tools Implemented**:
1. `list_workflow_runs`: List workflow runs for repo/branch
2. `inspect_workflow_run`: Get workflow run details
3. `inspect_job_logs`: Get job logs
4. `inspect_commit`: Get commit details
5. `inspect_pull_request`: Get PR details
6. `inspect_issue`: Get issue details
7. `search_repository`: Search commits/PRs/issues

**Scenarios**:
- `repocli/test-ci`: Simulates CI failures
- `repocli/integration-test`: Integration test scenarios

**Data Structure**:
```python
simulator = GithubSimulator()
simulator.initialize()

# Tool interface
github_tool = GithubTool(simulator)
result = github_tool.execute({
    "operation": "list_workflow_runs",
    "repo": "repocli/test-ci",
    "branch": "main"
})
```

### 3. Agent Executor (`executor/agent_executor.py`)

**Purpose**: Orchestrates task execution, tool selection, and planning.

**Key Components**:

#### ModelInterface
- Isolated LLM integration point
- Placeholder for TensorMux GLM-4.7-Flash
- Methods: `generate_answer()`, `parse_action()`

#### AgentExecutor
- Task planning
- Tool selection
- Sequential execution
- Final answer generation

**Execution Flow**:
1. Parse task description
2. Identify relevant tools
3. Generate execution plan (tool calls)
4. Execute tool calls sequentially
5. Generate final answer

**Code Example**:
```python
from syndicate.core.executor.agent_executor import ModelInterface, AgentExecutor

# Initialize
model = ModelInterface()
executor = AgentExecutor(model=model)
executor.register_tool("github", github_tool)

# Execute task
task = Task(
    task_id="demo",
    description="List workflow runs",
    available_tool_names=["github"],
    success_criteria="Should return runs"
)

result = executor.execute_task(task)

# Access results
print(f"Status: {result.status.value}")
print(f"Final Answer: {result.final_answer}")
print(f"Execution History: {result.execution_history}")
```

### 4. Trajectory Recorder (`recorder/trajectory_recorder.py`)

**Purpose**: Records and persists task execution trajectories.

**Storage Options**:
- Memory (default)
- SQLite (configurable)

**Recording Operations**:
- `record_trajectory_initialization()`: Task metadata
- `record_tool_call()`: Tool invocation
- `record_tool_result()`: Tool result
- `record_final_answer()`: Final answer
- `record_trajectory_summary()`: Performance metrics

**Trajectory Structure**:
```python
{
    "trajectory_id": "trajectory-001",
    "task_id": "task-001",
    "description": "Task description",
    "created_at": "2024-01-01T00:00:00Z",
    "tool_calls": [...],
    "tool_results": [...],
    "final_answer": "Task completed",
    "summary": {...}
}
```

**Code Example**:
```python
from syndicate.core.recorder.trajectory_recorder import TrajectoryRecorder, generate_trajectory_id

recorder = TrajectoryRecorder()
trajectory_id = generate_trajectory_id()

# Record trajectory
recorder.record_trajectory_initialization(
    task_id="task-001",
    description="Test task",
    available_tools=["tool1", "tool2"],
    success_criteria="Success",
    trajectory_id=trajectory_id
)

# Record steps
for tool_call in result.execution_history:
    recorder.record_tool_call(trajectory_id, tool_call)
    recorder.record_tool_result(trajectory_id, tool_call.result)

# Record final answer
recorder.record_final_answer(trajectory_id, "Done")

# Retrieve
trajectory = recorder.get_trajectory(trajectory_id)
```

### 5. Trajectory Evaluator (`evaluator/trajectory_evaluator.py`)

**Purpose**: Evaluates task completions across multiple dimensions.

**Evaluation Criteria**:

1. **Task Completeness**: Did task reach final answer?
2. **Correctness**: Are results aligned with success criteria?
3. **Efficiency**: Number of tool calls vs complexity?
4. **Reliability**: Success rate of tool calls?

**Scoring**:
- Overall score (0.0 - 1.0)
- Category (Excellent/Good/Fair/Poor)
- Detailed metrics per criterion

**Evaluation Flow**:
1. Retrieve trajectory
2. Parse execution history
3. Check completeness
4. Analyze correctness
5. Assess efficiency
6. Calculate reliability
7. Generate recommendations

**Code Example**:
```python
from syndicate.core.evaluator.trajectory_evaluator import TrajectoryEvaluator

evaluator = TrajectoryEvaluator()
evaluation = evaluator.evaluate(trajectory_id, recorder)

print(f"Score: {evaluation['overall_score']}")
print(f"Category: {evaluation['category']}")
print(f"Details:")
for criterion, score in evaluation['details'].items():
    print(f"  {criterion}: {score}")
```

## Data Flow

### Complete Workflow

```
1. Task Definition
   ↓
2. Executor Initialization
   - Register tools
   - Create ModelInterface
   ↓
3. Task Planning
   - Identify tools
   - Generate plan
   ↓
4. Tool Execution
   - Execute tools sequentially
   - Record tool calls/results
   ↓
5. Final Answer Generation
   - Generate final answer
   ↓
6. Trajectory Recording
   - Record all steps
   - Persist trajectory
   ↓
7. Evaluation
   - Score trajectory
   - Generate insights
```

### Data Structure Flow

```
Task → [Tool Calls] → Tool Results → Trajectory → Evaluation
      ↓                      ↓
   Recorder              Recorder
      ↓                      ↓
   Trajectory           Trajectory
```

## Design Decisions

### 1. Layered Architecture
**Rationale**: Separates concerns, enables modular testing, facilitates extensibility.

**Benefits**:
- Clear boundaries between components
- Easy to replace one layer without affecting others
- Testable in isolation
- Simpler to maintain

### 2. Dataclass Models
**Rationale**: Type safety, immutability, built-in serialization.

**Benefits**:
- Clear data contracts
- IDE support (autocomplete, type checking)
- Built-in serialization support
- Simple to extend with new fields

### 3. Tool Abstraction
**Rationale**: Flexibility for adding new tools without modifying executor.

**Benefits**:
- Pluggable tool ecosystem
- Consistent interface
- Easy to mock for testing
- Supports multiple tool types

### 4. Deterministic Simulator
**Rationale**: Reproducible testing, no external dependencies.

**Benefits**:
- Reliable test results
- Fast execution
- No API rate limits
- Consistent behavior across runs

### 5. Trajectory-Based Evaluation
**Rationale**: Comprehensive evaluation beyond just success/failure.

**Benefits**:
- Rich insights into execution patterns
- Identifies optimization opportunities
- Supports continuous improvement
- Enables analytics and benchmarking

### 6. Placeholder LLM Integration
**Rationale**: Minimal viable core, defers non-critical integration.

**Benefits**:
- Focus on core functionality
- Easier to test deterministically
- Clear path for future integration
- Maintains isolation

### 7. Exclusion of Non-Core Features
**Rationale**: Minimize scope for Track 1 deliverable.

**Exclusions**:
- Skill synthesis (Track 2)
- Long-term memory (Track 3)
- Promotion gate (Track 4)
- Web UI (Track 5)
- Domain-specific features (Track 6)

## Testing Strategy

### Test Coverage

1. **Unit Tests**
   - Model validation and behavior
   - Tool interface implementation
   - Simulator tools and scenarios
   - Recorder operations
   - Evaluator scoring logic

2. **Integration Tests**
   - Full executor workflow
   - End-to-end trajectory recording
   - Complete evaluation pipeline
   - Multiple tools in sequence

3. **Scenario Tests**
   - Successful execution
   - Failed execution
   - Incomplete execution
   - Edge cases and error handling

### Test Organization

```
tests/
├── __init__.py
├── run_tests.py         # Test runner
├── test_models.py       # Task, Tool models
├── test_simulator.py    # GithubSimulator
├── test_executor.py     # AgentExecutor
├── test_recorder.py     # TrajectoryRecorder
└── test_evaluator.py    # TrajectoryEvaluator
```

### Test Execution

```bash
# Run all tests
cd tests
python run_tests.py

# Run specific module
python -m unittest tests.test_models

# Run specific test class
python -m unittest tests.test_simulator.TestGithubSimulator
```

## Future Enhancements

### Short-term (Track 2)
1. **Integrate Real LLM Provider**
   - TensorMux GLM-4.7-Flash API integration
   - Enhanced prompt templates
   - Streaming responses

2. **SQLite Persistence**
   - Configurable storage backend
   - Query and search trajectories
   - Export/import functionality

3. **Error Handling**
   - Retry logic for transient failures
   - Tool selection fallback
   - Error recovery strategies

### Medium-term (Track 3)
1. **Long-term Memory**
   - Memory retrieval system
   - Experience aggregation
   - Learned preferences

2. **Enhanced Evaluation**
   - Domain-specific scoring
   - Performance benchmarks
   - Recommendations for improvement

3. **Skill Synthesis**
   - Tool aggregation
   - Composition patterns
   - Reusable components

### Long-term (Track 4+)
1. **Promotion Gate**
   - Performance thresholds
   - Automated promotion decisions
   - Risk assessment

2. **Web UI**
   - Dashboard for monitoring
   - Interactive exploration
   - Analytics visualization

3. **Multi-Domain Support**
   - Domain-specific rules
   - Specialized tools
   - Domain ontologies

## References

- Project Repository: https://github.com/Aayush-pixel29/my-syndicate-project.git
- Syndicate Track 1: Minimal working slice
- SkillFoundry Architecture Guidelines

## License

This project is part of the Syndicate Track 1 implementation for SkillFoundry.
