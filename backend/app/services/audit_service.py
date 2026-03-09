"""
Audit logging service

This module provides functions to create audit log entries for all user actions.

**Validates Requirements**: 21.1, 21.2, 21.3, 21.4, 21.5, 21.6, 21.7, 21.8, 21.9, 21.10

Note: With MongoDB/Beanie, audit logs can be created directly.
This service is maintained for backward compatibility.
"""
from uuid import UUID
from typing import Optional, Dict, Any
from fastapi import Request

from app.models.audit_log import AuditLog, ActionType


class AuditService:
    """Service for creating audit log entries"""
    
    @staticmethod
    async def log_action(
        user_id: Optional[UUID],
        action: ActionType,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Create an audit log entry for a user action.
        
        **Validates Requirements**: 21.9, 21.10
        
        Args:
            user_id: ID of the user performing the action
            action: Type of action being performed
            resource_type: Type of resource being acted upon (e.g., "User", "Request")
            resource_id: ID of the resource being acted upon (as string)
            ip_address: IP address of the client
            user_agent: User agent string of the client
            metadata: Additional metadata as JSON
            
        Returns:
            Created AuditLog instance
        """
        audit_log = AuditLog(
            userId=user_id,
            action=action,
            resourceType=resource_type,
            resourceId=resource_id,
            ipAddress=ip_address,
            userAgent=user_agent,
            metadata=metadata
        )
        
        await audit_log.insert()
        return audit_log


# Service instance
audit_service = AuditService()


# Legacy function for backward compatibility
async def create_audit_log(
    user_id: Optional[UUID],
    action: ActionType,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> AuditLog:
    """Create an audit log entry for a user action."""
    return await audit_service.log_action(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata
    )


async def create_audit_log_from_request(
    request: Request,
    user_id: Optional[UUID],
    action: ActionType,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> AuditLog:
    """
    Create an audit log entry from a FastAPI request object.
    
    This is a convenience function that extracts IP address and user agent
    from the request object.
    
    **Validates Requirements**: 21.9
    """
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    return await audit_service.log_action(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata
    )
