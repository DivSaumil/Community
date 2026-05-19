import asyncio
import os
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Ensure the backend directory is in the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings


async def create_database_if_not_exists() -> None:
    # Parse settings.DATABASE_URL to check target DB name
    db_name = settings.DATABASE_URL.split("/")[-1]
    # Remove any query params like ?ssl=... if present
    if "?" in db_name:
        db_name = db_name.split("?")[0]
        
    default_url = settings.DATABASE_URL.replace(f"/{db_name}", "/postgres")
    
    print(f"Connecting to default database to check '{db_name}'...")
    engine = create_async_engine(default_url, isolation_level="AUTOCOMMIT")
    
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT 1 FROM pg_database WHERE datname='{db_name}'")
        )
        exists = result.scalar()
        if not exists:
            print(f"Database '{db_name}' does not exist. Creating...")
            await conn.execute(text(f"CREATE DATABASE {db_name}"))
            print(f"Database '{db_name}' created successfully.")
        else:
            print(f"Database '{db_name}' already exists.")
            
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_database_if_not_exists())
