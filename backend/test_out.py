import sys
sys.path.append("/home/hiru616/Documents/Projects/SwiftDrop/backend")

import asyncio
from app.core.database import AsyncSessionLocal
from app.domain.models import User
from sqlalchemy import select
from app.services.auth_service import AuthService
import traceback

async def test():
    try:
        with open("test_out.txt", "w") as f:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(User))
                users = result.scalars().all()
                for u in users:
                    f.write(f"User: {u.email}, Hash: {u.hashed_password}\n")
                    f.write(f"Verify 'password123': {AuthService.verify_password('password123', u.hashed_password)}\n")
                    f.write(f"Verify 'Minimum 8 characters': {AuthService.verify_password('Minimum 8 characters', u.hashed_password)}\n")
    except Exception as e:
        with open("test_out.txt", "a") as f:
            f.write(traceback.format_exc())

asyncio.run(test())
