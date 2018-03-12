from datetime import datetime

from django.conf import settings
from django.middleware.csrf import rotate_token
from django.contrib.auth import load_backend, get_backends, authenticate
from django.utils.translation import LANGUAGE_SESSION_KEY
from django.utils.crypto import constant_time_compare
from rest_framework_jwt.settings import api_settings
from rest_framework_jwt.views import JSONWebTokenAPIView, jwt_response_payload_handler
from www.monitorservice.monitorhook import MonitorHook

SESSION_KEY = '_auth_user_id'
BACKEND_SESSION_KEY = '_auth_user_backend'
HASH_SESSION_KEY = '_auth_user_hash'
REDIRECT_FIELD_NAME = 'next'

monitorHook = MonitorHook()


def login(request, user):
    """
    Persist a user id and a backend in the request. This way a user doesn't
    have to reauthenticate on every request. Note that data set during
    the anonymous session is retained when the user logs in.
    """
    session_auth_hash = ''
    if user is None:
        user = request.user
    if hasattr(user, 'get_session_auth_hash'):
        session_auth_hash = user.get_session_auth_hash()

    if SESSION_KEY in request.session:
        if request.session[SESSION_KEY] != user.pk or (
                session_auth_hash and
                request.session.get(HASH_SESSION_KEY) != session_auth_hash):
            # To avoid reusing another user's session, create a new, empty
            # session if the existing session corresponds to a different
            # authenticated user.
            request.session.flush()
    else:
        request.session.cycle_key()
    request.session[SESSION_KEY] = user.pk
    request.session[BACKEND_SESSION_KEY] = user.backend
    request.session[HASH_SESSION_KEY] = session_auth_hash
    if hasattr(request, 'user'):
        request.user = user
    monitorHook.loginMonitor(user)
    rotate_token(request)
    # user_logged_in.send(sender=user.__class__, request=request, user=user)


def jwtlogin(request, user):
    """
    Persist a user id and a backend in the request. This way a user doesn't
    have to reauthenticate on every request. Note that data set during
    the anonymous session is retained when the user logs in.
    """
    session_auth_hash = ''
    if user is None:
        user = request.user
    if hasattr(user, 'get_session_auth_hash'):
        session_auth_hash = user.get_session_auth_hash()

    if SESSION_KEY in request.session:
        if request.session[SESSION_KEY] != user.pk or (
                session_auth_hash and
                request.session.get(HASH_SESSION_KEY) != session_auth_hash):
            # To avoid reusing another user's session, create a new, empty
            # session if the existing session corresponds to a different
            # authenticated user.
            request.session.flush()
    else:
        request.session.cycle_key()
    request.session[SESSION_KEY] = user.pk
    request.session[BACKEND_SESSION_KEY] = user.backend
    request.session[HASH_SESSION_KEY] = session_auth_hash
    if hasattr(request, 'user'):
        request.user = user
    monitorHook.loginMonitor(user)
    rotate_token(request)
    response_data = jwt_response_payload_handler(rotate_token, user, request)
    if api_settings.JWT_AUTH_COOKIE:
        expiration = (datetime.utcnow() +
                      api_settings.JWT_EXPIRATION_DELTA)
        response_data.set_cookie(api_settings.JWT_AUTH_COOKIE,
                                 rotate_token,
                                 expires=expiration,
                                 httponly=True)


def logout(request):
    """
    Removes the authenticated user's ID from the request and flushes their
    session data.
    """
    # Dispatch the signal before the user is logged out so the receivers have a
    # chance to find out *who* logged out.
    user = getattr(request, 'user', None)
    if hasattr(user, 'is_authenticated') and not user.is_authenticated():
        user = None
    # user_logged_out.send(sender=user.__class__, request=request, user=user)

    # remember language choice saved to session
    # for backwards compatibility django_language is also checked (remove in 1.8)
    language = request.session.get(LANGUAGE_SESSION_KEY, request.session.get('django_language'))

    request.session.flush()

    if language is not None:
        request.session[LANGUAGE_SESSION_KEY] = language

    if hasattr(request, 'user'):
        from www.models import AnonymousUser
        request.user = AnonymousUser()
    monitorHook.logoutMonitor(user)


def get_user(request):
    """
    Returns the user model instance associated with the given request session.
    If no user is retrieved an instance of `AnonymousUser` is returned.
    """
    from www.models import AnonymousUser
    user = None
    try:
        user_id = request.session[SESSION_KEY]
        backend_path = request.session[BACKEND_SESSION_KEY]
    except KeyError:
        pass
    else:
        if backend_path in settings.AUTHENTICATION_BACKENDS:
            backend = load_backend(backend_path)
            user = backend.get_user(user_id)
            # Verify the session
            if ('django.contrib.auth.middleware.SessionAuthenticationMiddleware'
                    in settings.MIDDLEWARE_CLASSES and hasattr(user, 'get_session_auth_hash')):
                session_hash = request.session.get(HASH_SESSION_KEY)
                session_hash_verified = session_hash and constant_time_compare(
                    session_hash,
                    user.get_session_auth_hash()
                )
                if not session_hash_verified:
                    request.session.flush()
                    user = None

    return user or AnonymousUser()

