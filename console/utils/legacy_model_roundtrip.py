"""Preserve live schema across startup-generated remove/recreate histories.

Only operations with the same initial and final database shape are eligible.
The regular migration executor still applies every state change, dependency and
unrelated operation. No migration is fake-applied and no data is copied away.
"""
import ast
import importlib
import os
import re
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from django.core.management.base import CommandError
from django.db import migrations
from django.db.models import UniqueConstraint
from django.db.migrations.executor import MigrationExecutor


def _field_shape(field):
    _, path, args, kwargs = field.deconstruct()
    kwargs = {
        key: value
        for key, value in kwargs.items() if key not in ("help_text", "verbose_name", "choices", "blank", "validators")
    }
    return path, args, kwargs


def _model_shape(model):
    return ({
        name: _field_shape(field)
        for name, field in model.fields.items()
    }, {
        key: value
        for key, value in model.options.items()
        if key not in ("verbose_name", "verbose_name_plural", "ordering", "permissions", "default_permissions")
    })


def _type(value):
    value = re.sub(r"\s+", " ", str(value).strip().lower())
    value = value.replace(" auto_increment", "")
    if value in ("bool", "boolean", "tinyint(1)"):
        return "bool"
    value = re.sub(r"\b(integer|int)(?:\(\d+\))?", "int", value)
    value = re.sub(r"\b(bigint|smallint|tinyint)\(\d+\)", r"\1", value)
    return value


def _verify_columns(connection, model, fields=None):
    table = model._meta.db_table
    if model._meta.local_many_to_many:
        raise CommandError("Cannot reconcile model with implicit many-to-many storage: {}".format(table))
    with connection.cursor() as cursor:
        columns = {column.name: column for column in connection.introspection.get_table_description(cursor, table)}
        constraints = connection.introspection.get_constraints(cursor, table)
        if connection.vendor == "mysql":
            cursor.execute(
                "SELECT COLUMN_NAME, COLUMN_TYPE FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s", [table])
            types = dict(cursor.fetchall())
        else:
            types = {name: column.type_code for name, column in columns.items()}
    for field in fields or model._meta.local_fields:
        column = columns.get(field.column)
        if column is None or bool(column.null_ok) != field.null or _type(types.get(field.column)) != _type(
                field.db_type(connection)):
            raise CommandError("Live column differs from preserved migration shape: {}.{} ({} versus {})".format(
                table, field.column, types.get(field.column), field.db_type(connection)))
        if field.primary_key and not any(
                c.get("primary_key") and c.get("columns") == [field.column] for c in constraints.values()):
            raise CommandError("Live primary key differs: {}.{}".format(table, field.column))
    return constraints


def _verify_model(connection, model):
    constraints = _verify_columns(connection, model)
    unique_sets = [
        set(item.get("columns") or []) for item in constraints.values() if item.get("unique") or item.get("primary_key")
    ]
    for field in model._meta.local_fields:
        if field.unique and {field.column} not in unique_sets:
            raise CommandError("Live unique field differs: {}.{}".format(model._meta.db_table, field.column))
        if field.is_relation and field.db_constraint:
            expected = (field.target_field.model._meta.db_table, field.target_field.column)
            if not any(
                    item.get("columns") == [field.column] and item.get("foreign_key") == expected
                    for item in constraints.values()):
                raise CommandError("Live foreign key differs: {}.{}".format(model._meta.db_table, field.column))
    groups = list(model._meta.unique_together)
    for constraint in model._meta.constraints:
        if not isinstance(constraint, UniqueConstraint) or not constraint.fields or constraint.condition:
            raise CommandError("Cannot verify preserved database constraint: {}".format(constraint.name))
        groups.append(constraint.fields)
    for group in groups:
        columns = {model._meta.get_field(name).column for name in group}
        if columns not in unique_sets:
            raise CommandError("Live unique constraint differs: {}".format(model._meta.db_table))


def _rewrite(migration, indexes, dry_run):
    module = sys.modules.get(type(migration).__module__)
    path = Path(getattr(module, "__file__", ""))
    if path.suffix != ".py" or path.stem != migration.name or path.is_symlink():
        raise CommandError("Cannot locate generated migration source: {}".format(migration.name))
    source = path.read_bytes()
    tree = ast.parse(source, filename=str(path))
    operations = [
        assignment.value for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Migration"
        for assignment in node.body if isinstance(assignment, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "operations" for target in assignment.targets)
    ]
    if len(operations) != 1 or not isinstance(operations[0], ast.List) or len(operations[0].elts) != len(migration.operations):
        raise CommandError("Cannot identify generated operation list: {}".format(migration.name))
    lines = source.splitlines(keepends=True)
    edits = []
    for index in indexes:
        node = operations[0].elts[index]
        if (not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute)
                or not isinstance(node.func.value, ast.Name) or node.func.value.id != "migrations"
                or node.func.attr != migration.operations[index].__class__.__name__):
            raise CommandError("Migration source and loaded operation differ: {}".format(migration.name))
        start = sum(map(len, lines[:node.lineno - 1])) + node.col_offset
        end = sum(map(len, lines[:node.end_lineno - 1])) + node.end_col_offset
        edits.append((start, end, b"migrations.SeparateDatabaseAndState(state_operations=[" + source[start:end] + b"])"))
    for start, end, replacement in sorted(edits, reverse=True):
        source = source[:start] + replacement + source[end:]
    ast.parse(source, filename=str(path))
    if dry_run:
        return
    backup = path.with_suffix(".py.before-schema-repair")
    if not backup.exists():
        with backup.open("xb") as stream:
            stream.write(path.read_bytes())
    temporary = None
    try:
        with NamedTemporaryFile(dir=str(path.parent), prefix=".schema-repair-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(source)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(path.stat().st_mode & 0o777)
        os.replace(str(temporary), str(path))
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    for index in indexes:
        migration.operations[index] = migrations.SeparateDatabaseAndState(state_operations=[migration.operations[index]])
    module.Migration.operations = migration.operations
    importlib.invalidate_caches()


def repair_generated_model_roundtrips(connection, app_labels, dry_run=False):
    executor = MigrationExecutor(connection)
    plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
    if any(backwards for _, backwards in plan):
        raise CommandError("Schema reconciliation cannot execute backwards migrations")
    initial = executor._create_project_state(with_applied_migrations=True)
    final = initial.clone()
    records = []
    for migration, _ in plan:
        for index, operation in enumerate(migration.operations):
            records.append((migration, index, operation))
            operation.state_forwards(migration.app_label, final)
    tables = set(connection.introspection.table_names())
    removed_models = {(m.app_label, op.name.lower()) for m, _, op in records if isinstance(op, migrations.DeleteModel)}
    removed_fields = {(m.app_label, op.model_name.lower(), op.name)
                      for m, _, op in records if isinstance(op, migrations.RemoveField)}
    restored_models = set()
    restored_fields = set()
    for key in removed_models:
        if key[0] not in app_labels or key not in initial.models or key not in final.models:
            continue
        model = final.apps.get_model(*key)
        if model._meta.db_table not in tables:
            continue
        if _model_shape(initial.models[key]) != _model_shape(final.models[key]):
            raise CommandError("Removed/recreated model has a different final shape: {}.{}".format(*key))
        _verify_model(connection, model)
        restored_models.add(key)
    for app_label, model_name, field_name in removed_fields:
        key = app_label, model_name
        if app_label not in app_labels or key not in initial.models or key not in final.models:
            continue
        before = initial.models[key].fields.get(field_name)
        after = final.models[key].fields.get(field_name)
        if before is None or after is None:
            continue
        model = final.apps.get_model(*key)
        if model._meta.db_table not in tables:
            continue
        if _field_shape(before) != _field_shape(after):
            raise CommandError("Removed/recreated field has a different final shape: {}.{}".format(model_name, field_name))
        _verify_columns(connection, model, [model._meta.get_field(field_name)])
        restored_fields.add((app_label, model_name, field_name))
    selected = {}
    model_operations = (migrations.CreateModel, migrations.DeleteModel, migrations.AddField, migrations.RemoveField,
                        migrations.AlterField, migrations.AddConstraint, migrations.RemoveConstraint)
    for migration, index, operation in records:
        key = migration.app_label, getattr(operation, "model_name", getattr(operation, "name", "")).lower()
        include = key in restored_models and isinstance(operation, model_operations)
        if isinstance(operation, (migrations.AddField, migrations.RemoveField, migrations.AlterField)):
            include |= (*key, operation.name) in restored_fields
            # Transient changes to an unchanged field, such as global OAuth
            # name uniqueness followed by the original ownership scope.
            if not include and key in initial.models and key in final.models and key[0] in app_labels:
                before = initial.models[key].fields.get(operation.name)
                after = final.models[key].fields.get(operation.name)
                if isinstance(operation,
                              migrations.AlterField) and before and after and _field_shape(before) == _field_shape(after):
                    model = final.apps.get_model(*key)
                    if model._meta.db_table in tables:
                        _verify_columns(connection, model, [model._meta.get_field(operation.name)])
                        include = True
        constraint_operation = isinstance(operation, (migrations.RemoveConstraint, migrations.AddConstraint))
        if constraint_operation and key in initial.models and key in final.models:
            name = operation.name if isinstance(operation, migrations.RemoveConstraint) else operation.constraint.name
            before = {c.name: c for c in initial.models[key].options.get("constraints", [])}.get(name)
            after = {c.name: c for c in final.models[key].options.get("constraints", [])}.get(name)
            if key[0] in app_labels and before and after and before.deconstruct() == after.deconstruct():
                model = final.apps.get_model(*key)
                if model._meta.db_table in tables:
                    constraints = _verify_columns(connection, model)
                    actual = constraints.get(name, {})
                    if actual.get("unique") and actual.get("columns") == list(after.fields):
                        include = True
        if include:
            selected.setdefault(migration, []).append(index)
    # Validate every planned source edit before modifying any file.
    for migration, indexes in selected.items():
        _rewrite(migration, indexes, dry_run=True)
    if not dry_run:
        for migration, indexes in selected.items():
            _rewrite(migration, indexes, dry_run=False)
    return ["{}.{}".format(m.app_label, m.name) for m in selected]
