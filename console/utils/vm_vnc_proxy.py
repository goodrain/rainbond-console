# -*- coding: utf-8 -*-
"""Scoped VNC URL validation; upstreams are administrator-configured per region."""
import json
import os
import re
from urllib.parse import quote, unquote, urlencode, urlparse

from django.core.exceptions import ImproperlyConfigured
from django.http import Http404


def get_vm_vnc_upstream(region_name):
    try:
        upstreams = json.loads(os.environ.get('RAINBOND_VM_VNC_PROXY_UPSTREAMS', '{}'))
    except (TypeError, ValueError):
        raise ImproperlyConfigured('VM VNC proxy region map is invalid')
    if not isinstance(upstreams, dict):
        raise ImproperlyConfigured('VM VNC proxy region map is invalid')
    upstream = upstreams.get(region_name, '')
    if not upstream:
        return ''
    if not isinstance(upstream, str):
        raise ImproperlyConfigured('VM VNC proxy upstream must be a string')
    parsed = urlparse(upstream)
    if (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password
            or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
        raise ImproperlyConfigured('VM VNC proxy upstream must be an HTTP origin without credentials')
    return upstream.rstrip('/')


def component_vnc_prefix(tenant, service):
    values = (service.service_region, tenant.tenant_name, service.service_alias)
    return '/console/regions/{}/teams/{}/apps/{}/vnc/'.format(*(quote(str(value), safe='') for value in values))


def build_component_vnc_url(request, tenant, service):
    if service.extend_method != 'vm' or not get_vm_vnc_upstream(service.service_region):
        return ''
    prefix = component_vnc_prefix(tenant, service)
    # noVNC uses an origin-relative WS path; never expose credentials in the URL.
    return request.build_absolute_uri(prefix + 'vnc_lite.html') + '?' + urlencode({'path': prefix.lstrip('/') + 'websockify'})


def validate_static_path(path):
    decoded = unquote(path)
    if decoded != path or '\\' in path or '%' in path or any(piece in ('', '.', '..') for piece in path.split('/')):
        raise Http404()
    if path == 'vnc_lite.html':
        return path
    if not re.fullmatch(r'(?:app|core|vendor)/[A-Za-z0-9_./-]+\.(?:js|css|png|svg|ico|woff2?|ttf|map)', path):
        raise Http404()
    return path


def component_vnc_backend_path(tenant, service, app):
    namespace = str(tenant.namespace)
    name = '{}-{}'.format(app.k8s_app, service.k8s_component_name)
    if not re.fullmatch(r'[a-z0-9][a-z0-9.-]*', namespace) or not re.fullmatch(r'[a-z0-9][a-z0-9.-]*', name):
        raise Http404()
    return '/k8s/apis/subresources.kubevirt.io/v1alpha3/namespaces/{}/virtualmachineinstances/{}/vnc'.format(namespace, name)
