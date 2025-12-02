"""Pydantic schemas for API request/response validation."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# Workflow Schemas
class WorkflowCreate(BaseModel):
    """Schema for creating a new workflow."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    config: Optional[Any] = None


class WorkflowUpdate(BaseModel):
    """Schema for updating a workflow."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    config: Optional[Any] = None


class WorkflowResponse(BaseModel):
    """Schema for workflow response."""
    id: int
    name: str
    description: Optional[str]
    status: str
    current_state: str
    retries: int
    config: Optional[Any]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    
    model_config = ConfigDict(from_attributes=True)


# Task Schemas
class TaskCreate(BaseModel):
    """Schema for creating a new task."""
    workflow_id: int
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    task_type: str = Field(..., min_length=1, max_length=100)
    config: Optional[Any] = None


class TaskResponse(BaseModel):
    """Schema for task response."""
    id: int
    workflow_id: int
    name: str
    description: Optional[str]
    status: str
    task_type: str
    config: Optional[Any]
    result: Optional[Any]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    retry_count: int
    
    model_config = ConfigDict(from_attributes=True)


# Workflow Execution Schema
class WorkflowExecutionResponse(BaseModel):
    """Schema for workflow execution status."""
    workflow_id: int
    name: str
    status: str
    started_at: Optional[str]
    completed_at: Optional[str]
    error_message: Optional[str]
    tasks: List[Dict[str, Any]]


# Transition Schema
class TransitionResponse(BaseModel):
    """Schema for workflow transition response."""
    id: int
    workflow_id: int
    from_state: str
    to_state: str
    trigger: Optional[str]
    transition_metadata: Optional[Any]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
