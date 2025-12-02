from typing import List, Optional, Any, Dict
from sqlalchemy.orm import Session
from src.db.models import Workflow, WorkflowStatus

class WorkflowDAO:
    def __init__(self, db: Session):
        self.db = db

    def create(self, workflow: Workflow) -> Workflow:
        """Create a new workflow."""
        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(workflow)
        return workflow

    def get_by_id(self, workflow_id: int) -> Optional[Workflow]:
        """Get a workflow by its ID."""
        return self.db.query(Workflow).filter(Workflow.id == workflow_id).first()

    def list(self, skip: int = 0, limit: int = 100) -> List[Workflow]:
        """List workflows with pagination."""
        return self.db.query(Workflow).offset(skip).limit(limit).all()

    def update(self, workflow_id: int, update_data: Dict[str, Any]) -> Optional[Workflow]:
        """
        Update a workflow.
        
        Args:
            workflow_id: The ID of the workflow to update.
            update_data: A dictionary of attributes to update.
        """
        workflow = self.get_by_id(workflow_id)
        if not workflow:
            return None
            
        for key, value in update_data.items():
            if hasattr(workflow, key):
                setattr(workflow, key, value)
        
        self.db.commit()
        self.db.refresh(workflow)
        return workflow

    def delete(self, workflow_id: int) -> bool:
        """Delete a workflow by ID."""
        workflow = self.get_by_id(workflow_id)
        if not workflow:
            return False
            
        self.db.delete(workflow)
        self.db.commit()
        return True
