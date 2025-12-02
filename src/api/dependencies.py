from fastapi import Depends
from sqlalchemy.orm import Session

from src.db import get_db
from src.db.dao.workflow_dao import WorkflowDAO
from src.db.dao.task_dao import TaskDAO
from src.db.dao.workflow_transition_dao import WorkflowTransitionDAO

def get_workflow_dao(db: Session = Depends(get_db)) -> WorkflowDAO:
    """Dependency for WorkflowDAO."""
    return WorkflowDAO(db)

def get_task_dao(db: Session = Depends(get_db)) -> TaskDAO:
    """Dependency for TaskDAO."""
    return TaskDAO(db)

def get_workflow_transition_dao(db: Session = Depends(get_db)) -> WorkflowTransitionDAO:
    """Dependency for WorkflowTransitionDAO."""
    return WorkflowTransitionDAO(db)
