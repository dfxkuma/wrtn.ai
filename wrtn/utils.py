import jwt
from datetime import datetime


def get_expired_from(token: str) -> datetime:
    decode = jwt.decode(token, algorithms="HS256", options={"verify_signature": False})
    return datetime.fromtimestamp(int(decode["exp"]))
