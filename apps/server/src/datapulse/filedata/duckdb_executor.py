import asyncio
import time
from pathlib import Path

import duckdb
from sqlglot import exp

from datapulse.query.models import QueryColumn, QueryResult
from datapulse.query.normalization import normalize_result_value
from datapulse.query.safety import QueryValidationError, validate_read_only_sql
from datapulse.settings import Settings

_FORBIDDEN_FUNCTIONS = {
    "glob",
    "read_blob",
    "read_csv",
    "read_csv_auto",
    "read_json",
    "read_json_auto",
    "read_parquet",
}


class FileQueryExecutionError(RuntimeError):
    def __init__(self, code: str, status_code: int, request_id: str) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code
        self.request_id = request_id


def _validate_file_query_sql(sql: str) -> str:
    validated = validate_read_only_sql(sql, "duckdb")
    statement = __import__("sqlglot").parse_one(sql, read="duckdb")
    if any(
        isinstance(node, exp.Anonymous) and node.name.lower() in _FORBIDDEN_FUNCTIONS
        for node in statement.walk()
    ):
        raise QueryValidationError("FILE_QUERY_INVALID")
    return validated.sql


class DuckDBExecutor:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.timeout_seconds = settings.duckdb_timeout_seconds

    def _validated_source_path(self, source_path: Path) -> Path:
        resolved = source_path.resolve(strict=True)
        files_dir = self._settings.resolved_files_dir()
        if (
            not resolved.is_file()
            or source_path.is_symlink()
            or not resolved.is_relative_to(files_dir)
        ):
            raise FileQueryExecutionError("FILE_NOT_FOUND", 404, "")
        return resolved

    def _dataset_source_sql(self, source_path: Path) -> str:
        suffix = source_path.suffix.lower()
        escaped = str(source_path).replace("'", "''")
        if suffix == ".csv":
            return f"read_csv_auto('{escaped}', header=true)"
        if suffix == ".json":
            return f"read_json_auto('{escaped}')"
        if suffix == ".parquet":
            return f"read_parquet('{escaped}')"
        raise FileQueryExecutionError("FILE_QUERY_INVALID", 422, "")

    def _execute_sync(
        self,
        sql: str,
        parameters,
        *,
        source_path: Path,
        max_rows: int,
    ) -> tuple[tuple[QueryColumn, ...], tuple[tuple[object, ...], ...], bool]:
        connection = duckdb.connect(":memory:")
        try:
            connection.execute(f"SET threads = {self._settings.duckdb_threads}")
            connection.execute(f"SET memory_limit = '{self._settings.duckdb_memory_limit}'")
            source_sql = self._dataset_source_sql(source_path)
            connection.execute(f"CREATE VIEW dataset_source AS SELECT * FROM {source_sql}")
            cursor = connection.execute(sql, parameters)
            fetched = cursor.fetchmany(max_rows + 1)
            truncated = len(fetched) > max_rows
            rows = tuple(
                tuple(normalize_result_value(value) for value in row) for row in fetched[:max_rows]
            )
            description = cursor.description or []
            columns = tuple(
                QueryColumn(name=column[0], data_type=str(column[1]).lower())
                for column in description
            )
            return columns, rows, truncated
        finally:
            connection.close()

    async def execute(
        self,
        sql: str,
        parameters,
        *,
        source_path: Path,
        request_id: str,
        timeout_seconds: float,
        max_rows: int,
    ) -> QueryResult:
        start = time.perf_counter()
        try:
            validated_sql = _validate_file_query_sql(sql)
        except QueryValidationError as error:
            code = error.code if error.code == "FILE_QUERY_INVALID" else "FILE_QUERY_INVALID"
            raise FileQueryExecutionError(code, 422, request_id) from error

        try:
            validated_source_path = self._validated_source_path(source_path)
        except FileQueryExecutionError as error:
            raise FileQueryExecutionError(error.code, error.status_code, request_id) from error

        try:
            async with asyncio.timeout(timeout_seconds):
                columns, rows, truncated = await asyncio.to_thread(
                    self._execute_sync,
                    validated_sql,
                    parameters,
                    source_path=validated_source_path,
                    max_rows=max_rows,
                )
        except TimeoutError as error:
            raise FileQueryExecutionError("FILE_QUERY_TIMEOUT", 504, request_id) from error
        except FileQueryExecutionError:
            raise
        except Exception as error:
            raise FileQueryExecutionError("FILE_QUERY_FAILED", 502, request_id) from error

        return QueryResult(
            request_id=request_id,
            columns=columns,
            rows=rows,
            row_count=len(rows),
            truncated=truncated,
            duration_ms=max(0, round((time.perf_counter() - start) * 1000)),
        )
