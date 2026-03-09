# FreeWay Community

A privacy-focused mobile application that resolves vehicle blocking issues through automated license plate recognition and notification-based communication.

## 🎯 Overview

FreeWay Community enables users to identify blocking vehicles via image capture or manual entry, then sends call requests to vehicle owners without exposing personal contact information. Built with React Native frontend and Python FastAPI backend, the application integrates ALPR technology for automatic vehicle number extraction and Firebase Cloud Messaging for real-time notifications.

## ✨ Features

### Core Functionality
- 🔐 **Secure Authentication** - JWT-based user registration and login
- 📸 **Vehicle Identification** - Camera capture with ALPR or manual entry
- 📱 **Call Requests** - Send notification-based requests to vehicle owners
- 🔔 **Push Notifications** - Real-time Firebase Cloud Messaging
- 📊 **Request History** - Track sent and received requests with pagination
- 🚫 **Abuse Reporting** - Report spam and harassment with automatic detection
- ⏱️ **Rate Limiting** - 10 requests/hour, 50 requests/day per user
- 🔒 **Privacy First** - Vehicle number masking, no phone number sharing

### Technical Features
- 🖼️ **Image Preprocessing** - Automatic resize, grayscale, contrast enhancement
- 🤖 **ALPR Integration** - OpenALPR for license plate recognition
- ⚡ **Redis Caching** - Fast rate limiting and session management
- 📝 **Audit Logging** - Complete action tracking for security
- ⏰ **Auto-Expiration** - Requests expire after 30 minutes
- 🔄 **Request Lifecycle** - PENDING → RESPONDED/EXPIRED states

## 🏗️ Architecture

```
┌─────────────────┐
│  React Native   │
│   Mobile App    │
└────────┬────────┘
         │ HTTPS/REST API
         ▼
┌─────────────────┐      ┌──────────────┐
│   FastAPI       │─────▶│  PostgreSQL  │
│   Backend       │      │   Database   │
└────────┬────────┘      └──────────────┘
         │
         ├─────▶ Redis (Rate Limiting)
         ├─────▶ OpenALPR (Plate Recognition)
         └─────▶ Firebase (Push Notifications)
```

## 📋 Prerequisites

- **Python** 3.9+
- **Node.js** 18+
- **PostgreSQL** 13+
- **Redis** 6+
- **Android Studio** (for Android) or **Xcode** (for iOS)
- **OpenALPR** (optional, for real plate recognition)

## 🚀 Quick Start

### Option 1: Using Quick Start Script

**Linux/Mac:**
```bash
chmod +x quick-start.sh
./quick-start.sh
```

**Windows:**
```bash
quick-start.bat
```

### Option 2: Manual Setup

#### Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Run migrations
alembic upgrade head

# Start server
uvicorn main:app --reload
```

#### Mobile App Setup

```bash
# Navigate to mobile
cd mobile

# Install dependencies
npm install

# iOS only (Mac)
cd ios && pod install && cd ..

# Start Metro bundler
npm start

# Run on Android (in another terminal)
npm run android

# Run on iOS (in another terminal, Mac only)
npm run ios
```

## 📖 Documentation

- **[Complete Testing Guide](COMPLETE_TESTING_GUIDE.md)** - Step-by-step testing instructions
- **[ALPR Setup Guide](backend/ALPR_SETUP.md)** - OpenALPR installation and configuration
- **[ALPR Implementation Status](ALPR_IMPLEMENTATION_STATUS.md)** - Current ALPR status
- **[Testing Without Firebase](mobile/TESTING_WITHOUT_FIREBASE.md)** - Test without push notifications
- **[Design Document](.kiro/specs/freeway-community/design.md)** - System architecture and workflows
- **[Requirements](.kiro/specs/freeway-community/requirements.md)** - Detailed requirements
- **[Tasks](.kiro/specs/freeway-community/tasks.md)** - Implementation tasks

## 🧪 Testing

### Quick Test

1. **Start Backend:**
   ```bash
   cd backend
   source venv/bin/activate
   uvicorn main:app --reload
   ```

2. **Start Mobile App:**
   ```bash
   cd mobile
   npm start
   npm run android  # or npm run ios
   ```

3. **Test Flow:**
   - Register User A with vehicle MH12AB1234
   - Register User B with vehicle MH12CD5678
   - Login as User A
   - Identify vehicle MH12CD5678
   - Send call request
   - Login as User B
   - View and respond to request

### Run Tests

```bash
# Backend tests
cd backend
pytest

# Mobile tests
cd mobile
npm test
```

## 🔧 Configuration

### Backend (.env)

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/freeway_community

# Redis
REDIS_URL=redis://localhost:6379

# JWT
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_DAYS=7

# Firebase (optional)
FIREBASE_CREDENTIALS_PATH=path/to/firebase-credentials.json
```

### Mobile (src/services/api.ts)

```typescript
// For local testing
const API_BASE_URL = 'http://localhost:8000/api';

// For device testing (use your computer's IP)
const API_BASE_URL = 'http://192.168.1.100:8000/api';
```

## 📱 Mobile App Features

### Screens Implemented
- ✅ Login Screen
- ✅ Registration Screen
- ✅ Home Screen
- ✅ Vehicle Identification Screen
- ✅ Manual Vehicle Entry Screen
- ✅ Call Request Screen
- ✅ Request Status Screen
- ✅ Request History Screen
- ✅ Request Response Screen
- ✅ Report User Screen
- ✅ Profile/Settings Screen

### Services Implemented
- ✅ API Service (Axios with interceptors)
- ✅ Storage Service (Secure keychain)
- ✅ Notification Service (Firebase Cloud Messaging)
- ✅ Navigation Service (React Navigation)
- ✅ Authentication Context (JWT management)

## 🔐 Security Features

- **JWT Authentication** - Secure token-based auth with 7-day expiration
- **Password Hashing** - bcrypt with 10 salt rounds
- **Rate Limiting** - Redis-based distributed rate limiting
- **Vehicle Masking** - Privacy-focused number masking (MH****1234)
- **Image Deletion** - Immediate deletion after ALPR processing
- **Audit Logging** - Complete action tracking
- **Input Validation** - Comprehensive request validation
- **HTTPS Only** - Secure communication (production)

## 📊 API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login

### Vehicle
- `POST /api/vehicle/identify` - Identify vehicle (image or manual)

### Requests
- `POST /api/request/create` - Create call request
- `POST /api/request/respond` - Respond to request
- `GET /api/request/history` - Get request history

### Notifications
- `POST /api/notification/register` - Register FCM device token

### Reports
- `POST /api/report/create` - Report user abuse

## 🐛 Troubleshooting

### Backend Issues

**Database connection error:**
```bash
# Check PostgreSQL is running
sudo service postgresql status

# Test connection
psql -U user -d freeway_community
```

**Redis connection error:**
```bash
# Check Redis is running
redis-cli ping  # Should return PONG
```

### Mobile App Issues

**Cannot connect to backend:**
- Use your computer's IP address, not `localhost` for physical devices
- Check firewall allows port 8000
- Verify backend is running: `curl http://localhost:8000/health`

**Build errors:**
```bash
# Clear cache
npm start -- --reset-cache

# Clean build
cd android && ./gradlew clean && cd ..
npm run android
```

## 🚀 Production Deployment

### Backend

1. **Set up production database**
2. **Configure environment variables**
3. **Install OpenALPR**
4. **Set up Firebase**
5. **Deploy with Docker:**
   ```bash
   docker-compose up -d
   ```

### Mobile App

1. **Add Firebase config files:**
   - `mobile/android/app/google-services.json`
   - `mobile/ios/FreewayCommunity/GoogleService-Info.plist`

2. **Update API URL** to production server

3. **Build release:**
   ```bash
   # Android
   cd android
   ./gradlew assembleRelease
   
   # iOS
   # Open in Xcode and archive
   ```

## 📈 Performance

- **API Response Time:** <200ms (p95)
- **ALPR Processing:** 1-3 seconds per image
- **Database Queries:** <100ms (p95)
- **Rate Limits:** 10/hour, 50/day per user
- **Request Expiration:** 30 minutes

## 🤝 Contributing

This is a final year project. For questions or issues, please refer to the documentation.

## 📄 License

This project is part of a final year academic project.

## 🙏 Acknowledgments

- **OpenALPR** - License plate recognition
- **Firebase** - Push notifications
- **FastAPI** - Backend framework
- **React Native** - Mobile framework
- **PostgreSQL** - Database
- **Redis** - Caching and rate limiting

## 📞 Support

For detailed instructions, see:
- [Complete Testing Guide](COMPLETE_TESTING_GUIDE.md)
- [ALPR Setup Guide](backend/ALPR_SETUP.md)
- [Design Document](.kiro/specs/freeway-community/design.md)

---

**Built with ❤️ for solving real-world parking problems**
