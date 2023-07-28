import jwt
from datetime import datetime


def get_expired_from(token: str) -> datetime:
    decode = jwt.decode(token, verify=False)
    return datetime.fromtimestamp(int(decode["exp"]))
