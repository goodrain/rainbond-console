"""Visibility for delivery-owned catalog copies; legacy templates keep their existing behavior."""
import uuid
from django.db.models import CharField, Exists, Func, OuterRef, Value
from django.db.models.functions import Cast, Replace


class CatalogText(Func):
    """Compare canonical IDs/versions independently of old and new table collations."""
    template = "%(expressions)s"
    output_field = CharField()

    def as_mysql(self, compiler, connection, **extra_context):
        extra_context["template"] = "CONVERT(%(expressions)s USING utf8mb4) COLLATE utf8mb4_bin"
        return super().as_sql(compiler, connection, **extra_context)


def _catalog_identity(query):
    return query.annotate(_catalog_id=CatalogText(Replace(Cast("template_id", CharField()), Value("-"), Value(""))))


def visible_catalog_versions(query):
    from console.models.delivery_template import DeliveryTemplateVersion, DeliveryListingRequest
    published = DeliveryListingRequest.objects.filter(destination__type="local", publication_status="published")
    hidden = _catalog_identity(DeliveryTemplateVersion.objects.all()).annotate(_catalog_version=CatalogText("version")).filter(
        _catalog_id=CatalogText(OuterRef("app_id")), _catalog_version=CatalogText(OuterRef("version"))).exclude(
            id__in=published.values("version_id"))
    return query.alias(_delivery_hidden=Exists(hidden)).filter(_delivery_hidden=False)


def visible_catalog_apps(query):
    from console.models.delivery_template import DeliveryTemplate, DeliveryListingRequest
    published = DeliveryListingRequest.objects.filter(destination__type="local", publication_status="published")
    hidden = DeliveryTemplate.objects.annotate(
        _catalog_id=CatalogText(Replace(Cast("id", CharField()), Value("-"), Value("")))).filter(
            _catalog_id=CatalogText(OuterRef("app_id"))).exclude(
            id__in=published.values("version__template_id"))
    return query.alias(_delivery_hidden=Exists(hidden)).filter(_delivery_hidden=False)


def catalog_version_available(app_id, version):
    from console.models.delivery_template import DeliveryTemplateVersion, DeliveryListingRequest
    try:
        template_id = uuid.UUID(str(app_id))
    except (ValueError, TypeError):
        return True
    published = DeliveryListingRequest.objects.filter(destination__type="local", publication_status="published")
    return not DeliveryTemplateVersion.objects.filter(template_id=template_id, version=version).exclude(
        id__in=published.values("version_id")).exists()
