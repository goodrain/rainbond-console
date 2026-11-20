"""Preserve known historical data when startup retires its Django model state.

This does not recover previously dropped columns or fake a migration. Incomplete
historical schemas require backup recovery before the normal migrate command.
"""
import ast
import importlib
import os
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from django.core.management.base import CommandError
from django.db import migrations, models
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.writer import MigrationWriter

from console.utils.legacy_model_roundtrip import _field_shape


HISTORICAL_MODELS = {
    "deliverylistingrequest": "delivery_listing_request",
    "deliverytask": "delivery_task",
    "deliverytaskitem": "delivery_task_item",
    "deliverytemplate": "delivery_template",
    "deliverytemplateversion": "delivery_template_version",
    "teamapplication": "team_creation_application",
}
HISTORICAL_FIELDS = {
    ("deliverylistingrequest", "publication_task"),
    ("deliverylistingrequest", "version"),
    ("deliverytask", "template"),
    ("deliverytask", "version"),
    ("deliverytaskitem", "task"),
    ("deliverytemplateversion", "template"),
    ("servicerecyclebin", "recovery_metadata"),
}
HISTORICAL_FIELD_TABLES = {"servicerecyclebin": "tenant_service_recycle_bin", **HISTORICAL_MODELS}


def _retired_operation(operation, state):
    if isinstance(operation, migrations.DeleteModel) and operation.name_lower in HISTORICAL_MODELS:
        name = operation.name_lower
        table = HISTORICAL_MODELS[name]
    elif isinstance(operation, migrations.RemoveField) and (operation.model_name_lower, operation.name) in HISTORICAL_FIELDS:
        name = operation.model_name_lower
        table = HISTORICAL_FIELD_TABLES[name]
    elif (isinstance(operation, migrations.AlterField) and operation.model_name_lower == "rainbondcenterappversion"
          and operation.name == "app_version_info" and operation.field.get_internal_type() == "CharField"
          and operation.field.max_length == 255):
        name = operation.model_name_lower
        table = "rainbond_center_app_version"
        if state.models["console", name].get_field(operation.name).get_internal_type() != "TextField":
            return None
    else:
        return None
    model = state.apps.get_model("console", name)
    if model._meta.db_table != table:
        raise CommandError("Historical model table does not match the preservation contract: {}".format(name))
    return model


def _validate_historical_schema(connection, model, operation, tables):
    table = model._meta.db_table

    def incomplete(detail):
        raise CommandError("Backup restore required for {}: {}; no migration or database changes made".format(table, detail))

    if table not in tables:
        incomplete("historical table is missing")
    fields = (model._meta.local_concrete_fields if isinstance(operation, migrations.DeleteModel)
              else [model._meta.get_field(operation.name)])
    with connection.cursor() as cursor:
        columns = {column.name: column for column in connection.introspection.get_table_description(cursor, table)}
        constraints = connection.introspection.get_constraints(cursor, table)
    for field in fields:
        column = columns.get(field.column)
        if column is None:
            incomplete("column {} is missing".format(field.column))
        if not field.primary_key and column.null_ok != field.null:
            incomplete("column {} has incompatible nullability".format(field.column))
        if (isinstance(operation, migrations.AlterField)
                and connection.introspection.get_field_type(column.type_code, column) != "TextField"):
            incomplete("column {} is no longer the historical text type".format(field.column))
        if field.is_relation and getattr(field, "db_constraint", False):
            target = (field.target_field.model._meta.db_table, field.target_field.column)
            if not any(value.get("foreign_key") == target and value.get("columns") == [field.column]
                       for value in constraints.values()):
                incomplete("foreign key on {} is missing or incompatible".format(field.column))
    if isinstance(operation, migrations.RemoveField):
        unique_groups = list(model._meta.unique_together)
        unique_groups.extend(constraint.fields for constraint in model._meta.constraints
                             if isinstance(constraint, models.UniqueConstraint) and constraint.fields)
        for unique_fields in unique_groups:
            if operation.name not in unique_fields:
                continue
            unique_columns = [model._meta.get_field(name).column for name in unique_fields]
            if not any(value.get("unique") and value.get("columns") == unique_columns for value in constraints.values()):
                incomplete("historical composite uniqueness is missing")


def _state_only_operation(operation):
    if (isinstance(operation, migrations.SeparateDatabaseAndState) and not operation.database_operations
            and len(operation.state_operations) == 1):
        return operation.state_operations[0]
    return operation


def _rewrite_operations(migration, indices, dry_run):
    module = sys.modules.get(type(migration).__module__)
    filename = getattr(module, "__file__", None)
    if not filename:
        raise CommandError("Cannot locate historical migration source: {}".format(migration.name))
    path = Path(filename)
    if path.suffix != ".py" or path.stem != migration.name or path.is_symlink():
        raise CommandError("Cannot safely rewrite historical migration: {}".format(migration.name))
    source = path.read_bytes()
    tree = ast.parse(source, filename=str(path))
    expressions = [assignment.value for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Migration"
                   for assignment in node.body if isinstance(assignment, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == "operations" for target in assignment.targets)]
    if (len(expressions) != 1 or not isinstance(expressions[0], ast.List)
            or len(expressions[0].elts) != len(migration.operations)):
        raise CommandError("Cannot identify historical migration operations: {}".format(migration.name))
    lines = source.splitlines(keepends=True)
    edits = []
    for index in indices:
        node = expressions[0].elts[index]
        expected = ast.parse(MigrationWriter.serialize(migration.operations[index])[0], mode="eval").body
        if ast.dump(node) != ast.dump(expected):
            raise CommandError("Historical migration source differs from its loaded operation: {}".format(migration.name))
        start = sum(len(line) for line in lines[:node.lineno - 1]) + node.col_offset
        end = sum(len(line) for line in lines[:node.end_lineno - 1]) + node.end_col_offset
        edits.append((start, end, b"migrations.SeparateDatabaseAndState(state_operations=[\n" + source[start:end] + b"\n])"))
    repaired = source
    for start, end, replacement in reversed(edits):
        repaired = repaired[:start] + replacement + repaired[end:]
    ast.parse(repaired, filename=str(path))
    if dry_run:
        return
    temporary = None
    try:
        with NamedTemporaryFile(dir=str(path.parent), prefix=".legacy-retirement-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(repaired)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(path.stat().st_mode & 0o777)
        if path.read_bytes() != source:
            raise CommandError("Historical migration changed during preservation; retry inspection")
        os.replace(str(temporary), str(path))
    except OSError as error:
        raise CommandError("Cannot write preserved historical migration: {}".format(migration.name)) from error
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    updated = list(migration.operations)
    for index in indices:
        updated[index] = migrations.SeparateDatabaseAndState(state_operations=[updated[index]])
    migration.operations = updated
    module.Migration.operations = updated
    importlib.invalidate_caches()


def _recreated_in_final_state(operation, initial, final):
    name = getattr(operation, "model_name_lower", getattr(operation, "name_lower", ""))
    key = "console", name
    if key not in initial.models or key not in final.models:
        return False
    if isinstance(operation, migrations.DeleteModel):
        return True
    before = initial.models[key].fields.get(operation.name)
    after = final.models[key].fields.get(operation.name)
    return before is not None and after is not None and _field_shape(before) == _field_shape(after)


def preserve_legacy_retirements(connection, dry_run=False):
    """Validate first, then preserve only the known historical retirement DDL.

    Applied migrations remain untouched. A blank installation retains its normal
    dependency sequence. Existing history with pending prerequisite migrations
    needs explicit inspection rather than guessing which SQL has already run.
    """
    executor = MigrationExecutor(connection)
    loader = executor.loader
    initial = executor._create_project_state(with_applied_migrations=True)
    final = loader.project_state()
    tables = set(connection.introspection.table_names())
    historical_tables = set(HISTORICAL_MODELS.values()) | {"tenant_service_recycle_bin", "rainbond_center_app_version"}
    fresh_history = not any(key[0] == "console" for key in loader.applied_migrations) and not tables.intersection(
        historical_tables)
    plans = []
    for key, migration in sorted(loader.disk_migrations.items()):
        if key[0] != "console" or key in loader.applied_migrations:
            continue
        state = loader.project_state(key, at_end=False)
        parents_applied = all(parent.key in loader.applied_migrations for parent in loader.graph.node_map[key].parents)
        indices = []
        for index, outer in enumerate(migration.operations):
            operation = _state_only_operation(outer)
            model = _retired_operation(operation, state)
            if model is not None:
                if _recreated_in_final_state(operation, initial, final):
                    # Roundtrip reconciliation owns remove/recreate SQL. Still
                    # reject missing live columns/FKs before any startup writes.
                    original = initial.apps.get_model("console", model._meta.model_name)
                    _validate_historical_schema(connection, original, operation, tables)
                    outer.state_forwards("console", state)
                    continue
                if not parents_applied:
                    if not fresh_history:
                        raise CommandError("Historical preservation requires applied dependencies: {}".format(migration.name))
                    if outer is operation:
                        indices.append(index)
                else:
                    _validate_historical_schema(connection, model, operation, tables)
                    if outer is operation:
                        indices.append(index)
            outer.state_forwards("console", state)
        if indices:
            plans.append((migration, indices))
    # No schema editor or recorder is used here. Validate every candidate before
    # writing a file or allowing startup's existing initial/OAuth repairs to run.
    for migration, indices in plans:
        _rewrite_operations(migration, indices, dry_run)
    return bool(plans)
