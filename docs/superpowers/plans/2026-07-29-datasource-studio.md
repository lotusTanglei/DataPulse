# DataPulse Datasource Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the authenticated DataPulse Studio vertical slice in which one administrator can configure SQLite, PostgreSQL, and MySQL/MariaDB data sources, browse schemas, execute constrained read-only SQL, preview results, and save datasets.

**Architecture:** Keep one FastAPI process and one Vue SPA, but isolate metadata, authentication, datasource, query, and dataset modules behind explicit interfaces. SQLAlchemy 2 manages the DataPulse SQLite metadata database and native async database engines; SQLGlot validates user SQL before connector execution. The browser uses server-side sessions and CSRF cookies, and the Studio follows the approved Notion-style design system.

**Tech Stack:** Python 3.13/3.14, FastAPI, Pydantic 2, SQLAlchemy 2 async, Alembic, aiosqlite, asyncpg, asyncmy, SQLGlot, cryptography AES-GCM, pwdlib Argon2, pytest; Vue 3, TypeScript, Vue Router, Pinia, CodeMirror 6, TanStack Virtual, Vitest, Playwright; SQLite, PostgreSQL, MariaDB, Docker Compose.

## Global Constraints

- Implement against `docs/superpowers/specs/2026-07-29-datasource-studio-design.md`.
- Start the execution branch `codex/datasource-studio` from `codex/foundation-contracts`; do not implement on `main`.
- Keep Python `>=3.13,<3.15`; Python 3.13 is the locked container baseline and Python 3.14 is a compatibility gate.
- Keep Node 22 and pnpm 10.33.0.
- DataPulse metadata defaults to `/data/datapulse.db`; external SQLite files must resolve under `/data/sources`.
- Use native async drivers: aiosqlite, asyncpg, and asyncmy. Do not add DuckDB in this plan.
- Keep exactly one administrator account. Do not add registration, multiple users, RBAC, OIDC, or collaboration.
- Store administrator passwords only as Argon2id hashes.
- Encrypt external database passwords with AES-256-GCM and a URL-safe Base64 32-byte `DATAPULSE_MASTER_KEY`.
- Only read-only, single-statement SQL may reach a connector. Bind values through named parameters; never interpolate values or identifiers.
- Default query timeout is 30 seconds, maximum timeout is 300 seconds, default row limit is 1,000, and absolute row limit is 5,000.
- Allow at most four concurrent queries globally and two per data source.
- Do not persist full query results, plaintext SQL, database passwords, or parameter values in QueryRun.
- Keep the approved Notion visual direction: `#FFFFFF`, `#F7F7F5`, `#37352F`, `#787774`, `#E9E9E7`; no gradients or dashboard-card decoration.
- Use test-driven development for every behavior change: verify the intended failure before writing implementation.
- Keep generated JSON Schema and TypeScript declarations deterministic and drift-free.
- Commit after every task only after its focused tests and static checks pass.

---

### Task 1: Metadata Database, ORM Models, and Alembic

**Files:**
- Modify: `apps/server/pyproject.toml`
- Modify: `apps/server/src/datapulse/settings.py`
- Create: `apps/server/src/datapulse/metadata/__init__.py`
- Create: `apps/server/src/datapulse/metadata/base.py`
- Create: `apps/server/src/datapulse/metadata/database.py`
- Create: `apps/server/src/datapulse/metadata/models.py`
- Create: `apps/server/alembic.ini`
- Create: `apps/server/migrations/env.py`
- Create: `apps/server/migrations/script.py.mako`
- Create: `apps/server/migrations/versions/0001_datasource_studio.py`
- Create: `apps/server/tests/metadata/test_database.py`
- Create: `apps/server/tests/metadata/test_migrations.py`
- Modify: `uv.lock`

**Interfaces:**
- Produces: `Base: DeclarativeBase`
- Produces: `create_metadata_engine(settings: Settings) -> AsyncEngine`
- Produces: `create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]`
- Produces: `metadata_database_url(settings: Settings) -> str`
- Produces ORM models `SystemState`, `AdminAccount`, `AdminSession`, `DataSourceRecord`, `DatasetRecord`, and `QueryRunRecord`

- [ ] **Step 1: Write failing settings and database tests**

Create tests that prove the default database is inside a temporary data directory and that sessions commit and read records:

```python
async def test_metadata_database_defaults_to_data_dir(tmp_path: Path) -> None:
    settings = Settings(environment="test", data_dir=tmp_path)
    assert metadata_database_url(settings) == (
        f"sqlite+aiosqlite:///{(tmp_path / 'datapulse.db').resolve()}"
    )


async def test_session_factory_persists_system_state(tmp_path: Path) -> None:
    settings = Settings(environment="test", data_dir=tmp_path)
    engine = create_metadata_engine(settings)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = create_session_factory(engine)
    async with factory() as session:
        session.add(SystemState(id=1))
        await session.commit()
    async with factory() as session:
        assert await session.get(SystemState, 1) is not None
    await engine.dispose()
```

Use `pytest.mark.anyio` and force the asyncio backend in a shared test fixture.

- [ ] **Step 2: Run the focused tests and verify the intended failure**

Run:

```bash
uv run --package datapulse-server pytest apps/server/tests/metadata/test_database.py -v
```

Expected: FAIL during collection because `datapulse.metadata` does not exist.

- [ ] **Step 3: Add runtime dependencies and database settings**

Add with uv so `uv.lock` remains authoritative:

```bash
uv add --package datapulse-server "sqlalchemy[asyncio]>=2,<3" "alembic>=1,<2" "aiosqlite>=0.20,<1"
```

Extend `Settings`:

```python
data_dir: Path = Path("data")
sources_dir: Path | None = None
database_url: str | None = None
```

`metadata_database_url()` must use `database_url` when provided and otherwise create an absolute SQLite URL under `data_dir`. Add `resolved_sources_dir()` returning the configured directory or `data_dir / "sources"`.

- [ ] **Step 4: Implement the ORM base and all six tables**

Use timezone-aware UTC timestamps and string UUID primary keys. Match the approved spec exactly:

```python
class QueryRunStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"
```

`SystemState` stores nullable `setup_code_hash` and `setup_code_expires_at`. Add unique constraints for `AdminAccount.username` and `DataSourceRecord.name`, foreign keys from datasets and query runs, and `ondelete="RESTRICT"` for datasets referencing data sources.

- [ ] **Step 5: Create the initial Alembic migration**

Configure Alembic to import `Base.metadata`. `env.py` must translate the async application URL to a synchronous migration URL (`sqlite+aiosqlite` → `sqlite`, `postgresql+asyncpg` → `postgresql`, `mysql+asyncmy` → `mysql`) and support `DATAPULSE_DATABASE_URL`.

The hand-written `0001_datasource_studio.py` migration creates the six tables and indexes; its downgrade drops them in reverse foreign-key order.

- [ ] **Step 6: Add and run a migration test**

The test invokes Alembic against a temporary SQLite URL:

```python
def test_upgrade_head_creates_expected_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "migration.db"
    run_alembic_upgrade(database_path)
    names = inspect_sqlite_tables(database_path)
    assert {
        "system_state",
        "admin_account",
        "admin_session",
        "data_source",
        "dataset",
        "query_run",
        "alembic_version",
    } <= names
```

Run:

```bash
uv run --package datapulse-server pytest apps/server/tests/metadata -v
uv run --package datapulse-server ruff check apps/server
uv run --package datapulse-server ruff format --check apps/server
```

- [ ] **Step 7: Commit**

```bash
git add apps/server/pyproject.toml apps/server/src/datapulse/settings.py \
  apps/server/src/datapulse/metadata apps/server/alembic.ini \
  apps/server/migrations apps/server/tests/metadata uv.lock
git commit -m "feat: add datasource studio metadata database"
```

---

### Task 2: Passwords, Bootstrap Codes, Sessions, and Login Limiting

**Files:**
- Modify: `apps/server/pyproject.toml`
- Create: `apps/server/src/datapulse/auth/__init__.py`
- Create: `apps/server/src/datapulse/auth/password.py`
- Create: `apps/server/src/datapulse/auth/bootstrap.py`
- Create: `apps/server/src/datapulse/auth/session.py`
- Create: `apps/server/src/datapulse/auth/limiter.py`
- Create: `apps/server/src/datapulse/auth/repository.py`
- Create: `apps/server/tests/auth/conftest.py`
- Create: `apps/server/tests/auth/test_password.py`
- Create: `apps/server/tests/auth/test_bootstrap.py`
- Create: `apps/server/tests/auth/test_session.py`
- Create: `apps/server/tests/auth/test_limiter.py`
- Modify: `uv.lock`

**Interfaces:**
- Produces: `hash_password(password: str) -> str`
- Produces: `verify_password(password: str, password_hash: str) -> bool`
- Produces: `BootstrapService`
- Produces: `SessionService`
- Produces: `LoginLimiter`
- Produces: `AuthRepository`

- [ ] **Step 1: Write failing password tests**

```python
def test_password_hash_uses_argon2_and_verifies() -> None:
    encoded = hash_password("correct horse battery staple")
    assert encoded.startswith("$argon2")
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong password", encoded)


def test_password_rejects_less_than_ten_characters() -> None:
    with pytest.raises(ValueError, match="at least 10"):
        hash_password("too-short")
```

Run and verify import failure:

```bash
uv run --package datapulse-server pytest apps/server/tests/auth/test_password.py -v
```

- [ ] **Step 2: Add Argon2 and implement password functions**

```bash
uv add --package datapulse-server "pwdlib[argon2]>=0.2,<1"
```

Use one module-level `PasswordHash.recommended()` instance. Do not expose password hashes outside the auth package.

- [ ] **Step 3: Write failing bootstrap lifecycle tests**

Use an injected UTC clock and deterministic token factory. Assert:

- no administrator creates a code hash and returns the raw code once;
- only the hash is persisted;
- expired or wrong codes fail;
- restart replaces an unconsumed code;
- creating the administrator consumes the code;
- an existing administrator prevents a new code.

The core assertion:

```python
raw_code = await service.issue_code()
assert raw_code == "setup-code"
state = await repository.get_system_state()
assert state.setup_code_hash != raw_code
assert await service.consume_code(raw_code)
assert not await service.consume_code(raw_code)
```

- [ ] **Step 4: Implement bootstrap and repository behavior**

Hash setup codes with SHA-256 plus `hmac.compare_digest`; set a 30-minute expiry. Use `secrets.token_urlsafe(24)` in production. `BootstrapService.create_admin()` must perform code consumption and administrator insertion in one transaction.

- [ ] **Step 5: Write failing Session tests**

Assert:

- 32-byte random session and CSRF values are returned only at creation;
- only hashes are persisted;
- valid sessions resolve the administrator;
- expired and revoked sessions fail;
- logout deletes the record;
- password change can revoke every other session.

Use:

```python
created = await service.create(admin_id=admin.id)
assert created.session_token != created.csrf_token
assert await service.authenticate(created.session_token) == admin
assert await service.verify_csrf(
    created.session_token,
    cookie_token=created.csrf_token,
    header_token=created.csrf_token,
)
```

- [ ] **Step 6: Implement sessions and the login limiter**

`SessionService` persists SHA-256 hashes and uses `hmac.compare_digest`. Absolute expiry is eight hours.

`LoginLimiter` is an in-memory fixed-window limiter keyed by normalized client IP:

```python
limiter = LoginLimiter(max_failures=5, window=timedelta(minutes=15), clock=clock)
```

The sixth failed attempt in one window raises `LoginRateLimited`; success clears the key.

- [ ] **Step 7: Verify and commit**

```bash
uv run --package datapulse-server pytest apps/server/tests/auth -v
uv run --package datapulse-server ruff check apps/server
uv run --package datapulse-server ruff format --check apps/server
git add apps/server/pyproject.toml apps/server/src/datapulse/auth \
  apps/server/tests/auth uv.lock
git commit -m "feat: add single-admin authentication core"
```

---

### Task 3: Error Envelope, Request IDs, and Authentication API

**Files:**
- Modify: `apps/server/src/datapulse/app.py`
- Modify: `apps/server/src/datapulse/settings.py`
- Create: `apps/server/src/datapulse/errors.py`
- Create: `apps/server/src/datapulse/lifespan.py`
- Create: `apps/server/src/datapulse/auth/api.py`
- Create: `apps/server/src/datapulse/auth/dependencies.py`
- Create: `apps/server/tests/support/app.py`
- Create: `apps/server/tests/test_errors.py`
- Create: `apps/server/tests/auth/test_api.py`
- Modify: `apps/server/tests/test_app.py`

**Interfaces:**
- Produces: `DataPulseError(code, message, status_code, field_errors=())`
- Produces: `request_id_middleware`
- Produces: `require_admin(request: Request) -> AdminAccount`
- Produces: `require_csrf(request: Request) -> None`
- Produces auth router under `/api/auth`

- [ ] **Step 1: Write failing error-envelope tests**

```python
def test_datapulse_error_uses_stable_envelope(client: TestClient) -> None:
    response = client.get("/api/test-error")
    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "TEST_INVALID",
            "message": "Invalid test input.",
            "request_id": response.headers["x-request-id"],
            "field_errors": [],
        }
    }
```

Also assert a caller-provided valid `X-Request-ID` is preserved and an invalid or oversized value is replaced.

- [ ] **Step 2: Implement request IDs and error handling**

Generate UUID4 request IDs, attach them to `request.state.request_id`, return `X-Request-ID`, and register handlers for `DataPulseError` and request validation. Never put exception representations into the client message.

- [ ] **Step 3: Create the async application lifespan**

`lifespan.py` must:

1. create `data_dir` and `sources_dir`;
2. construct the metadata engine and session factory;
3. check that Alembic is at `head`;
4. create auth services and store them on `app.state`;
5. issue and log a setup code only when no administrator exists;
6. dispose the engine on shutdown.

`build_test_app(tmp_path)` runs migrations before creating the application and provides a TestClient context manager so lifespan executes.

For deterministic browser tests only, add `bootstrap_code_override: str | None = None` to Settings. Lifespan may use it only when `environment == "test"`; any non-test environment with an override must fail startup. Unit-test this guard. Production and development always use `secrets.token_urlsafe(24)`.

- [ ] **Step 4: Write failing auth API tests**

Cover exact routes and cookie properties:

```python
def test_setup_login_session_logout_flow(app_client: AppClient) -> None:
    code = app_client.setup_code
    setup = app_client.client.post(
        "/api/auth/setup",
        json={"code": code, "username": "admin", "password": "long-enough-password"},
        headers={"Origin": app_client.origin},
    )
    assert setup.status_code == 201
    assert "datapulse_session=" in setup.headers["set-cookie"]
    assert "HttpOnly" in setup.headers["set-cookie"]

    session = app_client.client.get("/api/auth/session")
    assert session.json()["username"] == "admin"

    csrf = app_client.client.cookies["datapulse_csrf"]
    logout = app_client.client.post(
        "/api/auth/logout",
        headers={"X-CSRF-Token": csrf, "Origin": app_client.origin},
    )
    assert logout.status_code == 204
```

Add negative tests for wrong/expired setup code, second setup, invalid credentials, sixth failed login, missing Session, missing CSRF, mismatched CSRF, and wrong Origin.

- [ ] **Step 5: Implement auth request models and routes**

Use Pydantic models with `extra="forbid"`. Endpoints:

```text
GET    /api/auth/status
POST   /api/auth/setup
POST   /api/auth/login
POST   /api/auth/logout
GET    /api/auth/session
PATCH  /api/auth/password
```

Set both cookies with `Path=/` and `SameSite=Lax`; set `Secure` whenever `environment == "production"`. `status` returns only `{"initialized": bool}`. A second setup attempt returns 404.

- [ ] **Step 6: Protect a test admin endpoint and verify dependencies**

Add a test-only router through `build_test_app()`:

```python
@router.get("/api/admin/probe")
async def probe(admin: Annotated[AdminAccount, Depends(require_admin)]) -> dict[str, str]:
    return {"username": admin.username}
```

Assert unauthenticated access returns 401 and authenticated access succeeds. Assert POST requires `require_csrf`.

- [ ] **Step 7: Run all backend tests and commit**

```bash
uv run --package datapulse-server pytest apps/server/tests -v
uv run --package datapulse-server ruff check apps/server
uv run --package datapulse-server ruff format --check apps/server
git add apps/server/src/datapulse/app.py apps/server/src/datapulse/errors.py \
  apps/server/src/datapulse/lifespan.py apps/server/src/datapulse/settings.py \
  apps/server/src/datapulse/auth apps/server/tests
git commit -m "feat: add authenticated admin API"
```

Update the original health and static tests to use `build_test_app()` or a migrated temporary database so the new lifespan is exercised rather than bypassed.

---

### Task 4: Datasource API Models, Secret Encryption, Repository, and Registry

**Files:**
- Modify: `apps/server/pyproject.toml`
- Modify: `apps/server/src/datapulse/settings.py`
- Create: `apps/server/src/datapulse/datasource/__init__.py`
- Create: `apps/server/src/datapulse/datasource/models.py`
- Create: `apps/server/src/datapulse/datasource/secrets.py`
- Create: `apps/server/src/datapulse/datasource/repository.py`
- Create: `apps/server/src/datapulse/datasource/connector.py`
- Create: `apps/server/src/datapulse/datasource/registry.py`
- Create: `apps/server/src/datapulse/datasource/engine_manager.py`
- Create: `apps/server/tests/datasource/test_models.py`
- Create: `apps/server/tests/datasource/test_secrets.py`
- Create: `apps/server/tests/datasource/test_repository.py`
- Create: `apps/server/tests/datasource/test_registry.py`
- Modify: `uv.lock`

**Interfaces:**
- Produces discriminated `DatasourceConfig` and `DatasourceCreate`, `DatasourceUpdate`, `DatasourceResponse`
- Produces `SecretBox.encrypt(datasource_id: str, password: str) -> SecretEnvelope`
- Produces `SecretBox.decrypt(datasource_id: str, envelope: SecretEnvelope) -> str`
- Produces `DatasourceRepository`
- Produces `Connector` protocol and `ConnectorRegistry`
- Produces `EngineManager`

- [ ] **Step 1: Write failing config-model tests**

Define exact public request shapes:

```python
{
    "name": "Sales",
    "config": {
        "type": "postgresql",
        "host": "db.internal",
        "port": 5432,
        "database": "sales",
        "username": "reader",
        "ssl_mode": "prefer"
    },
    "password": "secret"
}
```

SQLite uses `{"type": "sqlite", "path": "demo/sales.db"}`. MySQL uses default port 3306 and `ssl_mode` values `disabled`, `preferred`, and `required`. Assert unknown fields, blank names, invalid ports, absolute SQLite paths, and `..` fail validation.

`DatasourceResponse` contains `has_password: bool` but has no password, ciphertext, nonce, or connection URL fields.

- [ ] **Step 2: Write failing AES-GCM tests**

```python
def test_secret_box_uses_random_nonce_and_datasource_aad(master_key: str) -> None:
    first = SecretBox(master_key).encrypt("source-a", "password")
    second = SecretBox(master_key).encrypt("source-a", "password")
    assert first != second
    assert SecretBox(master_key).decrypt("source-a", first) == "password"
    with pytest.raises(SecretDecryptionError):
        SecretBox(master_key).decrypt("source-b", first)
```

Also test malformed Base64 keys, keys not 32 bytes, wrong keys, and missing keys. Exception messages must not contain plaintext or ciphertext.

- [ ] **Step 3: Add cryptography and implement the secret envelope**

```bash
uv add --package datapulse-server "cryptography>=44,<50"
```

Use `AESGCM`, a fresh 12-byte nonce, envelope version 1, and AAD:

```text
datapulse:datasource:{datasource_id}:password:v1
```

Serialize nonce and ciphertext with URL-safe Base64 without logging them.

Add `master_key: str | None = None` to Settings. `SecretBox.from_settings()` returns no box when the key is absent, validates URL-safe Base64 and exactly 32 decoded bytes when present, and never stores decoded key material on a response model.

- [ ] **Step 4: Write and implement repository tests**

Assert create/list/get/update/delete, unique-name mapping, password preservation when omitted, explicit password clearing, and dependency-conflict behavior. Repository methods accept validated models and return response DTOs, never ORM records with secret fields.

Use a three-state password patch:

```python
class DatasourceUpdate(ContractModel):
    name: NonBlankStr | None = None
    config: DatasourceConfig | None = None
    password: SecretStr | None = None
    clear_password: bool = False
```

Reject `password` together with `clear_password=true`.

- [ ] **Step 5: Define the connector protocol and registry**

Implement the exact `Connector` methods from the approved spec plus typed `ConnectionTestResult`, `NamespaceInfo`, `RelationInfo`, `RelationSchema`, `QueryPolicy`, and `QueryStream`.

The registry rejects duplicates and unknown connector types:

```python
registry = ConnectorRegistry([sqlite, postgresql, mysql])
assert registry.get(ConnectorType.SQLITE) is sqlite
with pytest.raises(ConnectorNotFound):
    registry.get("oracle")
```

- [ ] **Step 6: Implement EngineManager lifecycle tests**

Use fake disposable engines. Assert engines are reused for the same `(datasource_id, updated_at)`, replaced and disposed after an update, disposed after deletion, and all disposed on application shutdown.

- [ ] **Step 7: Verify and commit**

```bash
uv run --package datapulse-server pytest apps/server/tests/datasource -v
uv run --package datapulse-server ruff check apps/server
uv run --package datapulse-server ruff format --check apps/server
git add apps/server/pyproject.toml apps/server/src/datapulse/settings.py \
  apps/server/src/datapulse/datasource apps/server/tests/datasource uv.lock
git commit -m "feat: define datasource core and secret storage"
```

---

### Task 5: SQL Safety, Parameters, Result Normalization, and Query Limits

**Files:**
- Modify: `apps/server/pyproject.toml`
- Create: `apps/server/src/datapulse/query/__init__.py`
- Create: `apps/server/src/datapulse/query/models.py`
- Create: `apps/server/src/datapulse/query/safety.py`
- Create: `apps/server/src/datapulse/query/parameters.py`
- Create: `apps/server/src/datapulse/query/normalization.py`
- Create: `apps/server/src/datapulse/query/limits.py`
- Create: `apps/server/tests/query/test_safety.py`
- Create: `apps/server/tests/query/test_parameters.py`
- Create: `apps/server/tests/query/test_normalization.py`
- Create: `apps/server/tests/query/test_limits.py`
- Modify: `uv.lock`

**Interfaces:**
- Produces: `validate_read_only_sql(sql: str, dialect: str) -> ValidatedQuery`
- Produces: `validate_parameters(query: ValidatedQuery, parameters: JsonObject) -> None`
- Produces: `normalize_result_value(value: object) -> JsonValue`
- Produces: `QueryLimiter`
- Produces: `QueryRequest`, `QueryColumn`, and `QueryResult`

- [ ] **Step 1: Write the failing SQL safety matrix**

Parameterize all three dialects and these accepted statements:

```sql
SELECT month, amount FROM sales
WITH totals AS (SELECT SUM(amount) AS value FROM sales) SELECT value FROM totals
SELECT id FROM current_sales UNION ALL SELECT id FROM archived_sales
```

Reject empty SQL, two statements, and every dangerous family:

```sql
INSERT INTO sales VALUES (1)
UPDATE sales SET amount = 0
DELETE FROM sales
CREATE TABLE leaked(id INT)
DROP TABLE sales
ALTER TABLE sales ADD COLUMN leaked INT
TRUNCATE TABLE sales
ATTACH DATABASE '/tmp/secret.db' AS secret
PRAGMA writable_schema = 1
CALL dangerous_proc()
SELECT * FROM sales FOR UPDATE
COPY sales TO '/tmp/sales.csv'
```

Also embed mutations inside CTEs to prove recursive AST inspection.

- [ ] **Step 2: Run the safety tests and verify import failure**

```bash
uv run --package datapulse-server pytest apps/server/tests/query/test_safety.py -v
```

- [ ] **Step 3: Add SQLGlot and implement AST validation**

```bash
uv add --package datapulse-server "sqlglot>=25,<40"
```

Use `sqlglot.parse(sql, read=dialect)`, require exactly one expression, require a query expression, and traverse all nodes for forbidden classes. Preserve the original SQL for driver execution; use SQLGlot output only for validation and a normalized SHA-256 query hash.

Map parse errors to `QUERY_SYNTAX_INVALID`, multiple statements to `QUERY_MULTIPLE_STATEMENTS`, and forbidden nodes to `QUERY_NOT_READ_ONLY`.

- [ ] **Step 4: Write and implement named-parameter validation**

Accept `:year` and repeated `:year`; ignore PostgreSQL `::type` casts. Reject missing parameters, extra parameters, invalid parameter names, and identifier substitution.

```python
query = validate_read_only_sql(
    "SELECT * FROM sales WHERE year = :year AND region = :region",
    "postgres",
)
validate_parameters(query, {"year": 2026, "region": "north"})
```

Return field errors with the missing or extra parameter names, never parameter values.

- [ ] **Step 5: Write and implement result normalization**

Test null, bool, int, finite float, string, UUID, date, datetime, Decimal, bytes, and unsupported objects. Rules:

- timezone-aware datetime → ISO 8601;
- naive datetime → ISO 8601 without inventing a timezone;
- Decimal exactly representable as a safe JSON number → int/float;
- other Decimal → string while column metadata remains `decimal`;
- bytes → Base64 string;
- NaN and infinity → null;
- unsupported values → `QUERY_RESULT_TYPE_UNSUPPORTED`.

- [ ] **Step 6: Write and implement concurrency tests**

`QueryLimiter(global_limit=4, per_source_limit=2, acquire_timeout=0)` is an async context manager. Assert the third query for one source and the fifth query globally raise `QueryConcurrencyLimited` immediately, and slots are released after success, error, timeout, and cancellation.

- [ ] **Step 7: Verify and commit**

```bash
uv run --package datapulse-server pytest apps/server/tests/query -v
uv run --package datapulse-server ruff check apps/server
uv run --package datapulse-server ruff format --check apps/server
git add apps/server/pyproject.toml apps/server/src/datapulse/query \
  apps/server/tests/query uv.lock
git commit -m "feat: add safe query validation and limits"
```

---

### Task 6: SQLite Connector and Shared Connector Contract Suite

**Files:**
- Create: `apps/server/src/datapulse/datasource/sqlite.py`
- Create: `apps/server/src/datapulse/query/execution.py`
- Create: `apps/server/tests/connectors/__init__.py`
- Create: `apps/server/tests/connectors/contract.py`
- Create: `apps/server/tests/connectors/test_sqlite.py`
- Create: `apps/server/tests/query/test_execution.py`

**Interfaces:**
- Produces: `SQLiteConnector`
- Produces: `QueryExecutor.execute(...) -> QueryResult`
- Produces reusable `ConnectorContract` tests consumed by Task 7

- [ ] **Step 1: Write the SQLite contract fixtures**

Create a temporary SQLite database under `tmp_path / "sources"` with:

```sql
CREATE TABLE sales (
  month TEXT NOT NULL,
  amount NUMERIC NOT NULL,
  region TEXT
);
CREATE VIEW monthly_sales AS
SELECT month, SUM(amount) AS amount FROM sales GROUP BY month;
```

Insert three rows. Tests assert connection success, one namespace-less catalog, tables and views, field names/types/nullability, parameterized query results, duplicate output column names, and empty results.

- [ ] **Step 2: Add failing SQLite security tests**

Assert rejection of:

- absolute paths;
- `../` paths;
- symlink escape outside `sources_dir`;
- missing files;
- directories;
- write attempts;
- `ATTACH`, `PRAGMA`, and extension loading.

Open a second direct SQLite connection after connector tests and prove the fixture has not changed.

- [ ] **Step 3: Implement SQLiteConnector**

Resolve the configured path against `Settings.resolved_sources_dir()`, call `resolve(strict=True)`, verify `is_relative_to(root)` and `is_file()`, and connect with:

```text
sqlite+aiosqlite:///file:/absolute/path?mode=ro&uri=true
```

Use SQLAlchemy inspection through `AsyncConnection.run_sync()` for catalog metadata. Normalize SQLite affinities to DataPulse types.

- [ ] **Step 4: Write failing QueryExecutor tests**

Use a fake connector stream to assert:

- SQL is validated before connector invocation;
- parameters are validated before connector invocation;
- global/per-source slots surround execution;
- exactly `max_rows + 1` rows are consumed;
- the extra row sets `truncated=true` but is not returned;
- timeout maps to status 504 and QueryRun `timed_out`;
- cancellation maps QueryRun `cancelled`;
- success and failure always finalize QueryRun.

- [ ] **Step 5: Implement QueryExecutor**

The executor flow is fixed:

```text
validate SQL
→ validate parameters
→ create QueryRun(running)
→ acquire query limits
→ asyncio.timeout(policy.timeout_seconds)
→ connector.stream_query()
→ normalize columns and rows
→ finalize QueryRun
→ return QueryResult
```

Use an injected repository, limiter, clock, and request ID factory. Never include SQL text or parameters in QueryRun.

- [ ] **Step 6: Verify and commit**

```bash
uv run --package datapulse-server pytest \
  apps/server/tests/connectors/test_sqlite.py \
  apps/server/tests/query/test_execution.py -v
uv run --package datapulse-server ruff check apps/server
uv run --package datapulse-server ruff format --check apps/server
git add apps/server/src/datapulse/datasource/sqlite.py \
  apps/server/src/datapulse/query/execution.py \
  apps/server/tests/connectors apps/server/tests/query/test_execution.py
git commit -m "feat: add read-only SQLite query connector"
```

---

### Task 7: PostgreSQL and MySQL/MariaDB Connectors

**Files:**
- Modify: `apps/server/pyproject.toml`
- Modify: `pyproject.toml`
- Create: `apps/server/src/datapulse/datasource/postgresql.py`
- Create: `apps/server/src/datapulse/datasource/mysql.py`
- Create: `apps/server/tests/connectors/test_postgresql.py`
- Create: `apps/server/tests/connectors/test_mysql.py`
- Create: `compose.test.yaml`
- Modify: `.github/workflows/ci.yml`
- Modify: `uv.lock`

**Interfaces:**
- Produces: `PostgreSQLConnector`
- Produces: `MySQLConnector` supporting both MySQL and MariaDB
- Consumes: shared `ConnectorContract`

- [ ] **Step 1: Add drivers and test-service configuration**

```bash
uv add --package datapulse-server "asyncpg>=0.29,<1" "asyncmy>=0.2,<1"
```

`compose.test.yaml` defines PostgreSQL and MariaDB on host ports 55432 and 53306 with fixed test-only credentials and health checks. Tests read:

```text
DATAPULSE_TEST_POSTGRES_URL
DATAPULSE_TEST_MYSQL_URL
```

They skip only when the variable is absent; CI always sets both, so a connector failure cannot become a skip.

- [ ] **Step 2: Write failing PostgreSQL contract tests**

Create an isolated schema per test run, create the shared sales table/view, and run all `ConnectorContract` assertions. Add PostgreSQL-specific tests for:

- namespace listing;
- `TIMESTAMPTZ`, `NUMERIC`, UUID, JSONB, and arrays;
- `statement_timeout`;
- read-only transaction rejecting a write even if the safety layer is bypassed in the test.

- [ ] **Step 3: Implement PostgreSQLConnector**

Use SQLAlchemy async engine with asyncpg, `pool_pre_ping=true`, pool size 2, and a safe URL created from structured fields rather than string concatenation. Before user query:

```sql
SET TRANSACTION READ ONLY;
SET LOCAL statement_timeout = :milliseconds;
```

Read catalog information with SQLAlchemy inspector or parameterized `pg_catalog` queries. Do not expose system schemas by default.

- [ ] **Step 4: Write failing MariaDB contract tests**

Create isolated table/view names inside the configured test database and execute the same contract suite. Do not require the test account to create another database. Add tests for:

- `information_schema` browsing;
- signed/unsigned integers, DECIMAL, DATETIME, JSON, BLOB;
- driver read timeout;
- read-only transaction rejecting writes.

- [ ] **Step 5: Implement MySQLConnector**

Use asyncmy, `pool_pre_ping=true`, pool size 2, and structured URL construction. Execute:

```sql
SET TRANSACTION READ ONLY;
```

before user queries. Use application/driver timeout universally; apply `MAX_EXECUTION_TIME` or MariaDB `max_statement_time` only after detecting server capability, and never fail a valid query solely because that optional server setting is unsupported.

- [ ] **Step 6: Add CI service containers**

In the Python 3.13 job, add PostgreSQL and MariaDB services with health checks and set both test URLs. The existing `pnpm verify` backend test step then runs the service-backed tests instead of skipping them. Keep Python 3.14 compatibility tests on SQLite only to avoid duplicating service cost.

Register an `integration` pytest marker in root `pyproject.toml` so service-backed tests are selectable without warnings.

- [ ] **Step 7: Verify against real containers**

```bash
docker compose -f compose.test.yaml up -d --wait
DATAPULSE_TEST_POSTGRES_URL='postgresql+asyncpg://datapulse:datapulse@127.0.0.1:55432/datapulse' \
DATAPULSE_TEST_MYSQL_URL='mysql+asyncmy://datapulse:datapulse@127.0.0.1:53306/datapulse' \
uv run --package datapulse-server pytest apps/server/tests/connectors -v
docker compose -f compose.test.yaml down -v
```

If tests fail, collect logs before removing only the two services declared by `compose.test.yaml`.

- [ ] **Step 8: Verify and commit**

```bash
uv run --package datapulse-server ruff check apps/server
uv run --package datapulse-server ruff format --check apps/server
git add apps/server/pyproject.toml apps/server/src/datapulse/datasource \
  apps/server/tests/connectors compose.test.yaml .github/workflows/ci.yml \
  pyproject.toml uv.lock
git commit -m "feat: add PostgreSQL and MySQL connectors"
```

---

### Task 8: Datasource Service and Authenticated Admin API

**Files:**
- Modify: `apps/server/src/datapulse/app.py`
- Modify: `apps/server/src/datapulse/lifespan.py`
- Create: `apps/server/src/datapulse/datasource/service.py`
- Create: `apps/server/src/datapulse/datasource/api.py`
- Create: `apps/server/tests/datasource/test_service.py`
- Create: `apps/server/tests/datasource/test_api.py`

**Interfaces:**
- Produces: `DatasourceService`
- Produces admin router under `/api/admin/datasources`
- Consumes: repository, SecretBox, registry, EngineManager, QueryExecutor

- [ ] **Step 1: Write failing service tests**

Assert these service rules:

- create validates config before persistence;
- PostgreSQL/MySQL password with no master key returns `DATASOURCE_SECRET_KEY_MISSING`;
- password is encrypted before repository insertion;
- update without password preserves secret;
- changing connection fields disposes the cached engine;
- delete disposes engine;
- test connection updates status, latency, timestamp, and safe error code;
- datasource responses contain only sanitized address fields.

- [ ] **Step 2: Implement DatasourceService**

Keep transaction boundaries in the service. Connector exceptions map through one translator:

```python
translate_connector_error(error: Exception, request_id: str) -> DataPulseError
```

Log only connector type, datasource ID, stable error code, and request ID.

- [ ] **Step 3: Write failing CRUD and security API tests**

Every test logs in first and sends the CSRF header for mutations. Cover:

```text
GET    /api/admin/datasources
POST   /api/admin/datasources
GET    /api/admin/datasources/{id}
PATCH  /api/admin/datasources/{id}
DELETE /api/admin/datasources/{id}
POST   /api/admin/datasources/{id}/test
```

Assert unauthenticated 401, missing CSRF 403, duplicate name 409, unknown source 404, and response bodies containing neither submitted password nor AES envelope keys.

- [ ] **Step 4: Write failing catalog and query API tests**

Using a real temporary SQLite source:

```text
GET  /api/admin/datasources/{id}/namespaces
GET  /api/admin/datasources/{id}/relations?namespace=
GET  /api/admin/datasources/{id}/relation?namespace=&relation=sales
POST /api/admin/datasources/{id}/query
```

Query body:

```json
{
  "sql": "SELECT month, amount FROM sales WHERE region = :region",
  "parameters": {"region": "north"},
  "max_rows": 1000,
  "timeout_seconds": 30
}
```

Assert correct QueryResult, SQL rejection before connector use, timeout 504, concurrency 429, and request ID parity between header/body.

- [ ] **Step 5: Implement the router and application wiring**

All `/api/admin/*` routes depend on `require_admin`; mutations and query execution also depend on `require_csrf`. Construct and register the three connectors, registry, engine manager, query limiter, query executor, and service in lifespan. Dispose all engines on shutdown.

- [ ] **Step 6: Verify and commit**

```bash
uv run --package datapulse-server pytest \
  apps/server/tests/datasource/test_service.py \
  apps/server/tests/datasource/test_api.py -v
uv run --package datapulse-server pytest apps/server/tests -v
uv run --package datapulse-server ruff check apps/server
uv run --package datapulse-server ruff format --check apps/server
git add apps/server/src/datapulse/app.py apps/server/src/datapulse/lifespan.py \
  apps/server/src/datapulse/datasource apps/server/tests/datasource
git commit -m "feat: expose authenticated datasource APIs"
```

---

### Task 9: Dataset Persistence, Save-from-Query, and Preview API

**Files:**
- Modify: `apps/server/src/datapulse/app.py`
- Create: `apps/server/src/datapulse/dataset/__init__.py`
- Create: `apps/server/src/datapulse/dataset/models.py`
- Create: `apps/server/src/datapulse/dataset/repository.py`
- Create: `apps/server/src/datapulse/dataset/service.py`
- Create: `apps/server/src/datapulse/dataset/api.py`
- Create: `apps/server/tests/dataset/test_repository.py`
- Create: `apps/server/tests/dataset/test_service.py`
- Create: `apps/server/tests/dataset/test_api.py`

**Interfaces:**
- Produces: `DatasetCreate`, `DatasetUpdate`, and `DatasetResponse`
- Produces: `DatasetRepository`
- Produces: `DatasetService`
- Produces admin router under `/api/admin/datasets`

- [ ] **Step 1: Write failing repository tests**

Test create/list/get/update/delete, unique names, source foreign key, timestamps, and round-trip validation of `DatasetDefinition` v1. Corrupt JSON in the database must raise `DATASET_DEFINITION_INVALID`, not a raw Pydantic error.

- [ ] **Step 2: Implement the repository**

Store the full versioned contract as canonical JSON with sorted keys. Keep indexed columns for `id`, `name`, and `data_source_id`. Return immutable response models.

- [ ] **Step 3: Write failing service tests**

“Save as dataset” accepts:

```json
{
  "name": "Monthly sales",
  "data_source_id": "uuid",
  "sql": "SELECT month, SUM(amount) AS sales FROM sales GROUP BY month",
  "parameters": [],
  "max_rows": 5000,
  "timeout_seconds": 30
}
```

The service must:

1. load the source;
2. validate SQL with that source dialect;
3. run one preview query;
4. infer `DatasetField` entries from result columns;
5. build and persist `DatasetDefinition(schema_version=1, query=SqlQuery(...))`.

Assert invalid source, unsafe SQL, duplicate name, and preview failure do not create a dataset.

- [ ] **Step 4: Write failing API tests**

Cover:

```text
GET    /api/admin/datasets
POST   /api/admin/datasets
GET    /api/admin/datasets/{id}
PATCH  /api/admin/datasets/{id}
DELETE /api/admin/datasets/{id}
POST   /api/admin/datasets/{id}/preview
```

Require admin + CSRF for mutations and previews. Preview accepts parameter values, runs the same safety path, and returns QueryResult.

- [ ] **Step 5: Implement service, router, and app wiring**

No dataset endpoint may call a connector directly. Register `DatasetService` in lifespan, inject it into the router, and use stable `DATASET_*` errors.

- [ ] **Step 6: Regenerate and prove contracts remain drift-free**

DatasetDefinition is already a public contract. If implementation requires a shape change, first add a failing contract test, update the Python model without changing `schema_version`, regenerate artifacts, and verify the change is backward-compatible. Otherwise generation must produce no diff:

```bash
pnpm generate:contracts
pnpm check:contracts
```

- [ ] **Step 7: Verify and commit**

```bash
uv run --package datapulse-server pytest apps/server/tests/dataset -v
uv run --package datapulse-server pytest apps/server/tests -v
uv run --package datapulse-server ruff check apps/server
uv run --package datapulse-server ruff format --check apps/server
git add apps/server/src/datapulse/app.py apps/server/src/datapulse/dataset \
  apps/server/tests/dataset packages/schema
git commit -m "feat: add dataset persistence and preview"
```

---

### Task 10: Notion-Style Studio Shell, Router, Setup, and Login

**Files:**
- Modify: `apps/web/package.json`
- Modify: `apps/web/src/main.ts`
- Modify: `apps/web/src/App.vue`
- Modify: `apps/web/src/App.test.ts`
- Modify: `apps/web/src/lib/api.ts`
- Replace: `apps/web/src/styles/base.css`
- Create: `apps/web/src/router/index.ts`
- Create: `apps/web/src/stores/auth.ts`
- Create: `apps/web/src/ui/StudioShell.vue`
- Create: `apps/web/src/ui/FormField.vue`
- Create: `apps/web/src/ui/InlineNotice.vue`
- Create: `apps/web/src/features/auth/SetupView.vue`
- Create: `apps/web/src/features/auth/LoginView.vue`
- Create: `apps/web/src/features/auth/auth.test.ts`
- Create: `apps/web/src/features/home/HomeView.vue`
- Modify: `pnpm-lock.yaml`

**Interfaces:**
- Produces: Vue Router with authenticated `/studio/*` routes
- Produces: `useAuthStore()`
- Produces: `apiRequest<T>()` with credentials, CSRF, and error-envelope parsing
- Produces reusable Notion-style shell and form primitives

- [ ] **Step 1: Write failing API-client tests**

Test `apiRequest()` with mocked fetch:

- always sends `credentials: "same-origin"`;
- adds `X-CSRF-Token` from `datapulse_csrf` for POST/PATCH/DELETE;
- does not add it to GET;
- parses `DataPulseErrorResponse`;
- preserves request ID;
- maps 401 to an auth-expired event without discarding the original error.

Use a cookie parser that reads only the exact `datapulse_csrf` name.

- [ ] **Step 2: Add Vue Router and implement the API client**

```bash
pnpm --filter @datapulse/web add vue-router@^4
```

Define:

```ts
export class ApiError extends Error {
  code: string;
  requestId: string;
  fieldErrors: FieldError[];
}
```

Do not display raw `Response.statusText` as user-facing copy.

- [ ] **Step 3: Write failing auth-store and router tests**

Assert:

- uninitialized status redirects to `/studio/setup`;
- initialized + anonymous redirects to `/studio/login`;
- authenticated users entering setup/login redirect to `/studio/datasources`;
- setup posts code/username/password and becomes authenticated;
- logout includes CSRF and clears local state;
- page refresh restores state from `/api/auth/session`.

- [ ] **Step 4: Implement the auth store and routes**

The store state is:

```ts
type AuthState =
  | { status: "unknown" }
  | { status: "setup-required" }
  | { status: "anonymous" }
  | { status: "authenticated"; username: string };
```

Avoid redirect loops by resolving `status` once per navigation and deduplicating concurrent status/session requests.

- [ ] **Step 5: Implement the approved design tokens and shell**

Define CSS custom properties:

```css
:root {
  --dp-surface: #ffffff;
  --dp-sidebar: #f7f7f5;
  --dp-text: #37352f;
  --dp-muted: #787774;
  --dp-border: #e9e9e7;
  --dp-action: #37352f;
  --dp-radius-sm: 5px;
  --dp-radius-md: 8px;
}
```

`StudioShell` has the approved workspace switcher, Overview/Data Sources/Datasets/Screens navigation, recent items region, system settings link, top breadcrumb bar, and a content column. Keep the editor minimum width at 1,200px; setup and login remain responsive.

- [ ] **Step 6: Implement setup and login views**

Setup fields: initialization code, username defaulting to `admin`, password, and confirmation. Login fields: username and password. Use inline field errors, one top-level notice, disabled submitting state, and no password persistence.

- [ ] **Step 7: Verify and commit**

```bash
pnpm --filter @datapulse/web test
pnpm --filter @datapulse/web typecheck
pnpm --filter @datapulse/web build
git add apps/web/package.json apps/web/src pnpm-lock.yaml
git commit -m "feat: add authenticated DataPulse Studio shell"
```

---

### Task 11: Datasource List, Forms, Detail, and Schema Browser

**Files:**
- Modify: `apps/web/package.json`
- Modify: `apps/web/src/router/index.ts`
- Create: `apps/web/src/features/datasources/types.ts`
- Create: `apps/web/src/features/datasources/api.ts`
- Create: `apps/web/src/features/datasources/DatasourceListView.vue`
- Create: `apps/web/src/features/datasources/DatasourceFormView.vue`
- Create: `apps/web/src/features/datasources/DatasourceDetailView.vue`
- Create: `apps/web/src/features/datasources/SchemaBrowser.vue`
- Create: `apps/web/src/features/datasources/datasource-list.test.ts`
- Create: `apps/web/src/features/datasources/datasource-form.test.ts`
- Create: `apps/web/src/features/datasources/schema-browser.test.ts`
- Modify: `pnpm-lock.yaml`

**Interfaces:**
- Produces datasource client DTOs and API functions
- Produces routes `/studio/datasources`, `/new`, and `/:id`
- Produces lazy `SchemaBrowser`

- [ ] **Step 1: Define client types and write failing list tests**

The list fixture contains SQLite, PostgreSQL, and MySQL records with `available`, `unavailable`, and `unknown` states. Assert:

- Notion-style table headers Name, Type, Address, Status, Last checked, Last query;
- sanitized addresses only;
- status text and accessible icon;
- inline test-connection action;
- empty state links to new datasource;
- API error shows safe message and copyable request ID.

- [ ] **Step 2: Implement datasource API functions and list view**

Use one typed API module. Testing a connection must update only the affected row, disable duplicate requests, and retain the previous status until the response arrives.

- [ ] **Step 3: Write failing form tests for all connector types**

Assert dynamic fields:

- SQLite: name and relative path;
- PostgreSQL: name, host, port 5432, database, username, password, SSL mode;
- MySQL/MariaDB: name, host, port 3306, database, username, password, SSL mode.

Edit mode shows an empty password field with “留空则保留现有密码”. Assert absolute/parent SQLite path feedback, invalid port feedback, password + clear conflict prevention, submit loading, and server field errors.

- [ ] **Step 4: Implement the form**

Keep one discriminated reactive model rather than one bag of optional fields. On connector-type changes, initialize that connector’s defaults and discard hidden fields. After create, navigate to detail; after update, remain on detail and refresh.

- [ ] **Step 5: Write failing detail and SchemaBrowser tests**

Assert:

- overview properties match the approved mockup;
- tabs are Overview, Schema, SQL Debug, Settings;
- namespaces load only when Schema opens;
- relations load only when a namespace expands;
- fields load only when a relation opens;
- SQLite skips namespace level;
- refresh invalidates only the current catalog branch;
- errors are isolated to the failing branch.

- [ ] **Step 6: Implement detail and schema browsing**

Use stable compound keys `(sourceId, namespace, relation)` and cancel stale fetches with `AbortController` when routes or expanded nodes change.

- [ ] **Step 7: Add icons and verify**

Use `lucide-vue-next` for a small consistent icon set; do not add an entire component framework:

```bash
pnpm --filter @datapulse/web add lucide-vue-next
pnpm --filter @datapulse/web test
pnpm --filter @datapulse/web typecheck
pnpm --filter @datapulse/web build
```

- [ ] **Step 8: Commit**

```bash
git add apps/web/package.json apps/web/src/features/datasources \
  apps/web/src/router/index.ts pnpm-lock.yaml
git commit -m "feat: add datasource management workspace"
```

---

### Task 12: SQL Debug Workspace, Virtual Results, and Dataset UI

**Files:**
- Modify: `apps/web/package.json`
- Modify: `apps/web/src/router/index.ts`
- Create: `apps/web/src/features/query/types.ts`
- Create: `apps/web/src/features/query/api.ts`
- Create: `apps/web/src/features/query/SqlEditor.vue`
- Create: `apps/web/src/features/query/ParameterEditor.vue`
- Create: `apps/web/src/features/query/QueryResultTable.vue`
- Create: `apps/web/src/features/query/SqlDebugView.vue`
- Create: `apps/web/src/features/query/sql-debug.test.ts`
- Create: `apps/web/src/features/query/query-result-table.test.ts`
- Create: `apps/web/src/features/datasets/types.ts`
- Create: `apps/web/src/features/datasets/api.ts`
- Create: `apps/web/src/features/datasets/DatasetListView.vue`
- Create: `apps/web/src/features/datasets/DatasetDetailView.vue`
- Create: `apps/web/src/features/datasets/SaveDatasetDialog.vue`
- Create: `apps/web/src/features/datasets/datasets.test.ts`
- Modify: `pnpm-lock.yaml`

**Interfaces:**
- Produces CodeMirror SQL editor with per-source dialect
- Produces virtualized `QueryResultTable`
- Produces save-to-dataset and dataset preview workflows

- [ ] **Step 1: Add editor and virtualization dependencies**

```bash
pnpm --filter @datapulse/web add \
  codemirror @codemirror/lang-sql @codemirror/state @codemirror/view \
  @tanstack/vue-virtual
```

Use CodeMirror 6 directly; do not add Monaco.

- [ ] **Step 2: Write failing SQL editor tests**

Assert:

- dialect changes with source type;
- `Cmd-Enter` and `Ctrl-Enter` emit run once;
- read-only badge, 30-second timeout, and 5,000-row maximum are visible;
- query text survives API errors;
- a new run cancels the previous request;
- navigating away aborts an active request.

Mock CodeMirror behind a small adapter in unit tests instead of depending on full browser layout.

- [ ] **Step 3: Implement SqlEditor and ParameterEditor**

Parameter rows have name, type, and JSON-compatible value. Reject duplicate/invalid names client-side but rely on the server as authority. Do not concatenate parameter text into SQL.

- [ ] **Step 4: Write failing result-table tests**

Use a 5,000-row fixture. Assert only the virtual window renders, duplicate column names retain separate positions, null/date/decimal/binary values format safely, horizontal scrolling works, and truncated results show an explicit warning.

- [ ] **Step 5: Implement the virtual result table**

Rows remain arrays aligned to column positions. Keep sorting out of scope because server results may exceed the returned window; column headers are informational only.

- [ ] **Step 6: Implement SqlDebugView**

Compose SchemaBrowser, SqlEditor, ParameterEditor, query actions, diagnostics, and results in the approved split layout. Display:

- running state;
- elapsed duration after completion;
- row count and truncated flag;
- safe error message;
- copyable request ID;
- “保存为数据集” only after a successful query.

- [ ] **Step 7: Write failing dataset UI tests**

Assert save dialog pre-populates source and SQL, requires name, submits parameter definitions, and navigates to the dataset detail. Dataset detail can edit name/config, run preview with parameter values, show QueryResult, and preserve inputs on errors.

- [ ] **Step 8: Implement dataset routes and views**

Add `/studio/datasets` and `/studio/datasets/:id`. Use the same QueryResultTable and error components; do not duplicate result rendering.

- [ ] **Step 9: Verify and commit**

```bash
pnpm --filter @datapulse/web test
pnpm --filter @datapulse/web typecheck
pnpm --filter @datapulse/web build
git add apps/web/package.json apps/web/src/features/query \
  apps/web/src/features/datasets apps/web/src/router/index.ts pnpm-lock.yaml
git commit -m "feat: add SQL debug and dataset workspace"
```

---

### Task 13: Migrations at Delivery, End-to-End Tests, CI, and Acceptance

**Files:**
- Create: `apps/server/docker-entrypoint.sh`
- Modify: `Dockerfile`
- Modify: `compose.yaml`
- Modify: `.dockerignore`
- Modify: `.gitignore`
- Create: `.env.example`
- Modify: `.github/workflows/ci.yml`
- Modify: `apps/web/package.json`
- Modify: `apps/web/vite.config.ts`
- Modify: `package.json`
- Create: `apps/web/playwright.config.ts`
- Create: `apps/web/e2e/datasource-studio.spec.ts`
- Create: `apps/web/e2e/fixtures/sales.sql`
- Create: `tools/prepare_e2e.py`
- Modify: `README.md`
- Modify: `pnpm-lock.yaml`

**Interfaces:**
- Produces container startup `alembic upgrade head → uvicorn`
- Produces `pnpm test:e2e`
- Produces `pnpm verify:full` covering backend, frontend, contracts, integration, and E2E gates

- [ ] **Step 1: Write a failing container migration smoke test**

Before changing the image, run a fresh named volume and verify `/api/auth/status` cannot work because metadata tables are absent. Capture the failure, then remove only the explicitly named container and volume.

- [ ] **Step 2: Implement the non-root entrypoint**

`apps/server/docker-entrypoint.sh`:

```sh
#!/bin/sh
set -eu
uv run --no-sync alembic -c apps/server/alembic.ini upgrade head
exec uv run --no-sync uvicorn datapulse.app:app --host 0.0.0.0 --port 8000
```

The Dockerfile copies the entrypoint, sets executable ownership during build, creates `/data/sources`, and keeps `USER datapulse`. Do not run migration as root. Compose passes `DATAPULSE_MASTER_KEY` from the deployment environment. `.env.example` contains only a `generate-before-use` placeholder and the README command; never commit a working shared key.

- [ ] **Step 3: Add Playwright and write the failing E2E scenario**

```bash
pnpm --filter @datapulse/web add -D @playwright/test
pnpm --filter @datapulse/web exec playwright install chromium
```

The test starts a temporary backend data directory and Vite. It sets `DATAPULSE_ENVIRONMENT=test` and the Task 3 test-only `DATAPULSE_BOOTSTRAP_CODE_OVERRIDE=e2e-setup-code`; startup must reject that override in every non-test environment. The test then performs:

```text
setup admin
→ logout
→ login
→ create SQLite source from e2e fixture
→ test connection
→ browse sales fields
→ run parameterized SELECT
→ save as dataset
→ preview dataset
```

Assert passwords are never rendered and dangerous SQL shows `QUERY_NOT_READ_ONLY`.

- [ ] **Step 4: Add E2E process orchestration**

`tools/prepare_e2e.py` creates a unique temporary data directory, creates `sources/sales.db` from `apps/web/e2e/fixtures/sales.sql` using Python's standard `sqlite3`, and writes non-secret paths to `.e2e/config.json`. Add `.e2e/` to `.gitignore`.

The root `test:e2e` script runs the preparation script before Playwright. `playwright.config.ts` reads `.e2e/config.json` and defines two `webServer` commands with that temporary directory:

```text
DATAPULSE_ENVIRONMENT=test DATAPULSE_BOOTSTRAP_CODE_OVERRIDE=e2e-setup-code DATAPULSE_DATA_DIR=<temp> uv run --package datapulse-server uvicorn datapulse.app:app --port 18001
VITE_API_PROXY_TARGET=http://127.0.0.1:18001 pnpm --filter @datapulse/web dev --host 127.0.0.1 --port 15173
```

Update `vite.config.ts` to read `VITE_API_PROXY_TARGET` with the existing `http://127.0.0.1:8000` default. Use unique temporary paths and ports. E2E teardown removes only its own temporary directory.

- [ ] **Step 5: Update root scripts and CI**

Add:

```json
{
  "scripts": {
    "test:e2e": "uv run --package datapulse-server python tools/prepare_e2e.py && pnpm --filter @datapulse/web exec playwright test",
    "test:integration": "uv run --package datapulse-server pytest apps/server/tests/connectors -m integration",
    "verify": "pnpm check:contracts && pnpm test && pnpm typecheck && pnpm build",
    "verify:full": "pnpm verify && pnpm test:integration && pnpm test:e2e"
  }
}
```

CI installs Chromium and runs `pnpm verify:full` with PostgreSQL/MariaDB service URLs, then builds the Docker image. Python 3.14 runs all non-service backend tests and contract generation.

- [ ] **Step 6: Update README with exact operation commands**

Document:

- migration command;
- generation of `DATAPULSE_MASTER_KEY` using a safe one-line Python command;
- setup code location in logs;
- Studio URL;
- SQLite source mount under `/data/sources`;
- PostgreSQL/MySQL read-only account recommendation;
- local integration test Compose commands;
- full verification and E2E commands;
- explicit statement that DuckDB, files, caching, screens, and embedding arrive in later stages.

- [ ] **Step 7: Run the complete acceptance gate**

```bash
pnpm generate:contracts
pnpm check:contracts
uv run --package datapulse-server pytest apps/server/tests -v
uv run --package datapulse-server ruff check apps/server tools
uv run --package datapulse-server ruff format --check apps/server tools
pnpm --filter @datapulse/web test
pnpm --filter @datapulse/web typecheck
pnpm --filter @datapulse/web build
pnpm --filter @datapulse/schema exec tsc -p tsconfig.json
pnpm test:e2e
docker compose -f compose.test.yaml up -d --wait
DATAPULSE_TEST_POSTGRES_URL='postgresql+asyncpg://datapulse:datapulse@127.0.0.1:55432/datapulse' \
DATAPULSE_TEST_MYSQL_URL='mysql+asyncmy://datapulse:datapulse@127.0.0.1:53306/datapulse' \
uv run --package datapulse-server pytest apps/server/tests/connectors -m integration -v
docker compose -f compose.test.yaml down -v
docker build -t datapulse:datasource-studio .
```

Run the image with a new explicitly named volume, wait by polling `/api/health`, and verify:

```text
GET /api/health       → 200
GET /api/auth/status  → {"initialized": false}
GET /studio/setup     → DataPulse SPA
container user        → datapulse
metadata tables       → migrated inside the volume
```

Stop and remove only the named acceptance container and volume. Then run Python 3.14 tests in an isolated uv environment and verify `git status --short` is empty after the final commit.

- [ ] **Step 8: Commit**

```bash
git add apps/server/docker-entrypoint.sh Dockerfile compose.yaml .dockerignore \
  .gitignore .env.example .github/workflows/ci.yml \
  apps/web/package.json apps/web/vite.config.ts apps/web/playwright.config.ts \
  apps/web/e2e tools/prepare_e2e.py package.json README.md pnpm-lock.yaml
git commit -m "chore: deliver authenticated datasource studio"
```

---

## Completion Criteria

The plan is complete only when:

- a fresh volume migrates and produces one secure administrator setup flow;
- every `/api/admin/*` route requires a valid Session and every mutation requires CSRF;
- plaintext administrator or database passwords appear in neither storage, logs, nor responses;
- SQLite, PostgreSQL, and MySQL/MariaDB pass the same connector contract;
- SQL safety rejects every dangerous test before connector execution;
- timeout, row, and concurrency limits are enforced and diagnosed;
- the Notion-style Studio supports datasource CRUD, test connection, Schema browsing, SQL debugging, dataset save, and preview;
- unit, integration, E2E, Python 3.13/3.14, TypeScript, contract drift, and Docker gates pass;
- the implementation branch is clean and each task is represented by one focused commit.
