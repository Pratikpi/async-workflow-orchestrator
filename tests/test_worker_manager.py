"""Unit tests for WorkerManager."""
import pytest
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.db import Base, Workflow, Task, WorkflowStatus, TaskStatus
from src.core import WorkerManager


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
def worker_manager(session_factory):
    """Create a worker manager instance."""
    manager = WorkerManager(max_workers=3, session_factory=session_factory)
    yield manager
    manager.shutdown()


@pytest.fixture
def sample_workflow(db_session):
    """Create a sample workflow."""
    workflow = Workflow(
        name="Test Workflow",
        status=WorkflowStatus.INIT
    )
    db_session.add(workflow)
    db_session.commit()
    db_session.refresh(workflow)
    return workflow


@pytest.fixture
def sample_task(db_session, sample_workflow):
    """Create a sample task."""
    task = Task(
        workflow_id=sample_workflow.id,
        name="Test Task",
        task_type="sleep",
        config={"duration": 0.1},
        status=TaskStatus.PENDING
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


def test_worker_manager_initialization(session_factory):
    """Test worker manager initialization."""
    manager = WorkerManager(max_workers=5, session_factory=session_factory)
    
    assert manager.max_workers == 5
    assert manager.get_active_count() == 0
    
    manager.shutdown()


def test_submit_task(worker_manager, db_session, sample_task):
    """Test submitting a task for execution."""
    future = worker_manager.submit_task(sample_task.id, db_session)
    
    assert future is not None
    result = future.result(timeout=5)
    assert result is True
    
    # Verify task was updated
    db_session.refresh(sample_task)
    assert sample_task.status == TaskStatus.COMPLETED


def test_parallel_task_execution(worker_manager, db_session, sample_workflow):
    """Test parallel execution of multiple tasks."""
    # Create multiple tasks
    tasks = []
    for i in range(5):
        task = Task(
            workflow_id=sample_workflow.id,
            name=f"Task {i+1}",
            task_type="sleep",
            config={"duration": 0.2},
            status=TaskStatus.PENDING
        )
        db_session.add(task)
        tasks.append(task)
    
    db_session.commit()
    for task in tasks:
        db_session.refresh(task)
    
    # Submit all tasks
    start_time = time.time()
    futures = [worker_manager.submit_task(task.id, db_session) for task in tasks]
    
    # Wait for completion
    for future in futures:
        future.result(timeout=10)
    
    end_time = time.time()
    
    # Should complete in less time than sequential execution
    # (5 tasks * 0.2s = 1s sequential, but with 3 workers should be ~0.4s)
    assert end_time - start_time < 0.8
    
    # Verify all tasks completed
    for task in tasks:
        db_session.refresh(task)
        assert task.status == TaskStatus.COMPLETED


def test_task_types(worker_manager, db_session, sample_workflow):
    """Test different task types."""
    # Sleep task
    sleep_task = Task(
        workflow_id=sample_workflow.id,
        name="Sleep Task",
        task_type="sleep",
        config={"duration": 0.1},
        status=TaskStatus.PENDING
    )
    db_session.add(sleep_task)
    
    # Compute task
    compute_task = Task(
        workflow_id=sample_workflow.id,
        name="Compute Task",
        task_type="compute",
        config={"iterations": 1000},
        status=TaskStatus.PENDING
    )
    db_session.add(compute_task)
    
    db_session.commit()
    db_session.refresh(sleep_task)
    db_session.refresh(compute_task)
    
    # Execute tasks
    future1 = worker_manager.submit_task(sleep_task.id, db_session)
    future2 = worker_manager.submit_task(compute_task.id, db_session)
    
    assert future1.result(timeout=5) is True
    assert future2.result(timeout=5) is True
    
    # Check results
    db_session.refresh(sleep_task)
    db_session.refresh(compute_task)
    
    assert sleep_task.status == TaskStatus.COMPLETED
    assert compute_task.status == TaskStatus.COMPLETED
    assert compute_task.result is not None


def test_task_failure_handling(worker_manager, db_session, sample_workflow):
    """Test handling of task failures."""
    # Create a task that will fail (invalid task type that raises error)
    from unittest.mock import patch
    
    task = Task(
        workflow_id=sample_workflow.id,
        name="Failing Task",
        task_type="sleep",
        config={"duration": 0.1},
        status=TaskStatus.PENDING
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    
    # Mock the task execution to raise an error
    with patch.object(worker_manager, '_run_task_logic', side_effect=Exception("Test error")):
        future = worker_manager.submit_task(task.id, db_session)
        result = future.result(timeout=5)
    
    assert result is False
    
    db_session.refresh(task)
    assert task.status == TaskStatus.FAILED
    assert "Test error" in task.error_message
