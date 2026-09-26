"""
Email delivery for the Research Paper Digest, using Resend.
"""

import os
import base64
import logging
import requests

logger = logging.getLogger("papers.emailer")


class DigestEmailer:
    def __init__(self):
        self.to_email = os.environ.get("REPORT_EMAIL_TO", "")
        self.api_key = os.environ.get("RESEND_API_KEY", "")
        self.from_email = "onboarding@resend.dev"

    def send(self, subject, html_body, attachment_html=None, attachment_name="paper_digest.html"):
        if not self.to_email or not self.api_key:
            raise RuntimeError("Missing REPORT_EMAIL_TO or RESEND_API_KEY secret")

        payload = {
            "from": f"Research Digest <{self.from_email}>",
            "to": [self.to_email],
            "subject": subject,
            "html": html_body,
        }

        if attachment_html:
            payload["attachments"] = [{
                "filename": attachment_name,
                "content": base64.b64encode(attachment_html.encode("utf-8")).decode("utf-8"),
            }]

        response = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
            timeout=30,
        )

        if response.status_code >= 300:
            raise RuntimeError(f"Resend failed ({response.status_code}): {response.text}")

        logger.info(f"Email sent via Resend to {self.to_email}")
