"""
Audit logging service

This module provides functions to create audit log entries for all user actions.

**Validates Requirements**: 21.1, 21.2, 21.3, 21.4, 21.5, 21.6, 21.7, 21.8, 21.9, 21.10
"""
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional, Dict, Any
from fastapi import Request

from app.models.audit_log import AuditLog, ActionType


class AuditService:
    """Service for creating audit log entries"""
    
    @staticmethod
    def log_action(
        db: Session,
        user_id: Optional[UUID],
        action: ActionType,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Create an audit log entry for a user action.
        
        **Validates Requirements**: 21.9, 21.10
        
        Args:
            db: Database session
            user_id: ID of the user performing the action
            action: Type of action being performed
            resource_type: Type of resource being acted upon (e.g., "User", "Request")
            resource_id: ID of the resource being acted upon
            ip_address: IP address of the client
            user_agent: User agent string of the client
            metadata: Additional metadata as JSON
            
        Returns:
            Created AuditLog instance
            
        Example:
            >>> log = audit_service.log_action(
            ...     db=db,
            ...     user_id=user.id,
            ...     action=ActionType.USER_REGISTER,
            ...     resource_type="User",
            ...     resource_id=user.id,
            ...     ip_address="192.168.1.1"
            ... )
        """
        audit_log = AuditLog(
            userId=user_id,
            action=action,
            resourceType=resource_type,
            resourceId=resource_id,
            ipAddress=ip_address,
            userAgent=user_agent,
            extra_data=metadata
        )
        
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)
        
        return audit_log


# Service instance
audit_service = AuditService()


# Legacy function for backward compatibility
def create_audit_log(
    db: Session,
    user_id: Optional[UUID],
    action: ActionType,
    resource_type: Optional[str] = None,
    resource_id: Optional[UUID] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> AuditLog:
    """
    Create an audit log entry for a user action.
    
    **Validates Requirements**: 21.9, 21.10
    
    Args:
        db: Database session
        user_id: ID of the user performing the action
        action: Type of action being performed
        resource_type: Type of resource being acted upon (e.g., "User", "Request")
        resource_id: ID of the resource being acted upon
        ip_address: IP address of the client
        user_agent: User agent string of the client
        metadata: Additional metadata as JSON
        
    Returns:
        Created AuditLog instance
        
    Example:
        >>> log = create_audit_log(
        ...     db=db,
        ...     user_id=user.id,
        ...     action=ActionType.USER_REGISTER,
        ...     resource_type="User",
        ...     resource_id=user.id,
        ...     ip_address="192.168.1.1"
        ... )
    """
    return audit_service.log_action(
        db=db,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata
    )


def create_audit_log_from_request(
    db: Session,
    request: Request,
    user_id: Optional[UUID],
    action: ActionType,
    resource_type: Optional[str] = None,
    resource_id: Optional[UUID] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> AuditLog:
    """
    Create an audit log entry from a FastAPI request object.
    
    This is a convenience function that extracts IP address and user agent
    from the request object.
    
    **Validates Requirements**: 21.9
    
    Args:
        db: Database session
        request: FastAPI request object
        user_id: ID of the user performing the action
        action: Type of action being performed
        resource_type: Type of resource being acted upon
        resource_id: ID of the resource being acted upon
        metadata: Additional metadata as JSON
        
    Returns:
        Created AuditLog instance
    """
    # Extract IP address from request
    ip_address = request.client.host if request.client else None
    
    # Extract user agent from headers
    user_agent = request.headers.get("user-agent")
    
    return audit_service.log_action(
        db=db,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata
    )
