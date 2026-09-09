"""
Email Handler — SMTP Email Sending
===================================
Sends emails via smtplib with TLS encryption.
Uses credentials from .env file.
"""

import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))


def send_email_flow(to_email: str, subject: str, body: str) -> dict:
    """
    Send an email using SMTP with TLS.
    
    Args:
        to_email: Recipient email address
        subject: Email subject line
        body: Email body text
        
    Returns:
        dict with keys:
            - success (bool)
            - error (str): Error message if failed
    """
    if not EMAIL_ADDRESS or EMAIL_ADDRESS == "your_email@gmail.com":
        return {
            "success": False,
            "error": (
                "Email is not configured. Please add your email credentials "
                "to the .env file. See .env.example for instructions."
            )
        }

    if not EMAIL_PASSWORD or EMAIL_PASSWORD == "your_app_password_here":
        return {
            "success": False,
            "error": (
                "Email password not configured. For Gmail, create an App Password "
                "at https://myaccount.google.com/apppasswords"
            )
        }

    try:
        # Create the email message
        message = MIMEMultipart("alternative")
        message["From"] = EMAIL_ADDRESS
        message["To"] = to_email
        message["Subject"] = subject

        # Add plain text body
        text_part = MIMEText(body, "plain")
        message.attach(text_part)

        # Also add an HTML version
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #333;">{subject}</h2>
            <p style="color: #555; line-height: 1.6;">{body}</p>
            <hr style="border: none; border-top: 1px solid #eee; margin-top: 20px;">
            <p style="color: #999; font-size: 12px;">
                Sent via Atlas Voice Assistant
            </p>
        </body>
        </html>
        """
        html_part = MIMEText(html_body, "html")
        message.attach(html_part)

        # Connect and send
        context = ssl.create_default_context()

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, to_email, message.as_string())

        return {"success": True, "error": ""}

    except smtplib.SMTPAuthenticationError:
        return {
            "success": False,
            "error": (
                "Email authentication failed. Please check your credentials. "
                "For Gmail, make sure you're using an App Password."
            )
        }
    except smtplib.SMTPRecipientsRefused:
        return {
            "success": False,
            "error": f"The recipient email '{to_email}' was rejected by the server."
        }
    except smtplib.SMTPException as e:
        return {
            "success": False,
            "error": f"SMTP error: {str(e)}"
        }
    except TimeoutError:
        return {
            "success": False,
            "error": "Email server connection timed out. Please try again."
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Email error: {str(e)}"
        }


def validate_email_config() -> dict:
    """
    Check if email configuration is valid.
    
    Returns:
        dict with keys:
            - configured (bool)
            - email (str): Configured email address (masked)
            - server (str): SMTP server
    """
    configured = (
        EMAIL_ADDRESS
        and EMAIL_ADDRESS != "your_email@gmail.com"
        and EMAIL_PASSWORD
        and EMAIL_PASSWORD != "your_app_password_here"
    )

    masked_email = ""
    if EMAIL_ADDRESS and "@" in EMAIL_ADDRESS:
        parts = EMAIL_ADDRESS.split("@")
        masked_email = f"{parts[0][:2]}***@{parts[1]}"

    return {
        "configured": configured,
        "email": masked_email,
        "server": SMTP_SERVER
    }
