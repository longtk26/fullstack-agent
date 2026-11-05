from functools import lru_cache
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from src.configs import config

from .sender import ConsoleEmailSender, IEmailSender, OutgoingEmail, SmtpEmailSender

TEMPLATES = Path(__file__).resolve().parents[2] / "templates" / "emails"


@lru_cache
def _environment() -> Environment:
    """`<name>.subject.j2`, `<name>.txt.j2`, `<name>.html.j2`; values are HTML-escaped in the HTML part only."""
    return Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=select_autoescape(enabled_extensions=("html.j2",), default=False),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )


def render(name: str, context: dict[str, Any]) -> tuple[str, str, str]:
    """(subject, text, html) of the template `name`."""
    env = _environment()
    subject = env.get_template(f"{name}.subject.j2").render(context).strip()
    return (
        subject,
        env.get_template(f"{name}.txt.j2").render(context),
        env.get_template(f"{name}.html.j2").render(context),
    )


@lru_cache
def get_sender() -> IEmailSender:
    if config.email_backend == "smtp":
        return SmtpEmailSender(
            config.smtp_host,
            config.smtp_port,
            config.smtp_user,
            config.smtp_password,
            config.smtp_from,
            config.smtp_tls,
        )
    return ConsoleEmailSender()


def send_template(name: str, to: str, context: dict[str, Any], message_id: str | None = None) -> OutgoingEmail:
    """Renders and sends one email; `message_id` (a job id) keeps a retried job's email the same message."""
    subject, text, html = render(name, context)
    headers = {"X-Tags": config.email_tag} if config.email_tag else {}
    if message_id:
        headers["Message-ID"] = f"<{message_id}@app.local>"
    email = OutgoingEmail(to=to, subject=subject, text=text, html=html, headers=headers)
    get_sender().send(email)
    return email
