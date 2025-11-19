from tortoise import Tortoise
from tortoise.contrib.fastapi import register_tortoise
from typing import List, Optional
import logging
import asyncio
import asyncpg
import os
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# PostgreSQL default configuration from environment
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")


async def create_database_if_not_exists(database_url: str) -> bool:
    """
    Kreira bazu podataka ako ne postoji
    Returns True ako je baza kreirana ili već postojala
    """
    try:
        # Parse database URL
        parsed = urlparse(database_url)
        database_name = parsed.path.lstrip('/')
        
        # Kreiraj URL za konekciju na postgres bazu (bez specifične baze)
        postgres_url = f"{parsed.scheme}://{parsed.netloc}/postgres"
        
        # Konektuj se na postgres bazu
        conn = await asyncpg.connect(postgres_url)
        
        try:
            # Proveravamo da li baza postoji
            result = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1",
                database_name
            )
            
            if result:
                logger.info(f"Database '{database_name}' already exists")
                return True
            
            # Kreiraj bazu
            await conn.execute(f'CREATE DATABASE "{database_name}"')
            logger.info(f"Database '{database_name}' created successfully")
            return True
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Failed to create database: {e}")
        logger.error(f"Database URL: {database_url}")
        logger.error("Make sure PostgreSQL is running and credentials are correct")
        return False


async def init_db(
    database_url: str,
    models_modules: List[str],
    generate_schemas: bool = True,
    create_database: bool = False
):
    """
    Inicijalizuje Tortoise ORM sa PostgreSQL bazom
    create_database: ako je True, pokušava da kreira bazu (deprecated - koristiti create_service.py)
    """
    try:
        # Kreiranje baze je sada opciono i deprecated
        if create_database:
            logger.warning("create_database=True is deprecated. Use create_service.py script instead.")
            logger.info("Checking if database exists...")
            database_created = await create_database_if_not_exists(database_url)
            
            if not database_created:
                raise Exception("Could not create or access database")
        
        # Inicijalizuj Tortoise ORM
        logger.info("Initializing Tortoise ORM...")
        await Tortoise.init(
            db_url=database_url,
            modules={"models": models_modules}
        )
        
        if generate_schemas:
            logger.info("Generating database schemas...")
            await Tortoise.generate_schemas()
            
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


async def close_db():
    """
    Zatvara konekciju sa bazom
    """
    try:
        await Tortoise.close_connections()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")


def get_database_config(
    database_url: str,
    models_modules: List[str],
    app_name: str = "basify"
) -> dict:
    """
    Vraća konfiguraciju za Tortoise ORM
    """
    return {
        "connections": {
            "default": database_url
        },
        "apps": {
            app_name: {
                "models": models_modules,
                "default_connection": "default",
            }
        }
    }


async def backup_database(database_url: str, backup_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Kreira backup PostgreSQL baze koristeći pg_dump
    Returns path do backup fajla ili None ako backup nije uspeo
    """
    try:
        # Parse database URL
        parsed = urlparse(database_url)
        database_name = parsed.path.lstrip('/')
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        username = parsed.username or "postgres"
        password = parsed.password or ""
        
        # Kreiraj backup direktorij
        if backup_dir is None:
            project_root = Path.cwd()
            backup_dir = project_root / "backups"
        
        backup_dir.mkdir(exist_ok=True)
        
        # Generiši timestamp za backup fajl
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{database_name}_{timestamp}.sql"
        backup_path = backup_dir / backup_filename
        
        logger.info(f"Creating backup for database '{database_name}'...")
        
        # Pripremi pg_dump komandu
        cmd = [
            "pg_dump",
            "-h", host,
            "-p", str(port),
            "-U", username,
            "-d", database_name,
            "--no-password",  # Koristi PGPASSWORD environment varijablu
            "--verbose",
            "--format=custom",  # Binary format za brže restore
            "-f", str(backup_path)
        ]
        
        # Pokreni pg_dump sa PGPASSWORD environment varijablom
        env = os.environ.copy()
        if password:
            env["PGPASSWORD"] = password
        
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5 minuta timeout
        )
        
        if result.returncode == 0:
            logger.info(f"Database backup created successfully: {backup_path}")
            return backup_path
        else:
            logger.error(f"pg_dump failed: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        logger.error("Database backup timeout (5 minutes)")
        return None
    except Exception as e:
        logger.error(f"Failed to create database backup: {e}")
        return None


async def drop_database(database_url: str, backup_first: bool = True) -> bool:
    """
    Briše PostgreSQL bazu
    backup_first: ako je True, pravi backup pre brisanja
    Returns True ako je brisanje uspešno
    """
    try:
        # Parse database URL
        parsed = urlparse(database_url)
        database_name = parsed.path.lstrip('/')
        
        # Pravi backup ako je potrebno
        backup_path = None
        if backup_first:
            backup_path = await backup_database(database_url)
            if backup_path is None:
                logger.warning(f"Backup failed, but continuing with database drop for '{database_name}'")
            else:
                logger.info(f"Backup created: {backup_path}")
        
        # Kreiraj URL za konekciju na postgres bazu
        postgres_url = f"{parsed.scheme}://{parsed.netloc}/postgres"
        
        # Konektuj se na postgres bazu
        conn = await asyncpg.connect(postgres_url)
        
        try:
            # Terminate existing connections to the database
            await conn.execute("""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = $1 AND pid <> pg_backend_pid()
            """, database_name)
            
            # Proveravamo da li baza postoji
            result = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1",
                database_name
            )
            
            if not result:
                logger.info(f"Database '{database_name}' does not exist")
                return True
            
            # Briši bazu
            await conn.execute(f'DROP DATABASE "{database_name}"')
            logger.info(f"Database '{database_name}' dropped successfully")
            
            if backup_path:
                logger.info(f"Backup saved at: {backup_path}")
            
            return True
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Failed to drop database: {e}")
        logger.error(f"Database URL: {database_url}")
        return False