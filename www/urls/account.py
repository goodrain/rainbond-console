from django.conf.urls import patterns, url
from www.views.account import PasswordReset, PasswordResetBegin, PasswordResetMethodSelect, ChangeLoginPassword
from django.contrib.auth.decorators import login_required

urlpatterns = patterns(
    '',
    url(r'^begin_password_reset$', PasswordResetBegin.as_view()),
    url(r'^select_verify_method$', PasswordResetMethodSelect.as_view()),
    #url(r'^password_reset_sended$', PasswordResetSended.as_view()),
    url(r'^reset_password$', PasswordReset.as_view()),
    # query user info
    url(r'^info$', PasswordReset.as_view()),
    url(r'^changepwd$', login_required(ChangeLoginPassword.as_view())),
)
