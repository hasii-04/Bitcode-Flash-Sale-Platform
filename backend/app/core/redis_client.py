import redis.asyncio as redis
from app.core.config import settings

# Initialize Redis connection pool
redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)

# LUA Script for atomic reservation
RESERVE_STOCK_LUA = """
local stock_key = KEYS[1]
local buyers_key = KEYS[2]
local user_id = ARGV[1]

if redis.call("SISMEMBER", buyers_key, user_id) == 1 then
    return -1 -- Error: Already purchased
end

local stock = tonumber(redis.call("GET", stock_key))
if stock and stock > 0 then
    local new_stock = redis.call("DECR", stock_key)
    redis.call("SADD", buyers_key, user_id)
    return new_stock -- Success: Returns remaining stock (>=0)
else
    return -2 -- Error: Sold out
end
"""

async def reserve_item_atomically(item_id: int, user_id: int) -> int:
    stock_key = f"item:{item_id}:stock"
    buyers_key = f"item:{item_id}:buyers"
    
    script = redis_client.register_script(RESERVE_STOCK_LUA)
    result = await script(keys=[stock_key, buyers_key], args=[user_id])
    return result

async def release_item_reservation(item_id: int, user_id: int) -> int:
    stock_key = f"item:{item_id}:stock"
    buyers_key = f"item:{item_id}:buyers"
    removed = await redis_client.srem(buyers_key, user_id)
    if removed:
        return await redis_client.incr(stock_key)
    stock = await redis_client.get(stock_key)
    return int(stock or 0)
