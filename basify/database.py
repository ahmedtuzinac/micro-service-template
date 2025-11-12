from tortoise import Tortoise
from tortoise.contrib.fastapi import register_tortoise
from typing import List, Optional
import logging
import asyncio
import asyncpg
import os
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
    generate_schemas: bool = True
):
    """
    Inicijalizuje Tortoise ORM sa PostgreSQL bazom
    Automatski kreira bazu ako ne postoji
    """
    try:
        # Pokušaj da kreira bazu ako ne postoji
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