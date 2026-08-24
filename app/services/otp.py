import secrets
from datetime import datetime, timedelta, timezone

from passlib.context import CryptContext


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


OTP_EXPIRE_MINUTES = 5
MAX_ATTEMPTS = 5


def generate_otp() -> str:
    """
    Генерирует случайный 6-значный код.
    """
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(code: str) -> str:
    """
    Хеширует OTP перед сохранением в БД.
    """
    return pwd_context.hash(code)


def verify_otp(code: str, code_hash: str) -> bool:
    """
    Проверяет введённый код против хеша.
    """
    return pwd_context.verify(code, code_hash)


def get_otp_expiration() -> datetime:
    """
    Возвращает время, до которого код действителен.
    """
    return datetime.now(timezone.utc) + timedelta(
        minutes=OTP_EXPIRE_MINUTES
    )