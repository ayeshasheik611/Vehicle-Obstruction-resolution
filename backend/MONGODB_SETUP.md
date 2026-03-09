# MongoDB Setup Guide

This guide will help you set up MongoDB and run the migrated application.

## Prerequisites

- Python 3.8+
- MongoDB 4.4+ or Docker

## Option 1: MongoDB with Docker (Recommended)

### 1. Install Docker
Download and install Docker Desktop from https://www.docker.com/products/docker-desktop

### 2. Run MongoDB Container
```bash
docker run -d \
  --name mongodb \
  -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=password \
  -v mongodb_data:/data/db \
  mongo:latest
```

### 3. Update .env File
```env
DATABASE_URL=mongodb://admin:password@localhost:27017/freeway_db?authSource=admin
DATABASE_NAME=freeway_db
```

## Option 2: Local MongoDB Installation

### Windows
1. Download MongoDB Community Server from https://www.mongodb.com/try/download/community
2. Run the installer and follow the setup wizard
3. MongoDB will run as a Windows service automatically

### macOS
```bash
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community
```

### Linux (Ubuntu/Debian)
```bash
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
sudo apt-get update
sudo apt-get install -y mongodb-org
sudo systemctl start mongod
sudo systemctl enable mongod
```

### Update .env File
```env
DATABASE_URL=mongodb://localhost:27017/freeway_db
DATABASE_NAME=freeway_db
```

## Application Setup

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Verify .env Configuration
Make sure your `backend/.env` file has the correct MongoDB connection string:

```env
# MongoDB Configuration
DATABASE_URL=mongodb://localhost:27017/freeway_db
DATABASE_NAME=freeway_db

# Other settings remain the same
SECRET_KEY=your-secret-key-here
REDIS_URL=redis://localhost:6379/0
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json
# ... etc
```

### 3. Run the Application
```bash
cd backend
python -m uvicorn main:app --reload
```

The application will:
- Connect to MongoDB
- Initialize Beanie with all models
- Create indexes automatically
- Start the FastAPI server on http://localhost:8000

### 4. Verify Connection
Check the console output for:
```
MongoDB connected successfully
```

Visit http://localhost:8000/docs to see the API documentation.

## MongoDB Management Tools

### MongoDB Compass (GUI)
Download from https://www.mongodb.com/products/compass

Connection string: `mongodb://localhost:27017`

### MongoDB Shell (CLI)
```bash
# Connect to MongoDB
mongosh

# Switch to database
use freeway_db

# View collections
show collections

# Query users
db.users.find().pretty()

# Query requests
db.requests.find().pretty()

# View indexes
db.users.getIndexes()
```

## Troubleshooting

### Connection Refused
- Ensure MongoDB is running: `docker ps` or `sudo systemctl status mongod`
- Check if port 27017 is available: `netstat -an | grep 27017`
- Verify firewall settings

### Authentication Failed
- Check username/password in connection string
- Ensure `authSource=admin` is included if using authentication
- Verify user has proper permissions

### Indexes Not Created
- Check application logs for Beanie initialization errors
- Manually create indexes if needed:
  ```javascript
  db.users.createIndex({ "vehicleNumber": 1 }, { unique: true })
  db.requests.createIndex({ "requesterId": 1, "createdAt": -1 })
  ```

### Import Existing Data
If you have PostgreSQL data to migrate:

1. Export from PostgreSQL:
```bash
pg_dump -U postgres -d freeway_db -t users --data-only --column-inserts > users.sql
```

2. Convert to MongoDB format (manual process or use migration script)

3. Import to MongoDB:
```bash
mongoimport --db freeway_db --collection users --file users.json
```

## Performance Optimization

### Enable Profiling
```javascript
db.setProfilingLevel(1, { slowms: 100 })
db.system.profile.find().pretty()
```

### Monitor Performance
```javascript
db.currentOp()
db.serverStatus()
```

### Backup Database
```bash
mongodump --db freeway_db --out /backup/$(date +%Y%m%d)
```

### Restore Database
```bash
mongorestore --db freeway_db /backup/20240101/freeway_db
```

## Production Deployment

### MongoDB Atlas (Cloud)
1. Create account at https://www.mongodb.com/cloud/atlas
2. Create a free cluster
3. Get connection string
4. Update .env:
```env
DATABASE_URL=mongodb+srv://username:password@cluster.mongodb.net/freeway_db?retryWrites=true&w=majority
```

### Security Best Practices
- Use strong passwords
- Enable authentication
- Use SSL/TLS connections
- Restrict network access
- Regular backups
- Monitor access logs

## Differences from PostgreSQL

### No Migrations
- MongoDB is schema-less
- No Alembic migrations needed
- Indexes created automatically by Beanie on startup

### Transactions
- MongoDB supports multi-document transactions
- Beanie handles this automatically for most operations
- Single document operations are atomic by default

### Relationships
- No foreign key constraints
- Relationships maintained via UUID references
- Application-level referential integrity

### Queries
- No SQL - uses MongoDB query language
- Beanie provides Pythonic query interface
- Operators: And, Or, In, LT, GT, GTE, etc.

## Support

For issues or questions:
- MongoDB Documentation: https://docs.mongodb.com/
- Beanie Documentation: https://beanie-odm.dev/
- Motor Documentation: https://motor.readthedocs.io/
