from abc import ABC, abstractmethod


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