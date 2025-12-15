# Async Workflow Orchestrator

A lightweight, production-quality workflow orchestrator built with Python, demonstrating modern backend engineering skills through async I/O coordination, thread-based parallel execution, and state machine-driven workflow management.

## 🎯 Project Purpose

This project showcases real backend engineering capabilities by combining:
- **Async orchestration** using `asyncio` for event-driven coordination
- **Thread-based execution** using `ThreadPoolExecutor` for parallel task processing
- **State machine design** using the `transitions` library
- **REST APIs** with FastAPI
- **Database persistence** with SQLAlchemy (PostgreSQL/SQLite)
- **Workflow history** with full audit trail
- **Unit testing** with pytest
- **Clean architecture** with modular, testable code

Perfect for demonstrating backend skills to recruiters and engineering teams.

## 🏗️ Architecture Overview

### Workflow State Machine

The system implements a complete workflow lifecycle with the following states:

```
INIT → PREPARE → EXECUTE → VALIDATE → COMPLETE
  ↓       ↓         ↓          ↓
  └──────→ FAILED ←────────────┘
                ↓
           CANCELLED
```

**State Descriptions:**
- **INIT**: Initial state, workflow resources are initialized
- **PREPARE**: Data and resources are prepared for execution
- **EXECUTE**: Main computation/processing occurs
- **VALIDATE**: Results are validated for correctness
- **COMPLETE**: Workflow successfully finished
- **FAILED**: Workflow encountered an error (can be retried)
- **CANCELLED**: Workflow was manually cancelled

### Core Components

1. **Workflow Orchestrator** (`src/core/orchestrator.py`)
   - Implements state machine using `transitions` library
   - Manages workflow lifecycle: INIT → PREPARE → EXECUTE → VALIDATE → COMPLETE
   - Uses `asyncio` for event-driven coordination and callbacks
   - Tracks all state transitions in database for audit trail
   - Supports automatic and manual step-by-step execution
   - Handles retries from failed state

2. **Worker Manager** (`src/core/worker_manager.py`)
   - Thread pool executor for parallel task execution
   - Uses `queue.Queue` for thread-safe task queuing
   - Each workflow state maps to a specific task type
   - Tasks run in worker threads with results pushed back to orchestrator
1.  **Workflow Orchestrator** (`src/core/orchestrator.py`)
    -   Implements state machine using `transitions` library
    -   Manages workflow lifecycle: INIT → PREPARE → EXECUTE → VALIDATE → COMPLETE
    -   Uses `asyncio` for event-driven coordination and callbacks
    -   Tracks all state transitions in database for audit trail
    -   Supports automatic and manual step-by-step execution
    -   Handles retries from failed state

2.  **Worker Manager** (`src/core/worker_manager.py`)
    -   Thread pool executor for parallel task execution
    -   Uses `queue.Queue` for thread-safe task queuing
    -   Each workflow state maps to a specific task type
    -   Tasks run in worker threads with results pushed back to orchestrator
    -   Configurable worker pool size

3.  **Database Layer** (`src/db/`)
    -   SQLAlchemy ORM models for workflows, tasks, and transitions
    -   Supports both PostgreSQL (production) and SQLite (development)
    -   Tracks workflow metadata, current state, retry count, and results
    -   Complete transition history for debugging and audit

4.  **REST API** (`src/api/`)
    -   FastAPI-based RESTful endpoints
    -   Workflow lifecycle management (start, status, next step, retry, delete)
    -   Background task execution for non-blocking operations
    -   Input validation with Pydantic schemas

### Hybrid Concurrency Model

The system demonstrates a production-grade hybrid concurrency pattern:

**Asyncio (async I/O):**
- Scheduling workflow transitions
- Handling timers and callbacks
- Managing orchestration events
- Serving async API requests
- Non-blocking coordination

**Thread Workers:**
- CPU-bound or blocking tasks
- Parallel job execution
- Safe communication through `queue.Queue`
- Task isolation and fault tolerance

This hybrid design mirrors real backend architectures where async and threads coexist for optimal performance.

## 📁 Project Structure

```
async-workflow-orchestrator/
├── config/
│   ├── __init__.py
│   └── settings.py          # Application configuration
├── src/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── workflow_api.py  # Main workflow endpoints (/workflow/*)
│   │   ├── routes.py        # Additional workflow CRUD endpoints
│   │   ├── tasks.py         # Task CRUD endpoints
│   │   ├── execution.py     # Execution control endpoints
│   │   └── schemas.py       # Pydantic schemas
│   ├── core/
│   │   ├── __init__.py
│   │   ├── orchestrator.py  # State machine orchestrator
│   │   └── worker_manager.py # Thread pool worker manager
│   └── db/
│       ├── __init__.py
│       ├── models.py         # SQLAlchemy models
│       └── database.py       # Database session management
├── tests/
│   ├── __init__.py
│   ├── test_orchestrator.py
│   ├── test_worker_manager.py
│   └── test_api.py
├── main.py                   # Application entry point
├── demo.py                   # Demonstration script
├── requirements.txt
├── .env.example
├── .gitignore
├── pytest.ini
├── QUICKSTART.md
├── PROJECT_SUMMARY.md
└── README.md
```

## 🚀 Getting Started

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Optional: PostgreSQL (for production use)

### Installation

1. **Clone the repository**
   ```bash
   cd async-workflow-orchestrator
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env to configure your settings
   ```

### Configuration

Edit the `.env` file to configure the application:

```bash
# For SQLite (development)
DATABASE_URL=sqlite:///./workflow.db

# For PostgreSQL (production)
# DATABASE_URL=postgresql://user:password@localhost:5432/workflow_db

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true

# Worker Configuration
MAX_WORKERS=5
TASK_TIMEOUT=300

# Logging
LOG_LEVEL=INFO
```

### Running the Application

**Start the server:**
```bash
python main.py
```

The API will be available at:
- API: `http://localhost:8000`
- Interactive docs: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`

**Run the demonstration:**
```bash
# In another terminal (while server is running)
python demo.py
```

This will demonstrate automatic workflow execution through all states.

## 📖 API Usage

### Core Workflow Endpoints

#### 1. Start a Workflow

Start a new workflow that executes automatically through all states.

```bash
curl -X POST "http://localhost:8000/workflow/start" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Data Processing Pipeline",
    "description": "Process and transform data",
    "config": {"priority": "high"}
  }'
```

Response:
```json
{
  "message": "Workflow started",
  "workflow_id": 1,
  "name": "Data Processing Pipeline",
  "status": "INIT",
  "current_state": "INIT"
}
```

#### 2. Get Workflow State

Get current workflow state with complete history.

```bash
curl "http://localhost:8000/workflow/1"
```

Response:
```json
{
  "workflow_id": 1,
  "name": "Data Processing Pipeline",
  "status": "EXECUTE",
  "current_state": "EXECUTE",
  "retries": 0,
  "started_at": "2025-11-27T10:01:00",
  "completed_at": null,
  "error_message": null,
  "next_trigger": "validate",
  "transitions": [
    {
      "from_state": "INIT",
      "to_state": "PREPARE",
      "trigger": "prepare",
      "timestamp": "2025-11-27T10:01:05"
    },
    {
      "from_state": "PREPARE",
      "to_state": "EXECUTE",
      "trigger": "execute",
      "timestamp": "2025-11-27T10:01:12"
    }
  ],
  "task_results": {
    "INIT": {"status": "initialized", "message": "Workflow resources initialized"},
    "PREPARE": {"status": "prepared", "files_created": 3}
  }
}
```

#### 3. Trigger Next Step (Manual Control)

Manually execute the next step in the workflow.

```bash
curl -X POST "http://localhost:8000/workflow/1/next"
```

Response:
```json
{
  "message": "Next step triggered for workflow 1",
  "workflow_id": 1,
  "current_state": "PREPARE",
  "status": "PREPARE"
}
```

#### 4. Retry Failed Workflow

Retry a workflow that failed, restarting from INIT state.

```bash
curl -X POST "http://localhost:8000/workflow/1/retry"
```

Response:
```json
{
  "message": "Workflow 1 retry initiated",
  "workflow_id": 1,
  "retries": 1,
  "current_state": "INIT",
  "status": "INIT"
}
```

#### 5. Delete Workflow

Delete a completed or failed workflow.

```bash
curl -X DELETE "http://localhost:8000/workflow/1"
```

### Additional Endpoints

#### Get Execution Statistics

```bash
curl "http://localhost:8000/execution/stats"
```

Response:
```json
{
  "worker_pool": {
    "max_workers": 5,
    "active_tasks": 2,
    "queue_size": 0
  },
  "workflows": {
    "total": 10,
    "init": 1,
    "prepare": 0,
    "execute": 1,
    "validate": 0,
    "complete": 6,
    "failed": 1,
    "cancelled": 1
  }
}
```

## 🧪 Running Tests

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=src --cov-report=html
```

Run specific test file:
```bash
pytest tests/test_orchestrator.py -v
```

## 🔧 Workflow State Tasks

Each workflow state automatically executes a specific task type:

| State | Task Type | Description | Execution Time |
|-------|-----------|-------------|----------------|
| **INIT** | initialize | Set up initial resources and configuration | ~0.5s |
| **PREPARE** | prepare | Prepare data and resources for processing | ~0.7s |
| **EXECUTE** | execute | Run main computation or processing logic | ~1.0s |
| **VALIDATE** | validate | Validate results and check for correctness | ~0.6s |
| **COMPLETE** | complete | Finalize workflow and cleanup | ~0.3s |

### Task Execution Details

**INIT State (initialize):**
```python
# Task: Initialize workflow resources
# Returns: {"status": "initialized", "message": "Workflow resources initialized"}
```

**PREPARE State (prepare):**
```python
# Task: Prepare data and create temporary files
# Returns: {"status": "prepared", "files_created": 3, "message": "Data and resources prepared"}
```

**EXECUTE State (execute):**
```python
# Task: Main computation (CPU-intensive)
# Config: {"iterations": 5000}
# Returns: {"status": "executed", "computation_result": 123456, "iterations": 5000}
```

**VALIDATE State (validate):**
```python
# Task: Validate computation results
# Returns: {"status": "validated", "validation_passed": true, "checks_performed": 5}
```

**COMPLETE State (complete):**
```python
# Task: Finalization and cleanup
# Returns: {"status": "completed", "message": "Workflow finalized"}
```

### Adding Custom Task Types

Extend `WorkerManager._run_workflow_task_logic()` in `src/core/worker_manager.py`:

```python
elif task_type == "custom_task":
    # Your custom logic here
    result = perform_custom_operation(config)
    return {"status": "success", "result": result}
```

## 🎯 Key Features

- ✅ **State Machine Design**: Workflow lifecycle managed by `transitions` library with clear state progression
- ✅ **Hybrid Concurrency**: Combines `asyncio` for coordination with thread pools for execution
- ✅ **Automatic Execution**: Workflows progress automatically through all states
- ✅ **Manual Control**: Step-by-step execution with `/workflow/{id}/next` endpoint
- ✅ **Retry Mechanism**: Failed workflows can be retried from INIT state
- ✅ **Workflow History**: Complete audit trail of all state transitions
- ✅ **Database Persistence**: SQLAlchemy with PostgreSQL/SQLite support
- ✅ **RESTful API**: Complete FastAPI-based REST interface
- ✅ **Background Execution**: Non-blocking workflow execution
- ✅ **Extensible**: Easy to add new workflow states and task types
- ✅ **Production-Ready**: Includes logging, error handling, and comprehensive testing
- ✅ **Lightweight**: No Docker, Kubernetes, or enterprise tool dependencies
- ✅ **Well-Documented**: Complete API docs and example scripts

## 🔍 How It Works

### Workflow Execution Flow

1. **Client starts workflow** via `POST /workflow/start`
   - Workflow created in database with status=INIT
   - Background task initiated for execution

2. **Orchestrator begins state progression**
   - For each state (INIT → PREPARE → EXECUTE → VALIDATE → COMPLETE):
     - Submit task to worker thread pool
     - Worker executes task logic
     - Worker returns result
     - Orchestrator receives result
     - State machine transition triggered
     - Transition logged to database

3. **Worker threads execute tasks**
   - Tasks run in parallel thread pool
   - Each state has specific task implementation
   - Results returned via futures
   - Thread-safe communication with orchestrator

4. **Async coordination**
   - Event queue manages state transitions
   - Non-blocking event processing loop
   - Callbacks trigger next state progression
   - Timers and async I/O handled efficiently

5. **State transitions logged**
   - Every transition recorded in database
   - Includes: from_state, to_state, trigger, timestamp
   - Provides complete audit trail
   - Enables debugging and monitoring

### Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant API
    participant Orchestrator
    participant Worker as Worker Thread
    participant DB as Database

    Client->>API: POST /workflow/start
    activate API
    API->>DB: Create Workflow (INIT)
    activate DB
    DB-->>API: workflow_id
    deactivate DB
    API-->>Client: 201 Created
    deactivate API

    Note right of API: Background Task Started

    API->>Orchestrator: execute_automatic()
    activate Orchestrator

    loop For each state [INIT, PREPARE, EXECUTE, VALIDATE]
        Orchestrator->>Worker: submit_task(current_state)
        activate Worker
        Worker->>Worker: Execute Task Logic
        Worker-->>Orchestrator: Task Result
        deactivate Worker

        Orchestrator->>Orchestrator: Determine Next Trigger
        Orchestrator->>DB: Log Transition & Update State
        activate DB
        DB-->>Orchestrator: Success
        deactivate DB
    end

    Orchestrator->>DB: Log Final Transition (COMPLETE)
    activate DB
    DB-->>Orchestrator: Success
    deactivate DB
    deactivate Orchestrator
```

## 🔍 Workflow States

Workflows transition through the following states with specific purposes:

### State Transition Rules

```mermaid
stateDiagram-v2
    direction LR

    state "In Progress" as Running {
        direction LR
        INIT --> PREPARE: prepare
        PREPARE --> EXECUTE: execute
        EXECUTE --> VALIDATE: validate
    }

    [*] --> INIT
    VALIDATE --> COMPLETE: complete
    
    Running --> FAILED: fail
    Running --> CANCELLED: cancel
    
    FAILED --> INIT: retry
    
    COMPLETE --> [*]
    CANCELLED --> [*]
```

State transitions are logged in the `workflow_transitions` table with full metadata.

## 📊 Database Schema

The system uses three main tables to track workflow execution:

### Workflows Table
Stores workflow definitions and current state.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `name` | String(255) | Workflow name |
| `description` | Text | Workflow description |
| `status` | Enum | Current workflow status (INIT, PREPARE, EXECUTE, VALIDATE, COMPLETE, FAILED, CANCELLED) |
| `current_state` | String(50) | Current state in workflow |
| `config` | JSON | Workflow configuration and metadata |
| `retries` | Integer | Number of retry attempts |
| `created_at` | DateTime | Workflow creation timestamp |
| `updated_at` | DateTime | Last update timestamp |
| `started_at` | DateTime | Workflow start timestamp |
| `completed_at` | DateTime | Workflow completion timestamp |
| `error_message` | Text | Error message if failed |

### Workflow Transitions Table
Complete audit trail of all state transitions.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `workflow_id` | Integer | Foreign key to workflows |
| `from_state` | String(50) | Source state |
| `to_state` | String(50) | Destination state |
| `trigger` | String(100) | Transition trigger name |
| `metadata` | JSON | Additional transition information |
| `created_at` | DateTime | Transition timestamp |

### Tasks Table (Optional)
For workflows that use explicit task definitions.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `workflow_id` | Integer | Foreign key to workflows |
| `name` | String(255) | Task name |
| `description` | Text | Task description |
| `status` | Enum | Task status |
| `task_type` | String(100) | Type of task |
| `config` | JSON | Task-specific configuration |
| `result` | JSON | Task execution result |
| `created_at` | DateTime | Task creation timestamp |
| `updated_at` | DateTime | Last update timestamp |
| `started_at` | DateTime | Task start timestamp |
| `completed_at` | DateTime | Task completion timestamp |
| `error_message` | Text | Error message if failed |
| `retry_count` | Integer | Number of retry attempts |

### Example Queries

**Get workflow with full history:**
```sql
SELECT w.*, 
       json_agg(wt.* ORDER BY wt.created_at) as transitions
FROM workflows w
LEFT JOIN workflow_transitions wt ON w.id = wt.workflow_id
WHERE w.id = 1
GROUP BY w.id;
```

**Count workflows by status:**
```sql
SELECT status, COUNT(*) 
FROM workflows 
GROUP BY status;
```

**Get transition timeline:**
```sql
SELECT from_state, to_state, trigger, created_at
FROM workflow_transitions
WHERE workflow_id = 1
ORDER BY created_at;
```

## 💡 Usage Examples

### Example 1: Automatic Workflow Execution

```python
import requests

# Start a workflow (automatic execution)
response = requests.post("http://localhost:8000/workflow/start", json={
    "name": "Data Pipeline",
    "description": "Process customer data",
    "config": {"priority": "high"}
})
workflow_id = response.json()["workflow_id"]

# Wait a few seconds for execution
import time
time.sleep(5)

# Check status
status = requests.get(f"http://localhost:8000/workflow/{workflow_id}").json()
print(f"Status: {status['status']}")
print(f"Current State: {status['current_state']}")
print(f"Transitions: {len(status['transitions'])}")
```

### Example 2: Manual Step-by-Step Execution

```python
import requests
import time

# Start a workflow
response = requests.post("http://localhost:8000/workflow/start", json={
    "name": "Manual Pipeline"
})
workflow_id = response.json()["workflow_id"]

# Manually trigger each step
states = ["INIT", "PREPARE", "EXECUTE", "VALIDATE"]
for state in states:
    time.sleep(2)  # Wait for current step
    requests.post(f"http://localhost:8000/workflow/{workflow_id}/next")
    status = requests.get(f"http://localhost:8000/workflow/{workflow_id}").json()
    print(f"Completed {state}, now in {status['current_state']}")
```

### Example 3: Handling Failures and Retries

```python
import requests

# Simulate workflow that might fail
response = requests.post("http://localhost:8000/workflow/start", json={
    "name": "Risky Pipeline"
})
workflow_id = response.json()["workflow_id"]

# Check if it failed
time.sleep(3)
status = requests.get(f"http://localhost:8000/workflow/{workflow_id}").json()

if status['status'] == 'FAILED':
    print(f"Workflow failed: {status['error_message']}")
    
    # Retry the workflow
    requests.post(f"http://localhost:8000/workflow/{workflow_id}/retry")
    print("Workflow retrying...")
```

### Example 4: Using the Demo Script

```bash
# Run the comprehensive example (runs all demos)
python demo.py

# Run in interactive mode
python demo.py --interactive
```

Output:
```
======================================================================
  ASYNC WORKFLOW ORCHESTRATOR - DEMONSTRATION
======================================================================

======================================================================
  Starting New Workflow
======================================================================

✓ Workflow Created:
  ID: 1
  Name: Data Processing Pipeline
  Status: INIT
  State: INIT

======================================================================
  Monitoring Workflow 1
======================================================================

[10:15:00] State: INIT (Status: INIT)
[10:15:01] State: PREPARE (Status: PREPARE)
[10:15:02] State: EXECUTE (Status: EXECUTE)
[10:15:03] State: VALIDATE (Status: VALIDATE)
[10:15:04] State: COMPLETE (Status: COMPLETE)

✓ Workflow COMPLETE

======================================================================
  Workflow 1 Details
======================================================================

Name: Data Processing Pipeline
Status: COMPLETE
Current State: COMPLETE
Retries: 0
Started: 2025-11-27T10:15:00
Completed: 2025-11-27T10:15:04

Transition History:
  1. INIT → PREPARE (trigger: prepare) at 2025-11-27T10:15:01
  2. PREPARE → EXECUTE (trigger: execute) at 2025-11-27T10:15:02
  3. EXECUTE → VALIDATE (trigger: validate) at 2025-11-27T10:15:03
  4. VALIDATE → COMPLETE (trigger: complete) at 2025-11-27T10:15:04

Task Results:
  INIT: {
    "status": "initialized",
    "message": "Workflow resources initialized"
  }
  PREPARE: {
    "status": "prepared",
    "message": "Data and resources prepared",
    "files_created": 3
  }
  EXECUTE: {
    "status": "executed",
    "computation_result": 41666625,
    "iterations": 5000
  }
  VALIDATE: {
    "status": "validated",
    "validation_passed": true,
    "checks_performed": 5
  }
```

## 🛠️ Development

### Setting Up Development Environment

```bash
# Install development dependencies
pip install -r requirements.txt

# Run with auto-reload
python main.py  # API_RELOAD=true in .env
```

### Code Style

The project follows PEP 8 style guidelines. Consider using:
- `black` for code formatting
- `flake8` for linting
- `mypy` for type checking

## 📝 Logging

Logs are written to:
- Console (stdout)
- `workflow_orchestrator.log` file

Log levels can be configured via the `LOG_LEVEL` environment variable.

## 🚦 Production Deployment

### Using PostgreSQL

1. Install PostgreSQL
2. Create database:
   ```sql
   CREATE DATABASE workflow_db;
   ```
3. Update `.env`:
   ```
   DATABASE_URL=postgresql://user:password@localhost:5432/workflow_db
   ```

### Running as a Service

Use systemd, supervisor, or similar process managers:

```ini
[Unit]
Description=Async Workflow Orchestrator
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/async-workflow-orchestrator
ExecStart=/path/to/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## 🎓 What This Project Demonstrates

This project showcases essential backend engineering skills:

### 1. **Concurrency Patterns**
- Hybrid async/thread model (real-world pattern)
- Non-blocking I/O with `asyncio`
- Thread pool management for CPU-bound tasks
- Thread-safe queue communication

### 2. **State Machine Design**
- Clean state transitions using `transitions` library
- Event-driven architecture
- Predictable workflow lifecycle
- Error handling and recovery

### 3. **API Design**
- RESTful endpoint design
- Input validation with Pydantic
- Background task execution
- Proper HTTP status codes

### 4. **Database Engineering**
- ORM design with SQLAlchemy
- Transaction management
- Audit trail implementation
- Support for multiple databases

### 5. **Architecture**
- Clean separation of concerns
- Modular, testable code
- Dependency injection
- Configuration management

### 6. **Testing**
- Unit tests with pytest
- Async test support
- Mock objects and fixtures
- API endpoint testing

### 7. **Production Practices**
- Comprehensive logging
- Error handling
- Retry mechanisms
- Documentation

## 📈 Project Complexity Breakdown

| Component | Lines of Code | Complexity | Purpose |
|-----------|---------------|------------|---------|
| **Orchestrator** | ~400 | High | State machine, async coordination |
| **Worker Manager** | ~300 | Medium | Thread pool, task execution |
| **API Layer** | ~500 | Medium | REST endpoints, validation |
| **Database Models** | ~150 | Low | Data persistence |
| **Tests** | ~400 | Medium | Quality assurance |
| **Total** | ~1,750 | Production-Ready | Complete backend system |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- **FastAPI**: Modern, high-performance web framework
- **SQLAlchemy**: Powerful ORM and database toolkit
- **transitions**: Elegant state machine library
- **pytest**: Comprehensive testing framework
- **uvicorn**: Lightning-fast ASGI server

## 📧 Support

For issues, questions, or contributions, please open an issue on the repository.

---

## 🌟 Why This Project Stands Out

✅ **Real Architecture**: Uses patterns from production systems  
✅ **Modern Stack**: Latest Python async features and frameworks  
✅ **Complete**: From API to database to testing  
✅ **Documented**: Every component explained  
✅ **Runnable**: Works out of the box with SQLite  
✅ **Extensible**: Easy to add features  
✅ **Educational**: Demonstrates multiple concepts  

**Perfect for**: Backend Engineer roles, System Design discussions, Portfolio projects, Learning modern Python patterns

---

Built with ❤️ for clean, production-quality Python backend development.
