import redis
# This keeps your settings file clean and ensures redis initializes properly
redis_client = redis.Redis(
    host="redis",
    port=6379,
    db=0,
    decode_responses=True
)