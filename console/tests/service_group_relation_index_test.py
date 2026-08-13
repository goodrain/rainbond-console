import importlib

import django
from django.apps import apps
from django.conf import settings
from django.db import connection


if not settings.configured:
    settings.configure(
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        INSTALLED_APPS=("www", ),
        SECRET_KEY="test-only",
    )
    django.setup()


from www.models.main import ServiceGroupRelation  # noqa: E402


INDEX_NAME = "service_group_rel_grp_svc_idx"
MIGRATION_MODULE = "console.schema_migrations.migrations.0001_service_group_relation_group_service_index"


def _index_columns():
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, ServiceGroupRelation._meta.db_table)
    return {name: constraint["columns"] for name, constraint in constraints.items() if constraint["index"]}


def _explain(queryset):
    sql, params = queryset.query.sql_with_params()
    with connection.cursor() as cursor:
        cursor.execute("EXPLAIN QUERY PLAN " + sql, params)
        return " ".join(str(value) for row in cursor.fetchall() for value in row)


def _reset_relation_table():
    with connection.schema_editor() as schema_editor:
        schema_editor.execute("DROP TABLE IF EXISTS service_group_relation")


def _restore_relation_table():
    _reset_relation_table()
    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(ServiceGroupRelation)


def test_migration_loads_and_model_queries_use_group_service_index():
    migration = importlib.import_module(MIGRATION_MODULE)
    _reset_relation_table()

    with connection.schema_editor() as schema_editor:
        schema_editor.execute(
            "CREATE TABLE service_group_relation ("
            "ID integer NOT NULL PRIMARY KEY AUTOINCREMENT, "
            "service_id varchar(32) NOT NULL, "
            "group_id integer NOT NULL, "
            "tenant_id varchar(32) NOT NULL, "
            "region_name varchar(64) NOT NULL"
            ")")
        schema_editor.execute("CREATE INDEX service_group_relation_service_idx ON service_group_relation (service_id)")
        migration.add_group_service_index(apps, schema_editor)
        migration.add_group_service_index(apps, schema_editor)

    try:
        assert _index_columns() == {
            "service_group_relation_service_idx": ["service_id"],
            INDEX_NAME: ["group_id", "service_id"],
        }
        assert [(index.name, index.fields) for index in ServiceGroupRelation._meta.indexes] == [
            (INDEX_NAME, ["group_id", "service_id"]),
        ]

        ServiceGroupRelation.objects.create(
            group_id=1,
            service_id="service-1",
            tenant_id="tenant-1",
            region_name="region-1",
        )

        combined_query = ServiceGroupRelation.objects.filter(group_id=1, service_id="service-1")
        group_query = ServiceGroupRelation.objects.filter(group_id=1)

        assert combined_query.get().tenant_id == "tenant-1"
        assert list(group_query.values_list("service_id", flat=True)) == ["service-1"]
        assert INDEX_NAME in _explain(combined_query)
        assert INDEX_NAME in _explain(group_query)
    finally:
        _restore_relation_table()


def test_migration_skips_an_equivalent_existing_composite_index():
    migration = importlib.import_module(MIGRATION_MODULE)
    _reset_relation_table()

    with connection.schema_editor() as schema_editor:
        schema_editor.execute(
            "CREATE TABLE service_group_relation ("
            "ID integer NOT NULL PRIMARY KEY AUTOINCREMENT, "
            "service_id varchar(32) NOT NULL, "
            "group_id integer NOT NULL, "
            "tenant_id varchar(32) NOT NULL, "
            "region_name varchar(64) NOT NULL"
            ")")
        schema_editor.execute(
            "CREATE INDEX equivalent_group_service_idx ON service_group_relation (group_id, service_id)")
        migration.add_group_service_index(apps, schema_editor)

    try:
        assert _index_columns() == {
            "equivalent_group_service_idx": ["group_id", "service_id"],
        }
    finally:
        _restore_relation_table()
