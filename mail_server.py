from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

class MailServer(object):
    """A class that can be used to send emails."""
    def __init__(self, smtp_server, user, password):
        self._server = smtp_server
        self._user = user
        self._password = password
        self._logged_in = False

    def Login(self):
        self._server.starttls()
        self._server.login(self._user, self._password)
        self._logged_in = True

    def SendEmail(self, sender, receipients, subject, text):
        if not isinstance(receipients, list):
            receipients = [receipients]

        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = ', '.join(receipients)
        msg.attach(MIMEText(text))

        if not self._logged_in:
            self.Login()
        self._server.send_message(msg)
