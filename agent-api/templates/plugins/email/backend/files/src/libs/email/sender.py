import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from email.message import EmailMessage as MimeMessage

from src.configs import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class OutgoingEmail:
    to: str
    subject: str
    text: str
    html: str
    headers: dict[str, str] = field(default_factory=dict)


class IEmailSender(ABC):
    """Where emails go (Story 10.7): SMTP in a running app, the log in development and tests."""

    @abstractmethod
    def send(self, email: OutgoingEmail) -> None:
        pass


class SmtpEmailSender(IEmailSender):
    def __init__(self, host: str, port: int, user: str, password: str, sender: str, tls: bool):
        self.host, self.port, self.user, self.password, self.sender, self.tls = host, port, user, password, sender, tls

    def send(self, email: OutgoingEmail) -> None:
        message = MimeMessage()
        message["From"], message["To"], message["Subject"] = self.sender, email.to, email.subject
        for name, value in email.headers.items():
            message[name] = value
        message.set_content(email.text)
        message.add_alternative(email.html, subtype="html")
        with smtplib.SMTP(self.host, self.port, timeout=15) as smtp:
            if self.tls:
                smtp.starttls()
            if self.user:
                smtp.login(self.user, self.password)
            smtp.send_message(message)


class ConsoleEmailSender(IEmailSender):
    """Test double (`EMAIL_BACKEND=console`, the default): writes the email to the log instead of sending it."""

    def __init__(self) -> None:
        self.sent: list[OutgoingEmail] = []

    def send(self, email: OutgoingEmail) -> None:
        self.sent.append(email)
        logger.info("email (console)", extra={"to": email.to, "subject": email.subject, "text": email.text[:500]})
