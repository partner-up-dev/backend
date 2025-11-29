import datetime
import random
import string


def cent_to_yuan(cent: int | None) -> int:
    """
    将以分为单位的金额数值转为以元为单位

    如果是None，将会返回0
    """
    if cent is None:
        return 0

    return int(round(cent / 100, 0))


def generate_random_string(length=6):
    characters = string.ascii_letters + string.digits
    return "".join(random.choice(characters) for _ in range(length))


def get_utc_now() -> datetime.datetime:
    """Get current UTC datetime.

    Use this as the default_factory for SQLModel datetime fields.
    """
    return datetime.datetime.now(datetime.timezone.utc)
