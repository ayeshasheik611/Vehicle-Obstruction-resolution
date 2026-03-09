# Remaining File Migrations

This document lists the remaining files that need to be migrated and provides specific update instructions for each.

## Status Summary

### ✅ Completed
- Core database configuration
- All models (User, Vehicle, Request, DeviceToken, Report, AuditLog)
- Main application (main.py)
- API dependencies
- Auth endpoint
- Request endpoint
- Request service
- Request expiration service
- Removed Alembic (PostgreSQL migrations)

### 🔄 Remaining Files

## 1. backend/app/services/notification_service.py

**Changes needed:**
- Remove `from sqlalchemy.orm import Session`
- Remove `db: Session` parameters from all methods
- Replace `db.query(DeviceToken).filter(...).all()` with `await DeviceToken.find(...).to_list()`
- Replace `db.query(User).filter(...).first()` with `await User.find_one(...)`
- Make all methods async
- Replace audit_service.log_action() calls with direct AuditLog creation and insert

## 2. backend/app/services/device_token_service.py

**Changes needed:**
- Remove SQLAlchemy imports
- Remove `db: Session` parameters
- Replace `db.query(DeviceToken).filter(...).first()` with `await DeviceToken.find_one(...)`
- Replace `db.add()` and `db.commit()` with `await token.insert()`
- Replace `db.delete()` and `db.commit()` with `await token.delete()`
- Make all methods async

## 3. backend/app/services/audit_service.py

**Changes needed:**
- Remove SQLAlchemy imports
- Remove `db: Session` parameters
- Replace `db.add(audit_log)` and `db.commit()` with `await audit_log.insert()`
- Make all methods async
- Update all callers to use async/await

## 4. backend/app/services/report_service.py

**Changes needed:**
- Remove SQLAlchemy imports
- Remove `db: Session` parameters
- Replace all query operations with Beanie equivalents
- Replace `db.query(Report).filter(...).count()` with `await Report.find(...).count()`
- Replace `db.add()` and `db.commit()` with `await report.insert()`
- Update user ban logic to use `await user.save()`
- Make all methods async

## 5. backend/app/api/v1/endpoints/vehicle.py

**Changes needed:**
- Remove `from sqlalchemy.orm import Session`
- Remove `from app.core.database import get_db`
- Remove `db: Session = Depends(get_db)` from all endpoints
- Replace `db.query(Vehicle).filter(...).first()` with `await Vehicle.find_one(...)`
- Replace `db.query(Vehicle).filter(...).all()` with `await Vehicle.find(...).to_list()`
- Replace `db.add()` and `db.commit()` with `await vehicle.insert()`
- Replace audit_service calls with direct AuditLog creation
- Make all endpoints async (they should already be)

## 6. backend/app/api/v1/endpoints/profile.py

**Changes needed:**
- Remove SQLAlchemy imports
- Remove `db: Session` parameter
- Replace `db.query(User).filter(...).first()` with `await User.find_one(...)`
- Replace `db.query(Request).filter(...).count()` with `await Request.find(...).count()`
- Update user modifications to use `await user.save()`
- Make all endpoints async

## 7. backend/app/api/v1/endpoints/report.py

**Changes needed:**
- Remove SQLAlchemy imports
- Remove `db: Session` parameter
- Replace all query operations with Beanie equivalents
- Replace `db.add()` and `db.commit()` with `await report.insert()`
- Update report_service calls to use await
- Make all endpoints async

## 8. backend/app/api/v1/endpoints/notification.py

**Changes needed:**
- Remove SQLAlchemy imports
- Remove `db: Session` parameter
- Replace device_token_service calls to use await
- Make all endpoints async

## Quick Reference: Common Replacements

### Queries
```python
# Before
user = db.query(User).filter(User.id == user_id).first()
users = db.query(User).filter(User.isActive == True).all()
count = db.query(User).count()

# After
user = await User.find_one(User.id == user_id)
users = await User.find(User.isActive == True).to_list()
count = await User.find(User.isActive == True).count()
```

### Complex Filters
```python
# Before
from sqlalchemy import and_, or_
results = db.query(Request).filter(
    and_(
        Request.status == RequestStatus.PENDING,
        or_(Request.requesterId == user_id, Request.targetUserId == user_id)
    )
).all()

# After
from beanie.operators import And, Or
results = await Request.find(
    And(
        Request.status == RequestStatus.PENDING,
        Or(Request.requesterId == user_id, Request.targetUserId == user_id)
    )
).to_list()
```

### Insert
```python
# Before
new_user = User(vehicleNumber="ABC123")
db.add(new_user)
db.commit()
db.refresh(new_user)

# After
new_user = User(vehicleNumber="ABC123")
await new_user.insert()
```

### Update
```python
# Before
user.isActive = False
db.commit()

# After
user.isActive = False
await user.save()
```

### Delete
```python
# Before
db.delete(user)
db.commit()

# After
await user.delete()
```

### Audit Logging
```python
# Before
audit_service.log_action(
    db=db,
    user_id=user_id,
    action=ActionType.USER_LOGIN,
    resource_type="User",
    resource_id=user_id,
    metadata={"key": "value"}
)

# After
audit_log = AuditLog(
    userId=user_id,
    action=ActionType.USER_LOGIN,
    resourceType="User",
    resourceId=str(user_id),
    metadata={"key": "value"}
)
await audit_log.insert()
```

## Testing After Migration

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Update `.env` file:
   ```
   DATABASE_URL=mongodb://localhost:27017/freeway_db
   DATABASE_NAME=freeway_db
   ```

3. Start MongoDB:
   ```bash
   # Using Docker
   docker run -d -p 27017:27017 --name mongodb mongo:latest
   
   # Or install MongoDB locally
   ```

4. Run the application:
   ```bash
   cd backend
   python -m uvicorn main:app --reload
   ```

5. Test endpoints:
   - Register a new user
   - Login
   - Create a request
   - Respond to a request
   - Check request history

## Notes

- All database operations are now async
- No need for session management or transactions
- MongoDB handles connection pooling automatically
- Beanie provides automatic index creation on startup
- UUID fields work seamlessly with MongoDB
- Enum values are stored as strings in MongoDB
