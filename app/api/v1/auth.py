from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

from app.core.database import get_db
from app.core.security import (
    hash_password,
    create_access_token,
    verify_password,
)

from app.models.email_verification import EmailVerification
from app.models.password_reset import PasswordResetCode
from app.schemas.auth import (
    EmailVerificationConfirm,
    EmailVerificationRequest,
    EmailVerificationResponse,
    IdentifyRequest,
    IdentifyResponse,
    RegisterRequest,
    TokenResponse,
    LoginRequest,
    PasswordResetRequest,
    PasswordResetVerify,
    PasswordResetConfirm,
    PasswordResetResponse
)

from app.services.email import DevEmailService
from app.services.otp import (
    generate_otp,
    get_otp_expiration,
    hash_otp,
    verify_otp,
)







router = APIRouter()

email_service = DevEmailService()


@router.post(
    "/email/request-code",
    response_model=EmailVerificationResponse,
)
async def request_email_code(
    data: EmailVerificationRequest,
    session: AsyncSession = Depends(get_db),
):
    email = data.email.lower().strip()

    # Генерирация кода
    code = generate_otp()

    # Хеширование кода
    code_hash = hash_otp(code)

    # Создание записи в БД
    verification = EmailVerification(
        email=email,
        code_hash=code_hash,
        expires_at=get_otp_expiration(),
        attempts=0,
    )

    session.add(verification)
    await session.commit()

    # Пока вывод кода в терминал
    await email_service.send_verification_code(
        email=email,
        code=code,
    )

    return EmailVerificationResponse(
        message="Verification code sent",
    )

# Проверка кода
@router.post(
    "/email/verify",
    response_model=EmailVerificationResponse,
)
async def verify_email_code(
    data: EmailVerificationConfirm,
    session: AsyncSession = Depends(get_db),
):
    email = data.email.lower().strip()

    # Поиск последней попытки подтверждения для этого email
    result = await session.execute(
        select(EmailVerification)
        .where(EmailVerification.email == email)
        .order_by(EmailVerification.created_at.desc())
        .limit(1)
    )

    verification = result.scalar_one_or_none()

    if verification is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code not found",
        )

    # Проверка количество попыток
    if verification.attempts >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Too many attempts",
        )

    # Проверка, не использован ли код
    if verification.verified_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code already used",
        )

    # Проверка срока действия
    now = datetime.now(timezone.utc)

    if verification.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code expired",
        )

    # Проверка кода
    if not verify_otp(
        data.code,
        verification.code_hash,
    ):
        verification.attempts += 1
        await session.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    # Код правильный
    verification.verified_at = now

    await session.commit()

    return EmailVerificationResponse(
        message="Email successfully verified",
    )

# Идентификация
@router.post(
    "/identify",
    response_model=IdentifyResponse,
)
async def identify_user(
    data: IdentifyRequest,
    session: AsyncSession = Depends(get_db),
):
    identifier = data.identifier.strip().lower()

    # Пока поддерживаем только email.
    if "@" not in identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only email identification is supported for now",
        )

    result = await session.execute(
        select(User).where(User.email == identifier)
    )

    user = result.scalar_one_or_none()

    if user is None:
        return IdentifyResponse(
            exists=False,
            method="email",
        )

    return IdentifyResponse(
        exists=True,
        method="email",
    )

@router.post(
    "/register",
    response_model=TokenResponse,
)
async def register_user(
    data: RegisterRequest,
    session: AsyncSession = Depends(get_db),
):
    email = data.email.lower().strip()

    # Проверяем, существует ли пользователь
    result = await session.execute(
        select(User).where(User.email == email)
    )

    existing_user = result.scalar_one_or_none()

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    # Проверяем, подтверждён ли email
    result = await session.execute(
        select(EmailVerification)
        .where(
            EmailVerification.email == email,
            EmailVerification.verified_at.is_not(None),
        )
        .order_by(EmailVerification.created_at.desc())
        .limit(1)
    )

    verification = result.scalar_one_or_none()

    if verification is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is not verified",
        )

    # Создаём пользователя
    user = User(
        email=email,
        password_hash=hash_password(data.password),
    )

    session.add(user)

    await session.commit()
    await session.refresh(user)

    # Создаём JWT
    access_token = create_access_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
    )

@router.post(
    "/login",
    response_model=TokenResponse,
)
async def login_user(
    data: LoginRequest,
    session: AsyncSession = Depends(get_db),
):
    email = data.email.lower().strip()

    result = await session.execute(
        select(User).where(User.email == email)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(
        data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
    )

@router.post(
    "/password-reset/request-code",
    response_model=PasswordResetResponse,
)
async def request_password_reset_code(
    data: PasswordResetRequest,
    session: AsyncSession = Depends(get_db),
):
    email = data.email.lower().strip()

    result = await session.execute(
        select(User).where(User.email == email)
    )

    user = result.scalar_one_or_none()

    # Не сообщаем, существует ли такой email.
    if user is None:
        return PasswordResetResponse(
            message="If the email exists, a verification code has been sent",
        )

    code = generate_otp()
    code_hash = hash_otp(code)

    reset_code = PasswordResetCode(
        email=email,
        code_hash=code_hash,
        expires_at=get_otp_expiration(),
        attempts=0,
    )

    session.add(reset_code)
    await session.commit()

    await email_service.send_verification_code(
        email=email,
        code=code,
    )

    return PasswordResetResponse(
        message="If the email exists, a verification code has been sent",
    )

@router.post(
    "/password-reset/verify",
    response_model=PasswordResetResponse,
)
async def verify_password_reset_code(
    data: PasswordResetVerify,
    session: AsyncSession = Depends(get_db),
):
    email = data.email.lower().strip()

    result = await session.execute(
        select(PasswordResetCode)
        .where(PasswordResetCode.email == email)
        .order_by(PasswordResetCode.created_at.desc())
        .limit(1)
    )

    reset_code = result.scalar_one_or_none()

    if reset_code is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code not found",
        )

    if reset_code.attempts >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Too many attempts",
        )

    if reset_code.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code already used",
        )

    now = datetime.now(timezone.utc)

    if reset_code.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code expired",
        )

    if not verify_otp(
        data.code,
        reset_code.code_hash,
    ):
        reset_code.attempts += 1
        await session.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    return PasswordResetResponse(
        message="Password reset code verified",
    )


@router.post(
    "/password-reset/confirm",
    response_model=PasswordResetResponse,
)
async def confirm_password_reset(
    data: PasswordResetConfirm,
    session: AsyncSession = Depends(get_db),
):
    email = data.email.lower().strip()

    result = await session.execute(
        select(PasswordResetCode)
        .where(PasswordResetCode.email == email)
        .order_by(PasswordResetCode.created_at.desc())
        .limit(1)
    )

    reset_code = result.scalar_one_or_none()

    if reset_code is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code not found",
        )

    if reset_code.attempts >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Too many attempts",
        )

    if reset_code.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code already used",
        )

    now = datetime.now(timezone.utc)

    if reset_code.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code expired",
        )

    if not verify_otp(
        data.code,
        reset_code.code_hash,
    ):
        reset_code.attempts += 1
        await session.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    result = await session.execute(
        select(User).where(User.email == email)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found",
        )

    user.password_hash = hash_password(data.new_password)
    reset_code.used_at = now

    await session.commit()

    return PasswordResetResponse(
        message="Password successfully reset",
    )