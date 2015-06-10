from django.core.mail import send_mail


def send_invite_mail(to, content):
    send_mail("invite user", content, 'no-reply@goodrain.com', [to])


def send_invite_mail_withHtml(to, html_content):
    send_mail(u'\u6fc0\u6d3b\u4f60\u7684\u597d\u96e8\u4e91\u5e73\u53f0\u8d26\u53f7', "", 'no-reply@goodrain.com', [to], fail_silently=False, auth_user=None, auth_password=None, connection=None, html_message=html_content)