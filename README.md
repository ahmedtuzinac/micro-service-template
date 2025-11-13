# Basify - Python Mikroservisni Framework

Enterprise-grade framework za brzo kreiranje mikroservisa sa FastAPI, PostgreSQL i Docker. Centralized authentication, automatski service discovery, inter-service komunikacija i comprehensive testing.

## 🚀 Quick Start

```bash
# 1. Setup konfiguracije  
cp .env.sample .env
# Edit: Set JWT_SECRET_KEY=your-secure-secret-key

# 2. Kreiraj servis (automatski auth-ready)
make create-service NAME=my-service

# 3. Pokreni sa auth sistemom
make up-build

# 4. Test auth workflow
curl http://localhost:8000/health                    # Auth service
curl http://localhost:8001/api/v1/my_service/profile # Demo endpoint
```

## 📋 Komande

```bash
# Service management
make create-service NAME=my-service
make delete-service NAME=my-service  
make list-services

# Docker operations
make up-build              # Build i pokreni sve
make down                  # Zaustavi sve
make logs                  # Prikaži logove

# Testing (nezavisan od servisa)
make test                  # Svi testovi
make test-unit             # Unit testovi
make test-integration      # Integration testovi
```

## 🌐 Inter-Service Komunikacija

```python
# U bilo kom servisu
from fastapi import Depends

def get_service_client():
    from main import app_instance
    return app_instance.service_client

@router.get("/example")
async def endpoint(service_client=Depends(get_service_client)):
    # Pozovi drugi servis
    user_data = await service_client.get("user-service", "/api/v1/123")
    
    # POST zahtev
    result = await service_client.post(
        "order-service", 
        "/api/v1/", 
        json_data={"name": "Order", "user_id": 123}
    )
```

## ⚙️ Konfiguracija

```bash
# .env fajl
POSTGRES_HOST=host.docker.internal
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
DB_PREFIX=basify

# Authentication (IMPORTANT!)
JWT_SECRET_KEY=your-super-secret-jwt-key-CHANGE-THIS
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Service komunikacija  
ENVIRONMENT=docker                     # local ili docker
SERVICE_CLIENT_TIMEOUT=5.0
SERVICE_CLIENT_MAX_RETRIES=3

# Performance
COMPOSE_BAKE=true                      # Brži build-ovi
```

## 🔧 Framework Features

- ✅ **Centralized Authentication** - JWT tokens, RBAC, auto-detection
- ✅ **Protected Routes** - `/protected`, `/admin-only` templates
- ✅ **Automatic Service Discovery** - čita docker-compose.yml
- ✅ **HTTP Service Client** - retry logika, health checks  
- ✅ **Independent Testing** - testovi rade bez pokretanih servisa
- ✅ **Auto Port Detection** - 8000 (auth), 8001, 8002, 8003...
- ✅ **Health Endpoints** - `/health`, `/info`, `/docs`
- ✅ **CORS + Middleware** - error handling, logging

## 📂 Struktura

```
project/
├── basify/                 # Core framework
│   ├── app.py             # BasifyApp klasa
│   ├── clients/           # Service komunikacija + auth_client
│   └── models/            # Base modeli
├── services/              # Mikroservisi
│   ├── auth-service/      # Centralized authentication (port 8000)
│   ├── user-service/      # Example business service
│   └── your-service/      # Auto-generated services  
├── tests/                 # Test suite (nezavisan)
└── docker-compose.yml     # Service definicije sa AUTH_SERVICE_URL
```

## 🔐 Authentication

### Protected Routes
```python
from fastapi import Depends
from basify.auth.dependencies import get_current_user, require_admin

@router.get("/protected")  
async def protected_endpoint(user=Depends(get_current_user)):
    return {"user_id": user.get("user_id"), "username": user.get("username")}

@router.get("/admin-only")
async def admin_endpoint(admin=Depends(require_admin)): 
    return {"message": "Admin access granted!"}
```

### Auth Workflow
```bash
# Register user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","username":"user","password":"SecurePass123!"}'

# Login & get JWT token  
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"SecurePass123!"}'

# Use protected endpoint
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:8001/api/v1/my_service/protected
```

## 🧪 Development

### Custom Model
```python
from basify.models.base import BaseModel
from tortoise import fields

class User(BaseModel):
    name = fields.CharField(max_length=100)
    email = fields.CharField(max_length=200)
    # Auto: id, created_at, updated_at, is_active
```

### Custom Routes
Izmeni `services/my-service/routes/my_service.py` - template već ima auth dependencies!

### Troubleshooting
```bash
# Clean restart
make down && make up-build

# Check logs  
make logs

# Test specific service
make test-unit
```