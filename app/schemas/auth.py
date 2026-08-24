from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class EmailVerificationRequest(BaseModel):
    email: EmailStr

class EmailVerificationConfirm(BaseModel):
    email: EmailStr
    code: str

class EmailVerificationResponse(BaseModel):
    message: str


class IdentifyRequest(BaseModel):
    identifier: str

class IdentifyResponse(BaseModel):
    exists: bool
    method: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetVerify(BaseModel):
    email: EmailStr
    code: str


class PasswordResetConfirm(BaseModel):
    email: EmailStr
    code: str
    new_password: str


class PasswordResetResponse(BaseModel):
    message: str

class UpdateCurrentUserRequest(BaseModel):
    name: str | None = None

