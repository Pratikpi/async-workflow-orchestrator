from typing import List, Optional
from sqlalchemy.orm import Session
from src.db.models import WorkflowTransition

class WorkflowTransitionDAO:
    def __init__(self, db: Session):
        self.db = db

    def create(self, transition: WorkflowTransition) -> WorkflowTransition:
        """Create a new workflow transition record."""
        self.db.add(transition)
        self.db.commit()
        self.db.refresh(transition)
        return transition

    def get_by_workflow_id(self, workflow_id: int) -> List[WorkflowTransition]:
        """Get all transitions for a specific workflow, ordered by creation time."""
        return self.db.query(WorkflowTransition)\
            .filter(WorkflowTransition.workflow_id == workflow_id)\
            .order_by(WorkflowTransition.created_at)\
            .all()
            
    # Note: Transitions are typically immutable history logs, so update/delete 
    # might not be commonly used, but are provided for completeness if needed.

    def get_by_id(self, transition_id: int) -> Optional[WorkflowTransition]:
        """Get a transition by its ID."""
        return self.db.query(WorkflowTransition).filter(WorkflowTransition.id == transition_id).first()

    def delete(self, transition_id: int) -> bool:
        """Delete a transition by ID."""
        transition = self.get_by_id(transition_id)
        if not transition:
            return False
            
        self.db.delete(transition)
        self.db.commit()
        return True
