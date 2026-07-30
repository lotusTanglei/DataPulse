from hashlib import sha256

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from datapulse.query.models import ValidatedQuery


class QueryValidationError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


_forbidden_names = (
    "Alter",
    "Attach",
    "Call",
    "Command",
    "Commit",
    "Copy",
    "Create",
    "Delete",
    "Detach",
    "Drop",
    "Execute",
    "Grant",
    "Insert",
    "Into",
    "LoadData",
    "Lock",
    "Merge",
    "Pragma",
    "Rollback",
    "Set",
    "Transaction",
    "TruncateTable",
    "Update",
    "Use",
)
_forbidden_types = tuple(
    expression_type
    for name in _forbidden_names
    if (expression_type := getattr(exp, name, None)) is not None
)


def validate_read_only_sql(sql: str, dialect: str) -> ValidatedQuery:
    if not sql.strip():
        raise QueryValidationError("QUERY_SYNTAX_INVALID")
    try:
        statements = sqlglot.parse(sql, read=dialect)
    except (ParseError, ValueError) as error:
        raise QueryValidationError("QUERY_SYNTAX_INVALID") from error
    if len(statements) != 1:
        raise QueryValidationError("QUERY_MULTIPLE_STATEMENTS")
    statement = statements[0]
    if statement is None:
        raise QueryValidationError("QUERY_SYNTAX_INVALID")
    if not isinstance(statement, exp.Query):
        raise QueryValidationError("QUERY_NOT_READ_ONLY")
    if any(isinstance(node, _forbidden_types) for node in statement.walk()):
        raise QueryValidationError("QUERY_NOT_READ_ONLY")
    normalized = statement.sql(
        dialect=dialect,
        comments=False,
        normalize=True,
        pretty=False,
    )
    return ValidatedQuery(
        sql=sql,
        dialect=dialect,
        query_hash=sha256(normalized.encode()).hexdigest(),
    )
