# coding: utf-8
"""
This module collects helper functions and classes that "span" multiple levels
of MVC. In other words, these functions/classes introduce controlled coupling
for convenience's sake.
"""
from django.db.models.base import ModelBase
from django.db.models.manager import Manager
from django.db.models.query import QuerySet

from console.exception.main import AbortRequest


def _get_queryset(klass):
    """
    Returns a QuerySet from a Model, Manager, or QuerySet. Created to make
    get_object_or_404 and get_list_or_404 more DRY.

    Raises a ValueError if klass is not a Model, Manager, or QuerySet.
    """
    if isinstance(klass, QuerySet):
        return klass
    elif isinstance(klass, Manager):
        manager = klass
    elif isinstance(klass, ModelBase):
        manager = klass._default_manager
    else:
        if isinstance(klass, type):
            klass__name = klass.__name__
        else:
            klass__name = klass.__class__.__name__
        raise ValueError("Object is of type '%s', but must be a Django Model, "
                         "Manager, or QuerySet" % klass__name)
    return manager.all()


def get_object_or_404(klass, msg='', msg_show=None, error_code=None, *args, **kwargs):
    """
    Uses get() to return an object, or raises a Http404 exception if the object
    does not exist.

    klass may be a Model, Manager, or QuerySet object. All other passed
    arguments and keyword arguments are used in the get() query.

    Note: Like with get(), an MultipleObjectsReturned will be raised if more than one
    object is found.
    """
    queryset = _get_queryset(klass)
    try:
        return queryset.get(*args, **kwargs)
    except queryset.model.DoesNotExist:
        raise AbortRequest(msg, msg_show=msg_show, status_code=404, error_code=error_code)
