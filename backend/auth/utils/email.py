"""Email utilities for sending verification and reset emails."""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional


def is_email_enabled() -> bool:
    """Check if email sending is configured."""
    return bool(os.environ.get('SMTP_USER') and os.environ.get('SMTP_PASSWORD'))


def send_email(to_email: str, subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
    """
    Send email via SMTP (Gmail by default).

    Returns True if sent successfully, False otherwise.
    """
    smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_password = os.environ.get('SMTP_PASSWORD', '')  # Gmail App Password
    smtp_from = os.environ.get('SMTP_FROM', smtp_user)

    if not smtp_user or not smtp_password:
        return False

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = smtp_from
    msg['To'] = to_email

    if text_body:
        msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_from, to_email, msg.as_string())

    return True


def send_verification_email(to_email: str, token: str, base_url: str) -> bool:
    """Send email verification link."""
    verify_url = f"{base_url}?action=verify-email&token={token}"

    subject = "Подтвердите email"

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Подтверждение email</h2>
        <p>Для завершения регистрации подтвердите ваш email:</p>
        <p style="margin: 30px 0;">
            <a href="{verify_url}"
               style="background: #007bff; color: white; padding: 12px 24px;
                      text-decoration: none; border-radius: 4px;">
                Подтвердить email
            </a>
        </p>
        <p style="color: #666; font-size: 14px;">
            Или скопируйте ссылку: {verify_url}
        </p>
        <p style="color: #999; font-size: 12px;">
            Ссылка действительна 24 часа.
        </p>
    </div>
    """

    text_body = f"Подтвердите email по ссылке: {verify_url}"

    return send_email(to_email, subject, html_body, text_body)


def send_password_reset_email(to_email: str, token: str, reset_url: str) -> bool:
    """Send password reset link."""
    full_url = f"{reset_url}?token={token}"

    subject = "Сброс пароля"

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Сброс пароля</h2>
        <p>Вы запросили сброс пароля. Нажмите кнопку ниже:</p>
        <p style="margin: 30px 0;">
            <a href="{full_url}"
               style="background: #007bff; color: white; padding: 12px 24px;
                      text-decoration: none; border-radius: 4px;">
                Сбросить пароль
            </a>
        </p>
        <p style="color: #666; font-size: 14px;">
            Или скопируйте ссылку: {full_url}
        </p>
        <p style="color: #999; font-size: 12px;">
            Ссылка действительна 1 час. Если вы не запрашивали сброс — проигнорируйте это письмо.
        </p>
    </div>
    """

    text_body = f"Сбросьте пароль по ссылке: {full_url}"

    return send_email(to_email, subject, html_body, text_body)
