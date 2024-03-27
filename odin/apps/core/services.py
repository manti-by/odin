import hashlib
import hmac


def get_data_hash(data: dict, secret_key: str) -> str:
    data_string = "\n".join([f"{k}={v}" for k, v in sorted(list(data.items()))]).encode()
    secret = hashlib.sha512(secret_key.encode()).digest()
    signature = hmac.new(key=secret, msg=data_string, digestmod=hashlib.sha512)
    return signature.hexdigest()
