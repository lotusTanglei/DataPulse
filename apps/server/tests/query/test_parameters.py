import pytest

from datapulse.query.models import ValidatedQuery
from datapulse.query.parameters import ParameterValidationError, validate_parameters
from datapulse.query.safety import validate_read_only_sql


def test_named_parameters_accept_repeated_names_and_postgres_casts() -> None:
    query = validate_read_only_sql(
        (
            "SELECT * FROM sales "
            "WHERE year = :year AND prior_year = :year "
            "AND created_at::date >= :start_date"
        ),
        "postgres",
    )

    validate_parameters(query, {"year": 2026, "start_date": "2026-01-01"})


@pytest.mark.parametrize(
    ("parameters", "expected_code", "expected_names"),
    [
        (
            {"year": 2026},
            "QUERY_PARAMETERS_MISSING",
            {"region"},
        ),
        (
            {"year": 2026, "region": "north", "unused": "do-not-leak"},
            "QUERY_PARAMETERS_EXTRA",
            {"unused"},
        ),
    ],
)
def test_missing_and_extra_parameters_report_names_not_values(
    parameters: dict[str, object],
    expected_code: str,
    expected_names: set[str],
) -> None:
    query = validate_read_only_sql(
        "SELECT * FROM sales WHERE year = :year AND region = :region",
        "postgres",
    )

    with pytest.raises(ParameterValidationError) as captured:
        validate_parameters(query, parameters)

    assert captured.value.code == expected_code
    assert {error["field"] for error in captured.value.field_errors} == expected_names
    assert "do-not-leak" not in str(captured.value)


def test_invalid_parameter_names_are_rejected() -> None:
    query = ValidatedQuery(
        sql="SELECT * FROM sales WHERE year = :1year",
        dialect="postgres",
        query_hash="0" * 64,
    )

    with pytest.raises(ParameterValidationError) as captured:
        validate_parameters(query, {"1year": 2026})

    assert captured.value.code == "QUERY_PARAMETER_NAME_INVALID"
    assert captured.value.field_errors == ({"field": "1year"},)


def test_identifier_substitution_is_rejected() -> None:
    query = ValidatedQuery(
        sql="SELECT * FROM :table",
        dialect="postgres",
        query_hash="0" * 64,
    )

    with pytest.raises(ParameterValidationError) as captured:
        validate_parameters(query, {"table": "sales"})

    assert captured.value.code == "QUERY_PARAMETER_IDENTIFIER_INVALID"
    assert captured.value.field_errors == ({"field": "table"},)


def test_parameter_like_text_inside_comments_is_ignored() -> None:
    query = validate_read_only_sql(
        """
        SELECT amount
        FROM sales
        -- example invalid placeholder: :1year
        /* another example: :2region */
        """,
        "postgres",
    )

    validate_parameters(query, {})
