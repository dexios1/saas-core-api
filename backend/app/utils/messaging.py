"""The :mod:`app.utils.messaging` module contains resuable utils for messaging users via SMS or email
"""
# Author: Christopher Dare

from enum import Enum
from typing import Any, List, Optional, Union

import requests
from pydantic import BaseModel, EmailStr

from app.core.config import settings


class MessagingProviders(Enum):
    TWILIO = "twilio"
    SENDGRID = "sendgrid"
    MAILGUN = "mailgun"


class ModeOfMessageDelivery(Enum):
    SMS = "sms"
    EMAIL = "email"


class EmailTemplate(Enum):
    NEW_USER_WELCOME = ""


class MessageClient:
    def __init__(self, provider: str = MessagingProviders.TWILIO, *args, **kwargs):

        if isinstance(provider, str):
            try:
                provider = MessagingProviders(provider)
            except ValueError:
                raise ValueError(f"{provider} is not a supported messaging provider")

        self.provider = provider
        self.from_address = None

        if provider == MessagingProviders.TWILIO:
            from twilio.rest import Client as TwilioClient

            # Your Account SID from twilio.com/console
            account_sid = settings.TWILIO_ACCOUNT_SID
            # Your Auth Token from twilio.com/console
            auth_token = settings.TWILIO_AUTH_TOKEN

            self.client = TwilioClient(account_sid, auth_token)
            self.messaging_service_sid = settings.TWILIO_MESSAGING_SERVICE_SID
        elif provider == MessagingProviders.SENDGRID:
            from sendgrid import SendGridAPIClient

            self.client = SendGridAPIClient(settings.SENDGRID_API_KEY)
        elif provider == MessagingProviders.MAILGUN:
            self.api_key = settings.MAILGUN_API_KEY
            self.api_base_url = settings.MAILGUN_BASE_URL
        else:
            raise Exception("Unsupported messaging provider")

    def send(self, recipient: str, message: str, template: Any = None):
        raise NotImplementedError(
            "This is an abstract class method which needs implementation in order to be used"
        )


class SMSMessageClient(MessageClient):
    def send(self, recipient: str, message: str, template: Any = None):
        if self.provider == MessagingProviders.TWILIO:
            message = self.client.messages.create(
                messaging_service_sid=self.messaging_service_sid,
                body=message,
                to=recipient,
            )
        else:
            raise Exception("Unsupported messaging provider")


class EmailMessageClient(MessageClient):
    def send(
        self,
        recipients: Union[List, EmailStr],
        subject: str,
        message: Optional[str] = None,
        template: Optional[EmailTemplate] = None,
        template_vars: Optional[BaseModel] = None,
    ):
        response = None
        html_content = None
        if not message and not template:
            raise ValueError(
                "Please provide a template or message in order to send an email!"
            )
        if message:
            html_content = message
        if template:
            raise ValueError("Dynamic Email templates not yet supported!")
        if self.provider == MessagingProviders.SENDGRID:
            from sendgrid.helpers.mail import Mail

            message = Mail(
                from_email=settings.EMAILS_FROM_EMAIL,
                to_emails=recipients,
                subject=subject,
                html_content=html_content,
            )
            try:
                response = self.client.send(message)
            except Exception as e:
                raise e
        elif self.provider == MessagingProviders.MAILGUN:
            recipients = recipients if isinstance(recipients, list) else [recipients]
            mailgun_data = {
                "from": f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>",
                "to": recipients,
                "subject": f"{subject}",
            }
            if template:
                mailgun_data["template"] = template.dict() if isinstance(template, EmailTemplate) else template
                mailgun_data["h:X-Mailgun-Variables"] = template_vars
            elif message:
                mailgun_data["text"] = message

            response = requests.post(
                f"{self.api_base_url}/messages",
                auth=("api", self.api_key),
                data=mailgun_data,
            )
        else:
            raise Exception("Unsupported messaging provider")

        return response


def send_sms(
    mobile: str,
    message: str,
    provider: Union[str, MessagingProviders] = MessagingProviders.TWILIO,
):
    client = SMSMessageClient(provider=provider)
    client.send(message=message, recipient=mobile)


def send_email(
    recipients: Union[List[EmailStr], EmailStr],
    subject: str,
    message: Optional[str] = None,
    template: Optional[EmailTemplate] = None,
    template_vars: Optional[BaseModel] = None,
    provider: MessagingProviders = MessagingProviders.SENDGRID,
):
    client = EmailMessageClient(provider=provider)
    recipients = recipients if isinstance(recipients, list) else [recipients]
    return client.send(
        recipients=recipients, subject=subject, template=template, message=message
    )
