import asyncio
from app.core.database import engine
from app.domain.models import Base

async def init_models():
    async with engine.begin() as conn:
        # This will create all tables defined in models.py
        print("Creating database tables...")
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully.")

if __name__ == "__main__":
    asyncio.run(init_models())
