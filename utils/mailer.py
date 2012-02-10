"""
Send email
"""
from config import NOODLES_ERROR_RECIPIENT, MAIL_SERVER, MAIL_PORT, MAIL_LOGIN, MAIL_PASSWORD, NOODLES_ERROR_SENDER
from email.mime.text import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.Utils import COMMASPACE, formatdate
from email.header import Header
import smtplib


class MailMan(object):
    def __init__(self, server=MAIL_SERVER, port=MAIL_PORT, login=MAIL_LOGIN,
                 password=MAIL_PASSWORD):
        self.server = server
        self.port = port
        self.login = login
        self.password = password

    @staticmethod
    def mail_send(self, subject, message, sender=NOODLES_ERROR_SENDER, recipient=NOODLES_ERROR_RECIPIENT):
        assert type(recipient) == list
        #msg = MIMEText(message, "", "utf-8")
        msg = MIMEMultipart('related')
        msg['From'] = Header(sender.decode("utf-8")).encode()
        msg['To'] = Header(COMMASPACE.join(recipient).decode("utf-8")).encode()
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = Header(subject.decode("utf-8")).encode()
        msg.preamble = 'This is a multi-part message in MIME format.'
        msgAlternative = MIMEMultipart('alternative')
        msg.attach(msgAlternative)
        msgText = MIMEText(str(message))
        msgAlternative.attach(msgText)
        msgText = MIMEText('<pre>%s</pre>' % message, 'html')
        msgAlternative.attach(msgText)
        server = smtplib.SMTP(self.server, self.port)
        server.starttls()
        server.login(self.login, self.password)
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()
