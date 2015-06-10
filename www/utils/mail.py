from django.core.mail import send_mail


def send_invite_mail(to, content):
    send_mail('invite email', content, 'no-reply@goodrain.com', [to])
