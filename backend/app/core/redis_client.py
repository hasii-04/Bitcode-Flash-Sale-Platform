import redis.asyncio as redis
from app.core.config import settings

# Initialize Redis connection pool
redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)

# LUA Script for atomic reservation
# Allows same user to buy same item multiple times (different transactions)
# Only enforces stock > 0
RESERVE_STOCK_LUA = """
local stock_key = KEYS[1]
local user_id = ARGV[1]

local stock = tonumber(redis.call("GET", stock_key))
if stock and stock > 0 then
    local new_stock = redis.call("DECR", stock_key)
    return new_stock -- Success: Returns remaining stock (>=0)
else
    return -2 -- Error: Sold out
end
"""

async def reserve_item_atomically(item_id: int, user_id: int) -> int:
    stock_key = f"item:{item_id}:stock"

    script = redis_client.register_script(RESERVE_STOCK_LUA)
    result = await script(keys=[stock_key], args=[user_id])
    return result
