import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

class EmailSender:
    def __init__(self):
        # SECURITY: Read directly from env
        self.email = os.getenv("SENDER_EMAIL")
        self.password = os.getenv("APP_PASSWORD")

        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        
        if not self.email or not self.password:
            raise ValueError("[WARNING] Credentials missing in .env file!")
        
        assert self.email is not None
        assert self.password is not None

    def send_email(self, to_email, subject, body, attachment_file=None, attachment_name=None, is_html=False):
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email # type: ignore
            msg['To'] = to_email
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'html' if is_html else 'plain'))

            if attachment_file is not None:
                attachment_file.seek(0)
                part = MIMEApplication(attachment_file.read(), Name=attachment_name)
                part['Content-Disposition'] = f'attachment; filename="{attachment_name}"'
                msg.attach(part)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email, self.password) # type: ignore
                server.send_message(msg)
            
            return True, "Success"
        except Exception as e:
            return False, str(e)