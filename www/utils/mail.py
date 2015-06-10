from django.core.mail import send_mail


def send_invite_mail(to, content):
    send_mail("invite user", content, 'no-reply@goodrain.com', [to])


def send_invite_mail_withHtml(to, html_content):
    send_mail(unicode('激活你的好雨云平台账号','UTF-8'), "", 'no-reply@goodrain.com', [to], fail_silently=False, auth_user=None, auth_password=None, connection=None, html_message=html_content)