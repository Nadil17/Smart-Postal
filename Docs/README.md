# Voice and Fingerprint Verification System - Backend

## Setup

### 1. Install Dependencies
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `config/.env` and update the values:
```bash
cp config/.env.example config/.env
```

### 3. Setup Database
```bash
# Create database (PostgreSQL)
createdb delivery_system

# Run migrations
alembic upgrade head
```

### 4. Run the Server
```bash
python run.py
```

The API will be available at: http://localhost:8000

## API Documentation

Interactive API documentation: http://localhost:8000/docs

## Testing
```bash
pytest tests/ -v
```

## Project Structure

```
backend/
├── main.py                 # FastAPI application entry point
├── run.py                  # Server runner
├── requirements.txt        # Python dependencies
├── alembic.ini            # Database migration config
├── alembic/               # Database migrations
│   └── env.py
├── config/
│   ├── settings.py        # Configuration management
│   └── .env               # Environment variables
├── models/
│   ├── database.py        # Database setup
│   ├── user.py            # User model
│   ├── order.py           # Order model
│   └── biometric.py       # Biometric models
├── api/
│   ├── middleware/
│   │   └── auth.py        # Authentication middleware
│   ├── routes/
│   │   ├── auth.py        # Authentication endpoints
│   │   ├── users.py       # User endpoints
│   │   ├── orders.py      # Order endpoints
│   │   └── biometric.py   # Biometric endpoints
│   └── schemas/
│       ├── user.py        # User schemas
│       ├── order.py       # Order schemas
│       └── biometric.py   # Biometric schemas
├── services/
│   ├── voice_auth/        # Voice authentication service
│   ├── fingerprint_auth/  # Fingerprint authentication service
│   ├── ai_detection/      # AI detection service
│   └── delivery/          # Delivery service
├── utils/
│   └── security.py        # Security utilities
└── tests/
    ├── conftest.py        # Test configuration
    ├── test_auth.py       # Authentication tests
    └── test_orders.py     # Order tests
```

## Environment Variables

See `config/.env` for all available configuration options.

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user
- `POST /api/auth/refresh` - Refresh token

### Users
- `GET /api/users/profile` - Get user profile
- `PUT /api/users/profile` - Update user profile
- `POST /api/users/enroll-voice` - Enroll voice samples
- `POST /api/users/enroll-fingerprint` - Enroll fingerprint

### Orders
- `POST /api/orders/` - Create order
- `GET /api/orders/` - List orders
- `GET /api/orders/{id}` - Get order details
- `PUT /api/orders/{id}` - Update order
- `GET /api/orders/{id}/biometric-status` - Get biometric verification status

### Biometric Verification
- `POST /api/biometric/verify-voice` - Verify voice
- `POST /api/biometric/verify-fingerprint` - Verify fingerprint
- `GET /api/biometric/verification-history` - Get verification history
