# utils/mail.py
from celery import shared_task
import requests
import logging
from django.conf import settings
from celery.exceptions import MaxRetriesExceededError

logger = logging.getLogger('gurkha_pasal')

@shared_task(bind=True, max_retries=3)
def send_mailersend_email(self, to_email, subject, message):
    try:
        url = "https://api.mailersend.com/v1/email"
        headers = {
            "Authorization": f"Bearer {settings.MAILERSEND_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "from": {"email": f"gurkha@{settings.MAILERSEND_DOMAIN}", "name": "Gurkha Pasal"},
            "to": [{"email": to_email}],
            "subject": subject,
            "text": message,
        }
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        logger.info(f"Email sent to {to_email} with subject: {subject}")
        return True
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            try:
                retry_countdown = 60 * (self.request.retries + 1)  # Wait 1min, 2min, 3min
                logger.warning(f"Rate limit hit for {to_email}. Retrying in {retry_countdown}s (attempt {self.request.retries + 1}/{self.max_retries})")
                self.retry(countdown=retry_countdown)
            except MaxRetriesExceededError:
                logger.error(f"Max retries exceeded for {to_email}: {e}")
                return False
        logger.error(f"Failed to send email to {to_email}: {e} - Response: {e.response.text}")
        return False
        