# MongoDB Migration Guide

This document outlines the migration from PostgreSQL to MongoDB for the FreeWay Community backend.

## Completed Changes

### 1. Dependencies (requirements.txt)
- ✅ Removed: `sqlalchemy`, `alembic`, `psycopg2-binary`, `asyncpg`
- ✅ Added: `motor`, `pymongo`, `beanie`

### 2. Configuration
- ✅ Updated `backend/app/core/config.py` - Removed pool settings, added DATABASE_NAME
- ✅ Updated `backend/.env.example` - Changed DATABASE_URL to MongoDB format

### 3. Database Connection (backend/app/core/database.py)
- ✅ Replaced SQLAlchemy engine with Motor (async MongoDB driver)
- ✅ Added Beanie initialization for ODM support
- ✅ Added connection lifecycle functions

### 4. Models (backend/app/models/)
- ✅ Converted all models from SQLAlchemy to Beanie Documents:
  - `user.py` - User model with indexed fields
  - `vehicle.py` - Vehicle model
  - `request.py` - Request model with validation
  - `device_token.py` - DeviceToken model
  - `report.py` - Report model
  - `audit_log.py` - AuditLog model
- ✅ Replaced Column definitions with Pydantic Field definitions
- ✅ Replaced SQLAlchemy relationships with UUID references
- ✅ Added MongoDB indexes via Settings class
- ✅ Converted enums to string-based enums

### 5. Main Application (backend/main.py)
- ✅ Added MongoDB connection initialization in lifespan
- ✅ Added MongoDB connection cleanup on shutdown

### 6. API Dependencies (backend/app/api/dependencies.py)
- ✅ Removed SQLAlchemy Session dependency
- ✅ Updated get_current_user to use async Beanie queries

### 7. Endpoints
- ✅ `backend/app/api/v1/endpoints/auth.py` - Updated to use async MongoDB queries

### 8. Services
- ✅ `backend/app/services/request_service.py` - Converted to async MongoDB operations

## Remaining Files to Update

The following files still need to be migrated from SQLAlchemy to MongoDB/Beanie:

### API Endpoints
1. `backend/app/api/v1/endpoints/notification.py`
2. `backend/app/api/v1/endpoints/profile.py`
3. `backend/app/api/v1/endpoints/report.py`
4. `backend/app/api/v1/endpoints/request.py`
5. `backend/app/api/v1/endpoints/vehicle.py`

### Services
1. `backend/app/services/audit_service.py`
2. `backend/app/services/device_token_service.py`
3. `backend/app/services/notification_service.py`
4. `backend/app/services/report_service.py`
5. `backend/app/services/request_expiration_service.py`

## Migration Pattern

For each file, follow this pattern:

### 1. Remove SQLAlchemy imports
```python
# Remove:
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from app.core.database import get_db

# Add if needed:
from beanie.operators import And, Or, In, LT, GT
```

### 2. Remove Session parameters
```python
# Before:
async def my_function(db: Session = Depends(get_db)):
    pass

# After:
async def my_function():
    pass
```

### 3. Convert queries
```python
# Before (SQLAlchemy):
user = db.query(User).filter(User.id == user_id).first()
users = db.query(User).filter(User.isActive == True).all()
count = db.query(User).count()

# After (Beanie):
user = await User.find_one(User.id == user_id)
users = await User.find(User.isActive == True).to_list()
count = await User.find(User.isActive == True).count()
```

### 4. Convert complex queries
```python
# Before (SQLAlchemy):
from sqlalchemy import or_
results = db.query(Request).filter(
    or_(Request.requesterId == user_id, Request.targetUserId == user_id)
).all()

# After (Beanie):
from beanie.operators import Or
results = await Request.find(
    Or(Request.requesterId == user_id, Request.targetUserId == user_id)
).to_list()
```

### 5. Convert inserts/updates
```python
# Before (SQLAlchemy):
new_user = User(vehicleNumber="ABC123")
db.add(new_user)
db.commit()
db.refresh(new_user)

# After (Beanie):
new_user = User(vehicleNumber="ABC123")
await new_user.insert()

# Updates:
# Before:
user.isActive = False
db.commit()

# After:
user.isActive = False
await user.save()
```

### 6. Convert deletes
```python
# Before (SQLAlchemy):
db.delete(user)
db.commit()

# After (Beanie):
await user.delete()
```

## Files to Remove

After migration is complete, remove these PostgreSQL-specific files:
- `backend/alembic/` (entire directory)
- `backend/alembic.ini`

## Testing

After migration:
1. Install new dependencies: `pip install -r requirements.txt`
2. Update `.env` file with MongoDB connection string
3. Start MongoDB server
4. Run the application and test all endpoints
5. Verify data operations work correctly

## Schema Preservation

All existing schema structures have been preserved:
- Field names remain unchanged
- Data types are equivalent
- Indexes are maintained
- Validation rules are preserved
- Enum values are identical
