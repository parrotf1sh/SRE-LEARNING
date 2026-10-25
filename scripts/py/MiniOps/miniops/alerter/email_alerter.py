"""Email alerter via SMTP."""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from miniops.alerter.base import BaseAlerter
from miniops.result import Alert

logger = logging.getLogger(__name__)


class EmailAlerter(BaseAlerter):
    """
    Sends alerts via SMTP email.

    NOTE: This alerter is DISABLED by default. To enable:
    1. Set SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD env vars
       or configure them in config/default.yaml
    2. Set enabled: true in config
    3. Configure recipients list
    """

    def __init__(self, smtp_host: str = "", smtp_port: int = 465,
                 username: str = "", password: str = "",
                 recipients: list[str] | None = None,
                 use_tls: bool = True,
                 enabled: bool = False, trigger_on: list[str] | None = None):
        super().__init__(enabled=enabled, trigger_on=trigger_on)
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.recipients = recipients or []
        self.use_tls = use_tls

    def send(self, alert: Alert) -> bool:
        if not self.should_send(alert):
            logger.debug("Email alerter disabled or level not in trigger_on, skipping")
            return False

        if not self.smtp_host:
            logger.warning("SMTP host not configured, skipping email alert")
            return False

        if not self.recipients:
            logger.warning("No recipients configured, skipping email alert")
            return False

        msg = self._build_email(alert)

        try:
            if self.use_tls:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=10)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10)
                server.starttls()

            if self.username and self.password:
                server.login(self.username, self.password)

            server.sendmail(self.username or "miniops@localhost",
                            self.recipients, msg.as_string())
            server.quit()
            logger.info("Email alert sent to %s: %s", self.recipients, alert.message)
            return True
        except smtplib.SMTPException as e:
            logger.error("SMTP error: %s", e)
            return False
        except Exception as e:
            logger.error("Email send error: %s", e)
            return False

    def _build_email(self, alert: Alert) -> MIMEMultipart:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[MiniOps {alert.level.upper()}] {alert.source}"
        msg["From"] = self.username or "miniops@localhost"
        msg["To"] = ", ".join(self.recipients)

        text = (
            f"MiniOps Alert\n"
            f"{'=' * 40}\n"
            f"Level:   {alert.level.upper()}\n"
            f"Source:  {alert.source}\n"
            f"Message: {alert.message}\n"
            f"Time:    {alert.timestamp}\n"
        )
        if alert.details:
            text += f"\nDetails:\n{alert.details}\n"

        html = f"""
        <html><body>
        <h2 style="color: {'red' if alert.level == 'critical' else 'orange'}">
            [MiniOps {alert.level.upper()}]
        </h2>
        <table border="1" cellpadding="5" cellspacing="0">
            <tr><td><b>Source</b></td><td>{alert.source}</td></tr>
            <tr><td><b>Message</b></td><td>{alert.message}</td></tr>
            <tr><td><b>Time</b></td><td>{alert.timestamp}</td></tr>
        </table>
        </body></html>
        """

        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))
        return msg
