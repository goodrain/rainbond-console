# -*- coding: utf8 -*-
from django.core.mail import send_mail
from django.conf import settings


def send_invite_mail(to, content):
    if settings.MODULES["Email_Invite"]:
        send_mail("invite user", content, 'no-reply@goodrain.com', [to])


def send_invite_mail_withHtml(to, html_content):
    if settings.MODULES["Email_Invite"]:
        send_mail(u'\u6fc0\u6d3b\u4f60\u7684\u597d\u96e8\u4e91\u5e73\u53f0\u8d26\u53f7', "", 'no-reply@goodrain.com',
              [to], fail_silently=False, auth_user=None, auth_password=None, connection=None, html_message=html_content)


def send_reset_pass_mail(to, content):
    if settings.MODULES["Email_Invite"]:
        send_mail(u"重新设置您的密码", content, 'no-reply@goodrain.com', [to])
    elif settings.MODULES["Password_Reset"]:
        send_mail(u"重新设置您的密码", content, 'no-reply@goodrain.com', [to])
