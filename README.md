# Basify - Python Mikroservisni Framework

Framework za brzo kreiranje mikroservisa sa FastAPI, PostgreSQL i Docker. Automatski service discovery, inter-service komunikacija i nezavisni testovi.

## 🚀 Quick Start

```bash
# 1. Setup konfiguracije  
cp .env.sample .env

# 2. Kreiraj servis
make create-service NAME=user-service

# 3. Pokreni
make up-build

# 4. Testiranje
curl http://localhost:8001/health
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

# Service komunikacija
ENVIRONMENT=docker                     # local ili docker
SERVICE_CLIENT_TIMEOUT=5.0
SERVICE_CLIENT_MAX_RETRIES=3

# Performance
COMPOSE_BAKE=true                      # Brži build-ovi
```

## 🔧 Framework Features

- ✅ **Automatic Service Discovery** - čita docker-compose.yml
- ✅ **HTTP Service Client** - retry logika, health checks  
- ✅ **Independent Testing** - testovi rade bez pokretanih servisa
- ✅ **Auto Port Detection** - 8001, 8002, 8003...
- ✅ **Health Endpoints** - `/health`, `/info`, `/docs`
- ✅ **CORS + Middleware** - error handling, logging

## 📂 Struktura

```
project/
├── basify/                 # Core framework
│   ├── app.py             # BasifyApp klasa
│   ├── clients/           # Service komunikacija
│   └── models/            # Base modeli
├── services/              # Tvoji mikroservisi
├── tests/                 # Test suite (nezavisan)
└── docker-compose.yml     # Service definicije
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
Izmeni `services/my-service/routes/my_service.py`

### Troubleshooting
```bash
# Clean restart
make down && make up-build

# Check logs  
make logs

# Test specific service
make test-unit
```