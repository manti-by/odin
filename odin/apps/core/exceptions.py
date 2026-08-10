class OdinException(Exception):
    pass


class KafkaReadError(OdinException):
    pass


class RedisReadError(OdinException):
    pass
