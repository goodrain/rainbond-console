from django.core.mail import send_mail


def send_invite_mail(to, content):
    send_mail("invite user", content, 'no-reply@goodrain.com', [to])
