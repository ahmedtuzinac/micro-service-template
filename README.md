# Basify - Python Mikroservisni Framework

🚀 **Kompletna platforma za kreiranje Python mikroservisa** sa automatizovanom service-to-service komunikacijom, JWT autentifikacijom, database migracijama i backup sistemom.

## ⚡ Quick Start

### Prerequisites
- **Python 3.8+** 
- **PostgreSQL** (running on localhost:5432)
- **Docker & Docker Compose**

### Setup & First Service
```bash
# 1. Setup environment
cp .env.example .env
# IMPORTANT: Edit JWT_SECRET_KEY in .env!

# 2. Install dependencies
pip install -r requirements.txt
make install-test-deps

# 3. Create service (with auto database creation)
make create-service NAME=my-api

# 4. Build and run
make build && make up

# 5. Your service is ready! 🎉
curl http://localhost:8001/health
```

## 🎯 Key Features

### ✅ **Service Management**
- **One-command service creation** sa database & migrations
- **🆕 Automatic backup system** - backup pre brisanja servisa  
- **Docker integration** sa optimized builds
- **Service discovery** (local/docker environments)

### ✅ **Enterprise Authentication** 
- **JWT tokens** (access/refresh/service-to-service)
- **Role-based access control** (admin/user/custom)
- **Password security** sa bcrypt hashing
- **Automatic auth headers** za inter-service pozive

### ✅ **Database Management**
- **Auto database creation** kada se kreira servis
- **Migration system** sa Aerich (version control)
- **🆕 pg_dump backups** - automatski backup pre delete
- **Schema rollback** capabilities

### ✅ **Developer Experience** 
- **76 passing tests** - comprehensive coverage
- **Hot reload development** 
- **Error handling & logging** middleware
- **Service health checks**

## 📋 Essential Commands

```bash
# Service Management
make create-service NAME=my-service        # Creates service + database
make delete-service NAME=my-service        # Deletes service + backup database
make list-services                         # List all services

# Database Backup Options (NEW!)
python scripts/delete_service.py --name my-service --yes                    # With backup
python scripts/delete_service.py --name my-service --yes --keep-database    # Keep database  
python scripts/delete_service.py --name my-service --yes --no-backup        # No backup

# Docker Operations
make build                 # Build all services
make up                   # Start all services  
make down                 # Stop all services
make logs                 # View logs

# Database Migrations
make migration-status               # Check migration status
make migrate NAME="add_fields"     # Create migration
make upgrade-db                    # Apply migrations

# Testing
make test                 # Run all tests (76 tests)
make test-auth           # Auth system tests
make test-coverage       # Coverage report
```

## 💾 Database Backup System (NEW!)

Basify automatski pravi **PostgreSQL backups** kada brišeš servise:

```bash
# Standard brisanje (sa backup)
make delete-service NAME=my-service
# Backup location: backups/my_service_db_20241119_120000.sql

# Options
--keep-database    # Keep database (for debugging)
--no-backup       # Delete without backup (development only)

# Restore from backup
psql -U postgres -c "CREATE DATABASE restored_db;"
pg_restore -U postgres -d restored_db backups/my_db_20241119_120000.sql
```

## 🔐 Authentication System

### Enable Auth in Service
```python
# services/my-service/main.py
from basify import BasifyApp

app_instance = BasifyApp(
    service_name="my-service",
    enable_auth=True,  # 🔑 Enables JWT auth system
    models_modules=["models"]
)
```

### Protected Routes
```python
from basify.auth import get_current_user, require_role
from fastapi import Depends

@router.get("/profile")
async def get_profile(user=Depends(get_current_user)):
    """Requires authenticated user"""
    return {"user_id": user.id}

@router.delete("/admin-action")  
async def admin_only(admin=Depends(require_role("admin"))):
    """Admin only endpoint"""
    return {"message": "Admin action completed"}
```

### Auth Endpoints (Auto-Available)
- `POST /auth/register` - User registration
- `POST /auth/login` - Login (returns JWT tokens)
- `POST /auth/refresh` - Refresh access token  
- `GET /auth/me` - Current user info

## 🌐 Service Communication

```python
# Inter-service calls with automatic auth
from fastapi import Depends

def get_service_client():
    from main import app_instance
    return app_instance.service_client

@router.get("/data")
async def get_data(service_client=Depends(get_service_client)):
    # ServiceClient automatically adds auth headers
    user_data = await service_client.get("user-service", "/api/users/123")
    return user_data
```

## ⚙️ Configuration (.env)

```bash
# PostgreSQL (Required)
POSTGRES_HOST=host.docker.internal   # or localhost for local dev  
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
DB_PREFIX=basify

# JWT Authentication (IMPORTANT!)
JWT_SECRET_KEY=your-super-secret-jwt-key-CHANGE-IN-PRODUCTION
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15

# Environment
ENVIRONMENT=docker                   # or 'local'
```

## 📂 Project Structure

```
basify/
├── basify/                    # Core framework
│   ├── app.py                # BasifyApp main class
│   ├── database.py           # Database & backup management  
│   ├── clients/              # Service communication
│   └── auth/                 # JWT authentication
├── services/                 # Your microservices
│   ├── auth-service/         # Central auth (port 8000)  
│   └── your-service/         # Auto-generated services
├── scripts/                  # Management scripts
├── templates/                # Service templates
├── backups/                  # Database backups
├── tests/                    # Test suite (76 tests)
└── docker-compose.yml        # Multi-service setup
```

## 🧪 Development

### Create Custom Models
```python
from basify.models.base import BaseModel
from tortoise import fields

class Product(BaseModel):
    name = fields.CharField(max_length=100)
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    # Auto includes: id, created_at, updated_at, is_active
```

### Test Your Service Locally  
```bash
# Run service in dev mode
cd services/my-service
uvicorn main:app --reload --port 8001

# Test endpoints
curl http://localhost:8001/health
curl http://localhost:8001/api/my-resource
```

### Database Schema Changes
```bash
# 1. Edit models.py in your service
# 2. Create migration
make migrate-service SERVICE=my-service NAME="add_new_field"
# 3. Apply migration
make upgrade-service-db SERVICE=my-service
```

## 🚀 Production Ready

### What's Included
- **76 passing tests** - comprehensive coverage
- **PostgreSQL backup system** - automatic pg_dump with restore
- **JWT security** - enterprise-grade authentication
- **Database migrations** - Aerich-powered schema management  
- **Docker optimization** - bake builds for performance
- **Error handling** - comprehensive middleware
- **Service discovery** - local & docker environments

### Production Checklist
- [ ] **Configure JWT_SECRET_KEY** in production environment
- [ ] **Setup external PostgreSQL** (AWS RDS, Google Cloud SQL, etc.)
- [ ] **Configure monitoring** (health checks, metrics)
- [ ] **Setup CI/CD pipeline** with automated testing
- [ ] **Configure load balancer** for service discovery

## 🛠️ Advanced Usage

### Custom Service Templates
```bash
# Copy existing template  
cp -r templates/service_template templates/my_custom_template
# Edit files with {{PLACEHOLDERS}} and use in create_service.py
```

### Backup Management
```bash
# List all backups
ls -la backups/

# Restore specific backup
pg_restore -U postgres -d my_restored_db backups/service_db_20241119_120000.sql

# Cleanup old backups (manual)
find backups/ -name "*.sql" -mtime +30 -delete  # Remove 30+ day old backups
```

---

**Basify** - Build enterprise microservices in minutes! 🚀

📚 **For detailed technical documentation**, see [CLAUDE.md](CLAUDE.md)