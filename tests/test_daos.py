"""Unit tests for Data Access Objects."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.db import Base, Workflow, Task, WorkflowTransition, WorkflowStatus, TaskStatus
from src.db.dao.workflow_dao import WorkflowDAO
from src.db.dao.task_dao import TaskDAO
from src.db.dao.workflow_transition_dao import WorkflowTransitionDAO


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


class TestWorkflowDAO:
    def test_create_workflow(self, db_session):
        dao = WorkflowDAO(db_session)
        workflow = Workflow(name="Test", status=WorkflowStatus.INIT)
        created = dao.create(workflow)
        
        assert created.id is not None
        assert created.name == "Test"
        assert created.status == WorkflowStatus.INIT

    def test_get_workflow(self, db_session):
        dao = WorkflowDAO(db_session)
        workflow = Workflow(name="Test", status=WorkflowStatus.INIT)
        created = dao.create(workflow)
        
        fetched = dao.get_by_id(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    def test_update_workflow(self, db_session):
        dao = WorkflowDAO(db_session)
        workflow = Workflow(name="Test", status=WorkflowStatus.INIT)
        created = dao.create(workflow)
        
        updated = dao.update(created.id, {"name": "Updated", "status": WorkflowStatus.PREPARE})
        assert updated.name == "Updated"
        assert updated.status == WorkflowStatus.PREPARE
        
        fetched = dao.get_by_id(created.id)
        assert fetched.name == "Updated"

    def test_delete_workflow(self, db_session):
        dao = WorkflowDAO(db_session)
        workflow = Workflow(name="Test", status=WorkflowStatus.INIT)
        created = dao.create(workflow)
        
        assert dao.delete(created.id) is True
        assert dao.get_by_id(created.id) is None

    def test_list_workflows(self, db_session):
        dao = WorkflowDAO(db_session)
        for i in range(5):
            dao.create(Workflow(name=f"Workflow {i}", status=WorkflowStatus.INIT))
            
        workflows = dao.list_workflows(skip=1, limit=2)
        assert len(workflows) == 2
        assert workflows[0].name == "Workflow 1"

    def test_count_workflows(self, db_session):
        dao = WorkflowDAO(db_session)
        dao.create(Workflow(name="W1", status=WorkflowStatus.INIT))
        dao.create(Workflow(name="W2", status=WorkflowStatus.INIT))
        dao.create(Workflow(name="W3", status=WorkflowStatus.COMPLETE))
        
        assert dao.count() == 3
        assert dao.count(WorkflowStatus.INIT) == 2
        assert dao.count(WorkflowStatus.COMPLETE) == 1


class TestTaskDAO:
    def test_create_task(self, db_session):
        # Need a workflow first
        wf_dao = WorkflowDAO(db_session)
        wf = wf_dao.create(Workflow(name="W1", status=WorkflowStatus.INIT))
        
        dao = TaskDAO(db_session)
        task = Task(workflow_id=wf.id, name="T1", status=TaskStatus.PENDING, task_type="sleep")
        created = dao.create(task)
        
        assert created.id is not None
        assert created.workflow_id == wf.id

    def test_get_tasks_by_workflow(self, db_session):
        wf_dao = WorkflowDAO(db_session)
        wf1 = wf_dao.create(Workflow(name="W1", status=WorkflowStatus.INIT))
        wf2 = wf_dao.create(Workflow(name="W2", status=WorkflowStatus.INIT))
        
        dao = TaskDAO(db_session)
        dao.create(Task(workflow_id=wf1.id, name="T1_W1", status=TaskStatus.PENDING, task_type="sleep"))
        dao.create(Task(workflow_id=wf1.id, name="T2_W1", status=TaskStatus.PENDING, task_type="sleep"))
        dao.create(Task(workflow_id=wf2.id, name="T1_W2", status=TaskStatus.PENDING, task_type="sleep"))
        
        tasks_w1 = dao.get_by_workflow_id(wf1.id)
        assert len(tasks_w1) == 2
        
        tasks_w2 = dao.get_by_workflow_id(wf2.id)
        assert len(tasks_w2) == 1

    def test_list_tasks(self, db_session):
        wf_dao = WorkflowDAO(db_session)
        wf = wf_dao.create(Workflow(name="W1", status=WorkflowStatus.INIT))
        
        dao = TaskDAO(db_session)
        for i in range(5):
            dao.create(Task(workflow_id=wf.id, name=f"T{i}", status=TaskStatus.PENDING, task_type="sleep"))
            
        tasks = dao.list_tasks(limit=3)
        assert len(tasks) == 3


class TestWorkflowTransitionDAO:
    def test_create_transition(self, db_session):
        wf_dao = WorkflowDAO(db_session)
        wf = wf_dao.create(Workflow(name="W1", status=WorkflowStatus.INIT))
        
        dao = WorkflowTransitionDAO(db_session)
        transition = WorkflowTransition(
            workflow_id=wf.id,
            from_state="INIT",
            to_state="PREPARE",
            trigger="prepare"
        )
        created = dao.create(transition)
        
        assert created.id is not None
        assert created.workflow_id == wf.id

    def test_get_transitions(self, db_session):
        wf_dao = WorkflowDAO(db_session)
        wf = wf_dao.create(Workflow(name="W1", status=WorkflowStatus.INIT))
        
        dao = WorkflowTransitionDAO(db_session)
        dao.create(WorkflowTransition(workflow_id=wf.id, from_state="A", to_state="B", trigger="t1"))
        dao.create(WorkflowTransition(workflow_id=wf.id, from_state="B", to_state="C", trigger="t2"))
        
        transitions = dao.get_by_workflow_id(wf.id)
        assert len(transitions) == 2
        assert transitions[0].from_state == "A"
        assert transitions[1].from_state == "B"
