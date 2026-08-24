class OdinException(Exception):
    pass


class RedisReadError(OdinException):
    """Raised when reading state from Redis fails.

    This error is raised when the Redis client cannot retrieve a value,
    when the stored payload cannot be decoded as JSON, or when the decoded
    payload has an unexpected type. Callers should treat it as a transient
    read failure and fall back to a safe default.
    """

    pass
