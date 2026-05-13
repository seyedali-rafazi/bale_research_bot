# core/state_manager.py

import json
from core.redis_client import init_redis, redis_client


async def set_state(chat_id, step, **kwargs):
    await init_redis()
    key = f"bot:state:{chat_id}"

    if step is None:
        await redis_client.delete(key)
        return

    state_data = {"step": step}
    state_data.update(kwargs)
    await redis_client.set(key, json.dumps(state_data), ex=3600)


async def get_state(chat_id):
    await init_redis()
    key = f"bot:state:{chat_id}"
    raw = await redis_client.get(key)
    if not raw:
        return {}

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


async def clear_state(chat_id):
    await init_redis()
    await redis_client.delete(f"bot:state:{chat_id}")
