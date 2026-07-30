import pytest

from datapulse.query.safety import QueryValidationError, validate_read_only_sql

DIALECTS = ("sqlite", "postgres", "mysql")
READ_ONLY_STATEMENTS = (
    "SELECT month, amount FROM sales",
    ("WITH totals AS (SELECT SUM(amount) AS value FROM sales) SELECT value FROM totals"),
    "SELECT id FROM current_sales UNION ALL SELECT id FROM archived_sales",
)
DANGEROUS_STATEMENTS = (
    "INSERT INTO sales VALUES (1)",
    "UPDATE sales SET amount = 0",
    "DELETE FROM sales",
    "CREATE TABLE leaked(id INT)",
    "DROP TABLE sales",
    "ALTER TABLE sales ADD COLUMN leaked INT",
    "TRUNCATE TABLE sales",
    "ATTACH DATABASE '/tmp/secret.db' AS secret",
    "PRAGMA writable_schema = 1",
    "CALL dangerous_proc()",
    "SELECT * FROM sales FOR UPDATE",
    "COPY sales TO '/tmp/sales.csv'",
    "WITH changed AS (DELETE FROM sales RETURNING id) SELECT id FROM changed",
    "WITH changed AS (UPDATE sales SET amount = 0 RETURNING id) SELECT id FROM changed",
)


@pytest.mark.parametrize("dialect", DIALECTS)
@pytest.mark.parametrize("sql", READ_ONLY_STATEMENTS)
def test_read_only_queries_are_accepted(sql: str, dialect: str) -> None:
    validated = validate_read_only_sql(sql, dialect)

    assert validated.sql == sql
    assert validated.dialect == dialect
    assert len(validated.query_hash) == 64


@pytest.mark.parametrize("dialect", DIALECTS)
@pytest.mark.parametrize("sql", DANGEROUS_STATEMENTS)
def test_mutating_or_command_statements_are_rejected(sql: str, dialect: str) -> None:
    with pytest.raises(QueryValidationError) as captured:
        validate_read_only_sql(sql, dialect)

    assert captured.value.code in {"QUERY_NOT_READ_ONLY", "QUERY_SYNTAX_INVALID"}


@pytest.mark.parametrize(
    ("sql", "expected_code"),
    [
        ("", "QUERY_SYNTAX_INVALID"),
        ("SELECT 1; SELECT 2", "QUERY_MULTIPLE_STATEMENTS"),
        ("SELECT FROM", "QUERY_SYNTAX_INVALID"),
    ],
)
def test_invalid_statement_shapes_use_stable_codes(
    sql: str,
    expected_code: str,
) -> None:
    with pytest.raises(QueryValidationError) as captured:
        validate_read_only_sql(sql, "sqlite")

    assert captured.value.code == expected_code


def test_query_hash_is_normalized_without_changing_execution_sql() -> None:
    first = validate_read_only_sql("SELECT amount FROM sales", "sqlite")
    second = validate_read_only_sql(
        " select amount  from sales -- diagnostic comment",
        "sqlite",
    )

    assert first.query_hash == second.query_hash
    assert second.sql == " select amount  from sales -- diagnostic comment"
