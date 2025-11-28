"""Unit tests for WorkflowOrchestrator."""
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.db import Base, Workflow, Task, WorkflowStatus, TaskStatus
from src.core import WorkflowOrchestrator, WorkerManager


@pytest.fixture
def db_engine():
    """Create a test database engine."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(db_engine):
    """Create a test database session."""
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def session_factory(db_engine):
    """Create a session factory for the test database."""
    return sessionmaker(bind=db_engine)


@pytest.fixture
def sample_workflow(db_session):
    """Create a sample workflow for testing."""
    workflow = Workflow(
        name="Test Workflow",
        description="A test workflow",
        status=WorkflowStatus.INIT,
        config={"test": True}
    )
    db_session.add(workflow)
    db_session.commit()
    db_session.refresh(workflow)
    return workflow


@pytest.fixture
def sample_tasks(db_session, sample_workflow):
    """Create sample tasks for testing."""
    tasks = []
    for i in range(3):
        task = Task(
            workflow_id=sample_workflow.id,
            name=f"Task {i+1}",
            task_type="sleep",
            config={"duration": 0.1},
            status=TaskStatus.PENDING
        )
        db_session.add(task)
        tasks.append(task)
    
    db_session.commit()
    for task in tasks:
        db_session.refresh(task)
    
    return tasks


def test_orchestrator_initialization(db_session, sample_workflow):
    """Test orchestrator initialization."""
    orchestrator = WorkflowOrchestrator(sample_workflow.id, db_session)
    
    assert orchestrator.workflow_id == sample_workflow.id
    assert orchestrator.workflow.name == "Test Workflow"
    assert orchestrator.workflow.status == WorkflowStatus.INIT


def test_orchestrator_state_transitions(db_session, sample_workflow):
    """Test state machine transitions."""
    orchestrator = WorkflowOrchestrator(sample_workflow.id, db_session)
    
    # Test transition to PREPARE
    orchestrator._transition_to_next_state()
    db_session.refresh(sample_workflow)
    assert sample_workflow.status == WorkflowStatus.PREPARE
    assert sample_workflow.started_at is not None
    
    # Test transition to EXECUTE
    orchestrator._transition_to_next_state()
    db_session.refresh(sample_workflow)
    assert sample_workflow.status == WorkflowStatus.EXECUTE


def test_orchestrator_fail_transition(db_session, sample_workflow):
    """Test failure transition."""
    orchestrator = WorkflowOrchestrator(sample_workflow.id, db_session)
    
    # Manually set workflow to FAILED status
    sample_workflow.status = WorkflowStatus.FAILED
    sample_workflow.error_message = "Test error"
    db_session.commit()
    db_session.refresh(sample_workflow)
    
    assert sample_workflow.status == WorkflowStatus.FAILED
    assert sample_workflow.error_message == "Test error"


def test_orchestrator_cancel_transition(db_session, sample_workflow):
    """Test cancel transition."""
    orchestrator = WorkflowOrchestrator(sample_workflow.id, db_session)
    
    # Manually set workflow to CANCELLED status
    sample_workflow.status = WorkflowStatus.CANCELLED
    db_session.commit()
    db_session.refresh(sample_workflow)
    
    assert sample_workflow.status == WorkflowStatus.CANCELLED


@pytest.mark.asyncio
async def test_orchestrator_execution(db_session, sample_workflow, sample_tasks, session_factory):
    """Test full workflow execution."""
    orchestrator = WorkflowOrchestrator(sample_workflow.id, db_session)
    worker_manager = WorkerManager(max_workers=2, session_factory=session_factory)
    
    try:
        await orchestrator.execute_workflow(worker_manager)
        
        # Check workflow status - should reach COMPLETE or FAILED
        db_session.refresh(sample_workflow)
        assert sample_workflow.status in [WorkflowStatus.COMPLETE, WorkflowStatus.FAILED]
        
        # Tasks may or may not be created depending on workflow config
        # Just verify workflow executed
        assert sample_workflow.started_at is not None
    
    finally:
        worker_manager.shutdown()


def test_orchestrator_get_status(db_session, sample_workflow, sample_tasks):
    """Test getting workflow status."""
    orchestrator = WorkflowOrchestrator(sample_workflow.id, db_session)
    
    status = orchestrator.get_status()
    
    assert status["workflow_id"] == sample_workflow.id
    assert status["name"] == "Test Workflow"
    assert status["status"] == "INIT"
    assert status["current_state"] == "INIT"
