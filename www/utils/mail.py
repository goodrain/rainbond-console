from django.core.mail import send_mail

import sys
reload(sys)
sys.setdefaultencoding('UTF-8')

class MailUtil(object):
            
    def get_inviteContent(self, link_url):
        return "rest"

        
    def send_invite_mail(to, content):
        send_mail("invite user", content, 'no-reply@goodrain.com', [to])
        
    def send_invite_mail_withHtml(to, html_content):
        send_mail('test', "", 'no-reply@goodrain.com', [to], fail_silently=False, auth_user=None, auth_password=None, connection=None, html_message=html_content)
    
