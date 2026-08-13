from django.db import migrations, models


INDEX_NAME = "service_group_rel_grp_svc_idx"
INDEX_FIELDS = ["group_id", "service_id"]


def add_group_service_index(apps, schema_editor):
    from www.models.main import ServiceGroupRelation

    table_name = ServiceGroupRelation._meta.db_table

    if table_name not in schema_editor.connection.introspection.table_names():
        return

    with schema_editor.connection.cursor() as cursor:
        constraints = schema_editor.connection.introspection.get_constraints(cursor, table_name)

    if any(constraint.get("columns") == INDEX_FIELDS for constraint in constraints.values()):
        return

    schema_editor.add_index(
        ServiceGroupRelation,
        models.Index(fields=INDEX_FIELDS, name=INDEX_NAME),
    )


def remove_group_service_index(apps, schema_editor):
    from www.models.main import ServiceGroupRelation

    table_name = ServiceGroupRelation._meta.db_table

    if table_name not in schema_editor.connection.introspection.table_names():
        return

    with schema_editor.connection.cursor() as cursor:
        constraints = schema_editor.connection.introspection.get_constraints(cursor, table_name)

    if INDEX_NAME not in constraints:
        return

    schema_editor.remove_index(
        ServiceGroupRelation,
        models.Index(fields=INDEX_FIELDS, name=INDEX_NAME),
    )


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.RunPython(add_group_service_index, remove_group_service_index),
    ]
