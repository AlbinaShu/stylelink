from abc import ABC, abstractmethod
from email.message import EmailMessage
import aiosmtplib

from app.core.config import settings


class EmailService(ABC):

    @abstractmethod
    async def send_verification_code(
        self,
        email: str,
        code: str,
    ) -> None:
        pass


class DevEmailService(EmailService):

    async def send_verification_code(
        self,
        email: str,
        code: str,
    ) -> None:
        print()
        print("=" * 50)
        print("DEV EMAIL VERIFICATION")
        print(f"To: {email}")
        print(f"Code: {code}")
        print("=" * 50)
        print()


class GmailEmailService(EmailService):

    async def send_verification_code(
        self,
        email: str,
        code: str,
    ) -> None:
        message = EmailMessage()
        message["From"] = settings.smtp_from
        message["To"] = email
        message["Subject"] = "StyleLink — код подтверждения"

        message.set_content(
            f"Ваш код подтверждения: {code}\n\n"
            "Если вы не запрашивали этот код, просто проигнорируйте это письмо."
        )

        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            start_tls=True,
            username=settings.smtp_user,
            password=settings.smtp_password,
        )