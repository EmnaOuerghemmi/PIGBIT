from redis.asyncio import Redis, from_url

from app.core.config import settings

_redis: Redis | None = None


async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


# ---------- Rate limiting helpers ----------

async def increment_login_attempts(ip: str) -> int:
    """Incrémente le compteur anti-bruteforce. Fail-open si Redis est indisponible
    (un cache down ne doit pas bloquer toute l'authentification)."""
    try:
        r = await get_redis()
        key = f"login_attempts:{ip}"
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, 900)  # 15 min TTL on first attempt
        return count
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(f"Redis unavailable (increment_login_attempts): {exc}")
        return 0


async def reset_login_attempts(ip: str) -> None:
    try:
        r = await get_redis()
        await r.delete(f"login_attempts:{ip}")
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(f"Redis unavailable (reset_login_attempts): {exc}")


async def get_login_attempts(ip: str) -> int:
    """Compteur anti-bruteforce. Fail-open (0) si Redis est indisponible — le
    verrouillage par compte (`locked_until` en base) reste actif en secours."""
    try:
        r = await get_redis()
        val = await r.get(f"login_attempts:{ip}")
        return int(val) if val else 0
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(f"Redis unavailable (get_login_attempts): {exc}")
        return 0


# ---------- Cache helpers ----------

async def set_cache(key: str, value: str, ttl_seconds: int = 300) -> None:
    r = await get_redis()
    await r.setex(key, ttl_seconds, value)


async def get_cache(key: str) -> str | None:
    r = await get_redis()
    return await r.get(key)


async def delete_cache(key: str) -> None:
    r = await get_redis()
    await r.delete(key)
