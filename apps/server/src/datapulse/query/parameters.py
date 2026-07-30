import re

import sqlglot
from sqlglot import exp

from datapulse.query.models import ValidatedQuery

_valid_name = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_invalid_placeholder = re.compile(r"(?<!:):(?!:)([0-9][A-Za-z0-9_]*)")
_single_quoted = re.compile(r"'(?:''|[^'])*'")
_double_quoted = re.compile(r'"(?:""|[^"])*"')
_line_comment = re.compile(r"--[^\r\n]*")
_block_comment = re.compile(r"/\*.*?\*/", re.DOTALL)


class ParameterValidationError(ValueError):
    def __init__(self, code: str, names: set[str]) -> None:
        super().__init__(code)
        self.code = code
        self.field_errors = tuple({"field": name} for name in sorted(names))


def validate_parameters(
    query: ValidatedQuery,
    parameters: dict[str, object],
) -> None:
    sql_without_strings = _block_comment.sub(
        "",
        _line_comment.sub(
            "",
            _double_quoted.sub(
                "",
                _single_quoted.sub("", query.sql),
            ),
        ),
    )
    invalid_in_sql = set(_invalid_placeholder.findall(sql_without_strings))
    invalid_keys = {name for name in parameters if _valid_name.fullmatch(name) is None}
    invalid_names = invalid_in_sql | invalid_keys
    if invalid_names:
        raise ParameterValidationError(
            "QUERY_PARAMETER_NAME_INVALID",
            invalid_names,
        )

    statement = sqlglot.parse_one(query.sql, read=query.dialect)
    placeholders = tuple(node for node in statement.walk() if isinstance(node, exp.Placeholder))
    identifier_names = {
        str(node.this) for node in placeholders if isinstance(node.parent, (exp.Table, exp.Column))
    }
    if identifier_names:
        raise ParameterValidationError(
            "QUERY_PARAMETER_IDENTIFIER_INVALID",
            identifier_names,
        )

    required = {str(node.this) for node in placeholders}
    provided = set(parameters)
    missing = required - provided
    if missing:
        raise ParameterValidationError("QUERY_PARAMETERS_MISSING", missing)
    extra = provided - required
    if extra:
        raise ParameterValidationError("QUERY_PARAMETERS_EXTRA", extra)
