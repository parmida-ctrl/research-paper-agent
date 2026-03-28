"""
Email delivery for the Research Paper Digest.
"""

import os
import logging
import smtplib
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

logger = logging.getLogger("papers.emailer")


class DigestEmailer:
    def __init__(self):
        self.to_email = os.environ.get("REPORT_EMAIL_TO", "")
        self.from_email = os.environ.get("REPORT_EMAIL_FROM", "")
        self.sendgrid_key = os.environ.get("SENDGRID_API_KEY", "")
        self.smtp_password = os.environ.get("SMTP_PASSWORD", "")

    def send(self, subject, html_body, attachment_html=None, attachment_name="paper_digest.html"):
        if not self.to_email:
            logger.error("REPORT_EMAIL_TO not configured")
            return

        if self.sendgrid_key:
            self._send_sendgrid(subject, html_body, attachment_html, attachment_name)
        elif self.smtp_password:
            self._send_smtp(subject, html_body, attachment_html, attachment_name)
        else:
            logger.error("No email credentials configured")

    def _send_sendgrid(self, subject, html_body, attachment_html, attachment_name):
        try:
            import sendgrid
            from sendgrid.helpers.mail import (
                Mail, Email, To, Content, Attachment,
                FileContent, FileName, FileType, Disposition,
            )

            sg = sendgrid.SendGridAPIClient(api_key=self.sendgrid_key)
            message = Mail(
                from_email=Email(self.from_email or "agent@paperdigest.dev"),
                to_emails=To(self.to_email),
                subject=subject,
                html_content=Content("text/html", html_body),
            )

            if attachment_html:
                encoded = base64.b64encode(attachment_html.encode("utf-8")).decode("utf-8")
                attachment = Attachment(
                    FileContent(encoded),
                    FileName(attachment_name),
                    FileType("text/html"),
                    Disposition("attachment"),
                )
                message.attachment = attachment

            response = sg.client.mail.send.post(request_body=message.get())
            logger.info(f"SendGrid response: {response.status_code}")
        except Exception as e:
            logger.error(f"SendGrid send failed: {e}")
            if self.smtp_password:
                self._send_smtp(subject, html_body, attachment_html, attachment_name)

    def _send_smtp(self, subject, html_body, attachment_html, attachment_name):
        try:
            msg = MIMEMultipart("mixed")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = self.to_email

            body_part = MIMEMultipart("alternative")
            body_part.attach(MIMEText("Your weekly research paper digest is ready. Open the attached HTML file for the full version.", "plain"))
            body_part.attach(MIMEText(html_body, "html"))
            msg.attach(body_part)

            if attachment_html:
                att = MIMEBase("text", "html")
                att.set_payload(attachment_html.encode("utf-8"))
                encoders.encode_base64(att)
                att.add_header("Content-Disposition", f"attachment; filename={attachment_name}")
                msg.attach(att)

            smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
            smtp_port = int(os.environ.get("SMTP_PORT", "587"))

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(self.from_email, self.smtp_password)
                server.sendmail(self.from_email, self.to_email, msg.as_string())

            logger.info(f"Email sent via SMTP to {self.to_email}")
        except Exception as e:
            logger.error(f"SMTP send failed: {e}")
