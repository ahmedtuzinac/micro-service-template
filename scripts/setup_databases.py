#!/usr/bin/env python3
"""
Skripta za kreiranje svih potrebnih baza podataka
"""

import asyncio
import sys
import os
from pathlib import Path

# Dodaj project root u Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# PostgreSQL konfiguracija iz environment varijabli
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")

from basify.database import create_database_if_not_exists


async def setup_databases():
    """Kreira sve potrebne baze za postojeće servise"""
    
    # Liste servisa iz services/ direktorijuma
    services_dir = project_root / "services"
    
    if not services_dir.exists():
        print("📂 No services directory found")
        return
    
    services = [d.name for d in services_dir.iterdir() if d.is_dir()]
    
    if not services:
        print("📂 No services found in services/ directory")
        return
    
    print(f"🔍 Found {len(services)} services: {', '.join(services)}")
    print("-" * 50)
    
    success_count = 0
    
    for service_name in services:
        # Generiši database_name na isti način kao u create_service.py
        # Čita iz docker-compose.yml ili koristi default logiku
        
        # Pokušaj da čita iz docker-compose.yml
        docker_compose_path = project_root / "docker-compose.yml"
        db_name = None
        
        if docker_compose_path.exists():
            try:
                import yaml
                with open(docker_compose_path, 'r') as f:
                    compose_data = yaml.safe_load(f)
                    
                service_config = compose_data.get('services', {}).get(service_name, {})
                database_url = service_config.get('environment', {}).get('DATABASE_URL', '')
                
                if database_url:
                    # Extract database name from URL
                    from urllib.parse import urlparse
                    parsed = urlparse(database_url)
                    db_name = parsed.path.lstrip('/')
            except Exception:
                pass
        
        # Fallback na default logiku ako se ne može čitati iz docker-compose.yml
        if not db_name:
            db_name = service_name.replace('-', '_') + '_db'
        
        # Standard database URL format using environment variables
        database_url = f"postgres://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{db_name}"
        
        print(f"🗄️  Creating database for {service_name}...")
        print(f"   Database: {db_name}")
        
        try:
            success = await create_database_if_not_exists(database_url)
            if success:
                success_count += 1
                print(f"   ✅ Success")
            else:
                print(f"   ❌ Failed")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
    
    print("-" * 50)
    print(f"📊 Results: {success_count}/{len(services)} databases created successfully")
    
    if success_count < len(services):
        print("⚠️  Some databases failed to create. Check PostgreSQL connection:")
        print("   - Is PostgreSQL running?")
        print("   - Are credentials correct? (postgres:password)")
        print("   - Is PostgreSQL accessible on localhost:5432?")


async def main():
    print("🏗️  Basify Database Setup")
    print("=" * 50)
    
    try:
        await setup_databases()
    except KeyboardInterrupt:
        print("\n❌ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())