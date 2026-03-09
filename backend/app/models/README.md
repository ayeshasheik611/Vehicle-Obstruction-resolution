# Database Models

This directory contains all SQLAlchemy database models for the FreeWay Community application.

## Models Overview

### User Model (`user.py`)
Represents registered vehicle owners in the system.

**Fields:**
- `id`: UUID primary key
- `vehicleNumber`: Unique vehicle number (indexed)
- `passwordHash`: Bcrypt hashed password
- `fcmToken`: Firebase Cloud Messaging token for push notifications
- `isActive`: Account active status
- `isBanned`: Account banned status
- `createdAt`: Registration timestamp
- `lastLoginAt`: Last login timestamp
- `requestCount`: Counter for rate limiting
- `reportCount`: Counter for abuse tracking

**Relationships:**
- `vehicles`: One-to-many with Vehicle
- `sent_requests`: One-to-many with Request (as requester)
- `received_requests`: One-to-many with Request (as target)
- `device_tokens`: One-to-many with DeviceToken
- `reports_made`: One-to-many with Report (as reporter)
- `reports_received`: One-to-many with Report (as target)
- `audit_logs`: One-to-many with AuditLog

**Validates Requirements:** 1.6, 22.6, 24.1

---

### Vehicle Model (`vehicle.py`)
Represents vehicles registered by users.

**Fields:**
- `id`: UUID primary key
- `userId`: Foreign key to User (indexed)
- `vehicleNumber`: Unique vehicle number (indexed)
- `isActive`: Vehicle active status
- `registeredAt`: Registration timestamp
- `lastIdentifiedAt`: Last time vehicle was identified

**Relationships:**
- `owner`: Many-to-one with User

**Validates Requirements:** 22.4, 22.5

---

### Request Model (`request.py`)
Represents call requests between users.

**Fields:**
- `id`: UUID primary key
- `requesterId`: Foreign key to User (indexed)
- `targetUserId`: Foreign key to User (indexed)
- `targetVehicle`: Vehicle number being requested
- `status`: Request status (PENDING, RESPONDED, RESOLVED, EXPIRED, CANCELLED) (indexed)
- `createdAt`: Request creation timestamp (indexed)
- `respondedAt`: Response timestamp
- `expiresAt`: Expiration timestamp
- `response`: Response type (MESSAGE, ON_MY_WAY, CANNOT_MOVE)
- `responseMessage`: Optional response message

**Relationships:**
- `requester`: Many-to-one with User
- `target_user`: Many-to-one with User

**Constraints:**
- Check constraint: `requesterId != targetUserId`
- Composite index: `(requesterId, createdAt)` for rate limiting

**Validates Requirements:** 22.1, 22.2, 22.3, 24.2, 24.3, 24.4, 24.5, 24.6

---

### DeviceToken Model (`device_token.py`)
Manages FCM tokens for push notifications.

**Fields:**
- `id`: UUID primary key
- `userId`: Foreign key to User (indexed)
- `fcmToken`: Unique FCM token
- `platform`: Device platform (IOS, ANDROID)
- `isActive`: Token active status
- `createdAt`: Token creation timestamp
- `lastUsedAt`: Last successful notification timestamp

**Relationships:**
- `user`: Many-to-one with User

**Validates Requirements:** 22.7, 24.7

---

### Report Model (`report.py`)
Tracks abuse reports between users.

**Fields:**
- `id`: UUID primary key
- `reporterId`: Foreign key to User (indexed)
- `targetUserId`: Foreign key to User (indexed)
- `reason`: Report reason (SPAM, HARASSMENT, FALSE_REQUEST, ABUSE, OTHER)
- `description`: Optional description
- `status`: Report status (PENDING, UNDER_REVIEW, RESOLVED, DISMISSED) (indexed)
- `createdAt`: Report creation timestamp (indexed)
- `reviewedAt`: Review timestamp
- `reviewedBy`: Admin user ID who reviewed
- `action`: Admin action taken (WARNING, TEMPORARY_BAN, PERMANENT_BAN, NO_ACTION)

**Relationships:**
- `reporter`: Many-to-one with User
- `target_user`: Many-to-one with User

---

### AuditLog Model (`audit_log.py`)
Tracks all user actions for security and debugging.

**Fields:**
- `id`: UUID primary key
- `userId`: Foreign key to User (indexed, nullable)
- `action`: Action type (USER_REGISTER, USER_LOGIN, VEHICLE_IDENTIFY, etc.)
- `resourceType`: Type of resource affected
- `resourceId`: UUID of affected resource
- `ipAddress`: Client IP address
- `userAgent`: Client user agent
- `timestamp`: Action timestamp (indexed)
- `metadata`: Additional JSON metadata

**Relationships:**
- `user`: Many-to-one with User

**Validates Requirements:** 24.8, 24.9

---

## Database Indexes

The following indexes are created for optimal query performance:

1. **users.vehicleNumber** - Fast vehicle lookups (Req 24.1)
2. **requests.requesterId** - Request history queries (Req 24.2)
3. **requests.targetUserId** - Request history queries (Req 24.3)
4. **requests.status** - Filtering by status (Req 24.4)
5. **requests.createdAt** - Expiration job queries (Req 24.5)
6. **requests(requesterId, createdAt)** - Rate limiting queries (Req 24.6)
7. **device_tokens.userId** - Token retrieval (Req 24.7)
8. **audit_logs.userId** - User action queries (Req 24.8)
9. **audit_logs.timestamp** - Time-based queries (Req 24.9)

---

## Migrations

Database migrations are managed using Alembic. The initial schema migration is located at:
`backend/alembic/versions/001_create_initial_schema.py`

To apply migrations:
```bash
cd backend
alembic upgrade head
```

To create a new migration:
```bash
alembic revision --autogenerate -m "Description of changes"
```

---

## Usage Example

```python
from app.models import User, Vehicle, Request
from app.core.database import SessionLocal
import uuid
from datetime import datetime, timedelta

# Create a database session
db = SessionLocal()

# Create a new user
user = User(
    id=uuid.uuid4(),
    vehicleNumber="MH12AB1234",
    passwordHash="hashed_password_here",
    isActive=True,
    createdAt=datetime.utcnow()
)
db.add(user)
db.commit()

# Create a vehicle
vehicle = Vehicle(
    id=uuid.uuid4(),
    userId=user.id,
    vehicleNumber="MH12AB1234",
    registeredAt=datetime.utcnow()
)
db.add(vehicle)
db.commit()

# Query users
user = db.query(User).filter(User.vehicleNumber == "MH12AB1234").first()

# Close session
db.close()
```
