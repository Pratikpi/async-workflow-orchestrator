"""Unit tests for API endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from src.db import Base, get_db, Workflow, Task, WorkflowStatus, TaskStatus


# Test database setup with StaticPool to share in-memory database across threads
engine = create_engine(
    "sqlite:///:memory:", 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    """Set up test database before each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


# Create test client after fixture is defined
@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_create_workflow(client):
    """Test creating a workflow."""
    workflow_data = {
        "name": "Test Workflow",
        "description": "A test workflow",
        "config": {"test": True}
    }
    
    response = client.post("/workflows/", json=workflow_data)
    assert response.status_code == 201
    
    data = response.json()
    assert data["name"] == "Test Workflow"
    assert data["description"] == "A test workflow"
    assert data["status"] == "INIT"
    assert "id" in data


def test_list_workflows(client):
    """Test listing workflows."""
    # Create some workflows
    for i in range(3):
        client.post("/workflows/", json={"name": f"Workflow {i+1}"})
    
    response = client.get("/workflows/")
    assert response.status_code == 200
    
    workflows = response.json()
    assert len(workflows) == 3


def test_get_workflow(client):
    """Test getting a specific workflow."""
    # Create a workflow
    create_response = client.post("/workflows/", json={"name": "Test Workflow"})
    workflow_id = create_response.json()["id"]
    
    # Get the workflow
    response = client.get(f"/workflows/{workflow_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == workflow_id
    assert data["name"] == "Test Workflow"


def test_get_nonexistent_workflow(client):
    """Test getting a workflow that doesn't exist."""
    response = client.get("/workflows/999")
    assert response.status_code == 404


def test_update_workflow(client):
    """Test updating a workflow."""
    # Create a workflow
    create_response = client.post("/workflows/", json={"name": "Original Name"})
    workflow_id = create_response.json()["id"]
    
    # Update the workflow
    update_data = {"name": "Updated Name", "description": "New description"}
    response = client.put(f"/workflows/{workflow_id}", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["description"] == "New description"


def test_delete_workflow(client):
    """Test deleting a workflow."""
    # Create a workflow
    create_response = client.post("/workflows/", json={"name": "To Delete"})
    workflow_id = create_response.json()["id"]
    
    # Delete the workflow
    response = client.delete(f"/workflows/{workflow_id}")
    assert response.status_code == 204
    
    # Verify it's gone
    get_response = client.get(f"/workflows/{workflow_id}")
    assert get_response.status_code == 404


def test_create_task(client):
    """Test creating a task."""
    # Create a workflow first
    workflow_response = client.post("/workflows/", json={"name": "Test Workflow"})
    workflow_id = workflow_response.json()["id"]
    
    # Create a task
    task_data = {
        "workflow_id": workflow_id,
        "name": "Test Task",
        "task_type": "sleep",
        "config": {"duration": 1}
    }
    
    response = client.post("/tasks/", json=task_data)
    assert response.status_code == 201
    
    data = response.json()
    assert data["name"] == "Test Task"
    assert data["task_type"] == "sleep"
    assert data["status"] == "pending"


def test_list_tasks(client):
    """Test listing tasks."""
    # Create workflow and tasks
    workflow_response = client.post("/workflows/", json={"name": "Test Workflow"})
    workflow_id = workflow_response.json()["id"]
    
    for i in range(3):
        client.post("/tasks/", json={
            "workflow_id": workflow_id,
            "name": f"Task {i+1}",
            "task_type": "sleep"
        })
    
    response = client.get("/tasks/")
    assert response.status_code == 200
    
    tasks = response.json()
    assert len(tasks) == 3


def test_get_workflow_tasks(client):
    """Test getting tasks for a specific workflow."""
    # Create workflow and tasks
    workflow_response = client.post("/workflows/", json={"name": "Test Workflow"})
    workflow_id = workflow_response.json()["id"]
    
    for i in range(2):
        client.post("/tasks/", json={
            "workflow_id": workflow_id,
            "name": f"Task {i+1}",
            "task_type": "sleep"
        })
    
    response = client.get(f"/workflows/{workflow_id}/tasks")
    assert response.status_code == 200
    
    tasks = response.json()
    assert len(tasks) == 2


def test_get_execution_stats(client):
    """Test getting execution statistics."""
    # Create some workflows
    client.post("/workflows/", json={"name": "Workflow 1"})
    client.post("/workflows/", json={"name": "Workflow 2"})
    
    response = client.get("/execution/stats")
    assert response.status_code == 200
    
    stats = response.json()
    assert "worker_pool" in stats
    assert "workflows" in stats
    assert stats["workflows"]["total"] == 2
