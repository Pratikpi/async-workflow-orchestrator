# Quick Start Guide

## Setup (5 minutes)

1. **Install dependencies:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # .env is already configured for SQLite - no changes needed!
   ```

3. **Start the server:**
   ```bash
   python main.py
   ```

   You should see:
   ```
   INFO: Starting Async Workflow Orchestrator
   INFO: Database initialized
   INFO: Uvicorn running on http://0.0.0.0:8000
   ```

## Try It Out (2 minutes)

### Option 1: Use the Demo Script

In a new terminal:
```bash
python demo.py
```

This will demonstrate automatic workflow execution with full output.

### Option 2: Manual API Testing

**Start a workflow:**
```bash
curl -X POST http://localhost:8000/workflow/start \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Workflow", "description": "My first workflow"}'
```

**Check status (replace {id} with workflow_id from above):**
```bash
curl http://localhost:8000/workflow/1
```

**View API docs:**
Open http://localhost:8000/docs in your browser

## What Happens?

1. Workflow starts in **INIT** state
2. Automatically progresses through:
   - **INIT** → resources initialized (~0.5s)
   - **PREPARE** → data prepared (~0.7s)
   - **EXECUTE** → computation runs (~1.0s)
   - **VALIDATE** → results validated (~0.6s)
   - **COMPLETE** → workflow finished (~0.3s)

3. All transitions logged to database
4. Full history available via API

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [demo.py](demo.py) for usage patterns
- Explore the API at http://localhost:8000/docs
- Run tests: `pytest`

## Common Endpoints

```bash
# Start workflow (automatic execution)
POST /workflow/start

# Get workflow status and history
GET /workflow/{id}

# Manually trigger next step
POST /workflow/{id}/next

# Retry failed workflow
POST /workflow/{id}/retry

# Delete workflow
DELETE /workflow/{id}

# System statistics
GET /execution/stats
```

## Troubleshooting

**Port 8000 already in use:**
```bash
# Change port in .env
API_PORT=8001
```

**Database errors:**
```bash
# Delete and recreate
rm workflow.db
python main.py  # Will recreate automatically
```

**Import errors:**
```bash
# Make sure virtual environment is activated
source venv/bin/activate
pip install -r requirements.txt
```

## Architecture at a Glance

```
Client Request
     ↓
FastAPI REST API
     ↓
Workflow Orchestrator (asyncio)
     ↓
Worker Manager (ThreadPoolExecutor)
     ↓
Worker Threads (execute tasks)
     ↓
Database (SQLAlchemy)
```

Enjoy exploring the Async Workflow Orchestrator! 🚀
