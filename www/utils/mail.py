from django.core.mail import send_mail


def send_invite_mail(to, content):
    send_mail(u"激活你的好雨云平台账号", content, 'no-reply@goodrain.com', [to])
