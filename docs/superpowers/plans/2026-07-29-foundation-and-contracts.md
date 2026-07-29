# DataPulse Foundation and Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a bootable DataPulse monorepo with a tested FastAPI service, a tested Vue shell, versioned Python contract models, generated JSON Schema and TypeScript types, and a reproducible Docker/CI workflow.

**Architecture:** Python Pydantic models are the source of truth for DataPulse's six long-lived protocols. A deterministic generator exports JSON Schema and TypeScript declarations consumed by the Vue application and future plugin/embed SDKs. The first deliverable has no data connectors or editor behavior; it establishes the boundaries those subsystems must depend on.

**Tech Stack:** Python 3.13, uv, FastAPI, Pydantic, pytest, Vue 3, TypeScript, Vite, Pinia, Vitest, pnpm, Docker, GitHub Actions.

## Global Constraints

- License the repository under Apache-2.0.
- Use Python 3.13 as the dependency-lock baseline and verify Python 3.14 in CI.
- Use Vue 3, TypeScript, and Vite for the Web application.
- Keep the backend a modular monolith; do not introduce Redis, Celery, Kafka, Kubernetes, or microservices.
- Keep protocol models versioned and generate consumer artifacts deterministically.
- Do not implement multi-user collaboration, organization structures, template/plugin marketplaces, ETL, 3D/GIS, or fine-grained data permissions.
- AI, queries, plugins, and embedding must use the same versioned protocol package rather than private duplicate types.
- Do not add product features from later subsystem plans to this foundation plan.

## Plan Boundary

This is the first independently testable subsystem plan. Later plans, created only after this one passes its acceptance gate, will cover:

1. Data sources, datasets, query safety, DuckDB, and caching.
2. Component runtime and built-in ECharts components.
3. Screen editor and draft persistence.
4. Publishing, player, Embed Ticket, and Embed SDK.
5. AI analysis, chart generation, embedded Q&A, and screen generation.
6. Scheduling, plugin loading, import/export, and release hardening.

## Planned File Structure

```text
.
├── .editorconfig
├── .gitignore
├── .github/workflows/ci.yml
├── LICENSE
├── README.md
├── Dockerfile
├── compose.yaml
├── package.json
├── pnpm-workspace.yaml
├── pyproject.toml
├── apps
│   ├── server
│   │   ├── pyproject.toml
│   │   ├── src/datapulse
│   │   │   ├── __init__.py
│   │   │   ├── app.py
│   │   │   ├── settings.py
│   │   │   ├── static.py
│   │   │   └── contracts
│   │   │       ├── __init__.py
│   │   │       ├── ai.py
│   │   │       ├── chart.py
│   │   │       ├── common.py
│   │   │       ├── dashboard.py
│   │   │       ├── dataset.py
│   │   │       ├── embed.py
│   │   │       └── plugin.py
│   │   └── tests
│   │       ├── contracts
│   │       │   ├── test_ai.py
│   │       │   ├── test_chart.py
│   │       │   ├── test_dashboard.py
│   │       │   ├── test_dataset.py
│   │       │   ├── test_embed.py
│   │       │   └── test_plugin.py
│   │       ├── test_app.py
│   │       └── test_static.py
│   └── web
│       ├── index.html
│       ├── package.json
│       ├── tsconfig.json
│       ├── vite.config.ts
│       └── src
│           ├── App.test.ts
│           ├── App.vue
│           ├── main.ts
│           ├── env.d.ts
│           ├── lib/api.ts
│           └── styles/base.css
├── packages
│   └── schema
│       ├── package.json
│       ├── schemas
│       └── src
│           ├── generated
│           └── index.ts
└── tools
    ├── check_generated.py
    ├── export_schemas.py
    └── generate_types.mjs
```

The root owns workspace commands. `apps/server` owns runtime Python code. `apps/web` owns the authoring shell. `packages/schema` contains generated public artifacts only. `tools` contains deterministic generators and checks.

---

### Task 1: Repository Foundation and FastAPI Health Contract

**Files:**
- Create: `.editorconfig`
- Create: `.gitignore`
- Create: `LICENSE`
- Create: `pyproject.toml`
- Create: `apps/server/pyproject.toml`
- Create: `apps/server/src/datapulse/__init__.py`
- Create: `apps/server/src/datapulse/settings.py`
- Create: `apps/server/src/datapulse/app.py`
- Create: `apps/server/tests/test_app.py`

**Interfaces:**
- Produces: `datapulse.app.create_app(settings: Settings | None = None) -> FastAPI`
- Produces: `datapulse.settings.Settings`
- Produces: `GET /api/health -> {"status": "ok", "version": str}`

- [ ] **Step 1: Create root workspace metadata**

Create a root `pyproject.toml` with the uv workspace and shared tool configuration:

```toml
[tool.uv.workspace]
members = ["apps/server"]

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]

[tool.pytest.ini_options]
testpaths = ["apps/server/tests"]
```

Create `.editorconfig` with UTF-8, LF, final newline, two spaces for JSON/YAML/TypeScript/Vue, and four spaces for Python. Create `.gitignore` covering `.venv`, `__pycache__`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, `node_modules`, `dist`, `.env`, `data`, and generated coverage output.

Create `LICENSE` using the unmodified Apache License 2.0 text from `https://www.apache.org/licenses/LICENSE-2.0.txt`.

- [ ] **Step 2: Declare the server package**

Create `apps/server/pyproject.toml`:

```toml
[project]
name = "datapulse-server"
version = "0.1.0"
requires-python = ">=3.13,<3.15"
dependencies = [
  "fastapi>=0.115,<1",
  "pydantic-settings>=2.7,<3",
  "uvicorn[standard]>=0.34,<1",
]

[dependency-groups]
dev = [
  "httpx>=0.28,<1",
  "pytest>=8.3,<9",
  "pytest-cov>=6,<8",
  "ruff>=0.9,<1",
]

[build-system]
requires = ["hatchling>=1.27,<2"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/datapulse"]
```

Run `uv sync --all-packages --group dev` to create `.venv` and `uv.lock`. Do not request or accept prerelease packages.

- [ ] **Step 3: Write the failing health endpoint test**

Create `apps/server/tests/test_app.py`:

```python
from fastapi.testclient import TestClient

from datapulse.app import create_app
from datapulse.settings import Settings


def test_health_returns_status_and_version() -> None:
    app = create_app(Settings(app_version="0.1.0", environment="test"))
    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}
```

- [ ] **Step 4: Run the focused test and verify the intended failure**

Run:

```bash
uv run --package datapulse-server pytest apps/server/tests/test_app.py -v
```

Expected: FAIL during collection because `datapulse.app` and `datapulse.settings` do not exist.

- [ ] **Step 5: Implement settings and application factory**

Create `apps/server/src/datapulse/settings.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DATAPULSE_", extra="ignore")

    app_name: str = "DataPulse"
    app_version: str = "0.1.0"
    environment: str = "development"
```

Create `apps/server/src/datapulse/app.py`:

```python
from fastapi import FastAPI

from datapulse.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or Settings()
    app = FastAPI(title=resolved.app_name, version=resolved.app_version)

    @app.get("/api/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": resolved.app_version}

    return app


app = create_app()
```

Set `__version__ = "0.1.0"` in `apps/server/src/datapulse/__init__.py`.

- [ ] **Step 6: Verify backend quality gates**

Run:

```bash
uv run --package datapulse-server pytest apps/server/tests/test_app.py -v
uv run --package datapulse-server ruff check apps/server
uv run --package datapulse-server ruff format --check apps/server
```

Expected: one test passes; Ruff reports no errors or formatting changes.

- [ ] **Step 7: Commit**

```bash
git add .editorconfig .gitignore LICENSE pyproject.toml uv.lock apps/server
git commit -m "chore: bootstrap DataPulse backend"
```

---

### Task 2: Vue Application Shell

**Files:**
- Create: `package.json`
- Create: `pnpm-workspace.yaml`
- Create: `apps/web/package.json`
- Create: `apps/web/index.html`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/vite.config.ts`
- Create: `apps/web/src/env.d.ts`
- Create: `apps/web/src/main.ts`
- Create: `apps/web/src/App.vue`
- Create: `apps/web/src/App.test.ts`
- Create: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/styles/base.css`

**Interfaces:**
- Consumes: `GET /api/health`
- Produces: `getHealth(): Promise<{status: string; version: string}>`
- Produces: a buildable Vue SPA that displays server reachability

- [ ] **Step 1: Define the pnpm workspace**

Create `pnpm-workspace.yaml`:

```yaml
packages:
  - apps/web
  - packages/*
```

Create the root `package.json`:

```json
{
  "name": "datapulse",
  "private": true,
  "packageManager": "pnpm@10",
  "scripts": {
    "dev:web": "pnpm --filter @datapulse/web dev",
    "test:web": "pnpm --filter @datapulse/web test",
    "typecheck:web": "pnpm --filter @datapulse/web typecheck",
    "build:web": "pnpm --filter @datapulse/web build"
  }
}
```

- [ ] **Step 2: Define the Web package**

Create `apps/web/package.json` with:

```json
{
  "name": "@datapulse/web",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "test": "vitest run",
    "typecheck": "vue-tsc --noEmit",
    "build": "vue-tsc --noEmit && vite build"
  },
  "dependencies": {
    "pinia": "^3.0.0",
    "vue": "^3.5.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^6.0.0",
    "@vue/test-utils": "^2.4.0",
    "happy-dom": "^18.0.0",
    "typescript": "^5.8.0",
    "vite": "^7.0.0",
    "vitest": "^3.2.0",
    "vue-tsc": "^3.0.0"
  }
}
```

Run `pnpm install` and commit `pnpm-lock.yaml`. If a declared major is unavailable, use the latest stable non-prerelease major that supports Node 22, update this plan's package declaration in the same commit, and preserve all scripts and APIs above.

- [ ] **Step 3: Write the failing application test**

Create `apps/web/src/App.test.ts`:

```ts
import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";

import App from "./App.vue";

afterEach(() => vi.restoreAllMocks());

test("shows the DataPulse title and backend version", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "ok", version: "0.1.0" }),
    }),
  );

  const wrapper = mount(App);
  await flushPromises();

  expect(wrapper.get("h1").text()).toBe("DataPulse");
  expect(wrapper.text()).toContain("Server 0.1.0");
});
```

- [ ] **Step 4: Run the test and verify the intended failure**

Run:

```bash
pnpm --filter @datapulse/web test
```

Expected: FAIL because `App.vue` is missing.

- [ ] **Step 5: Implement the shell and typed API helper**

Create `apps/web/src/lib/api.ts`:

```ts
export interface HealthResponse {
  status: string;
  version: string;
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch("/api/health");
  if (!response.ok) throw new Error(`Health request failed: ${response.status}`);
  return response.json() as Promise<HealthResponse>;
}
```

Implement `App.vue` with a `DataPulse` heading, the product sentence from the approved design, and three states: checking, `Server {version}`, and unavailable. Use `onMounted()` to call `getHealth()`. Add a small neutral layout in `styles/base.css`; do not create the editor UI in this task.

Create `main.ts` to install Pinia and mount the app. Configure Vite to proxy `/api` to `http://127.0.0.1:8000` in development and configure Vitest with `happy-dom`.

- [ ] **Step 6: Verify Web quality gates**

Run:

```bash
pnpm --filter @datapulse/web test
pnpm --filter @datapulse/web typecheck
pnpm --filter @datapulse/web build
```

Expected: the application test passes, type checking succeeds, and `apps/web/dist` is created.

- [ ] **Step 7: Commit**

```bash
git add package.json pnpm-workspace.yaml pnpm-lock.yaml apps/web
git commit -m "feat: add DataPulse web shell"
```

---

### Task 3: Dashboard, Chart, Dataset, and AI Contracts

**Files:**
- Create: `apps/server/src/datapulse/contracts/common.py`
- Create: `apps/server/src/datapulse/contracts/dashboard.py`
- Create: `apps/server/src/datapulse/contracts/chart.py`
- Create: `apps/server/src/datapulse/contracts/dataset.py`
- Create: `apps/server/src/datapulse/contracts/ai.py`
- Create: `apps/server/tests/contracts/test_dashboard.py`
- Create: `apps/server/tests/contracts/test_chart.py`
- Create: `apps/server/tests/contracts/test_dataset.py`
- Create: `apps/server/tests/contracts/test_ai.py`

**Interfaces:**
- Produces: `DashboardDocument`, `ComponentInstance`, `Canvas`, `Geometry`
- Produces: `ChartSpec`, `Measure`, `Filter`, `Sort`
- Produces: `DatasetDefinition`, `QueryDefinition`, `CachePolicy`, `RefreshPolicy`
- Produces: `AnalysisPlan`
- All top-level contracts expose `schema_version: Literal[1]`

- [ ] **Step 1: Write failing contract tests**

Create tests that instantiate each top-level model and assert:

```python
assert model.schema_version == 1
assert type(model).model_validate_json(model.model_dump_json()) == model
```

Use these exact fixtures:

- Dashboard: 1920×1080 canvas and one `echarts.line` component at `(100, 80, 600, 360)`.
- Chart: dataset `sales`, dimension `month`, `sum(amount)`, line visual.
- Dataset: SQL query `SELECT month, amount FROM sales`, `max_rows=5000`, `timeout_seconds=30`.
- Analysis plan: question `按月份汇总销售额`, dataset `sales`, dimension `month`, measure `amount`, aggregation `sum`, chart type `line`.

Add negative assertions:

- Canvas width and height must be positive.
- Component IDs must be unique in one DashboardDocument.
- Chart limit must be between 1 and 5,000.
- SQL query definitions must contain non-empty text.
- AnalysisPlan must reference at least one dataset.

- [ ] **Step 2: Run tests and verify the intended failure**

Run:

```bash
uv run --package datapulse-server pytest apps/server/tests/contracts/test_dashboard.py apps/server/tests/contracts/test_chart.py apps/server/tests/contracts/test_dataset.py apps/server/tests/contracts/test_ai.py -v
```

Expected: FAIL during collection because the contract modules do not exist.

- [ ] **Step 3: Implement shared primitives**

In `common.py`, define:

```python
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

PositiveInt = Annotated[int, Field(gt=0)]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
```

All contract types inherit `ContractModel`; unknown fields must fail validation.

- [ ] **Step 4: Implement dashboard and chart contracts**

Implement explicit enums for chart type, filter operator, sort direction, and aggregation. Use discriminated unions where variants have different fields.

`DashboardDocument` must validate unique component IDs with a Pydantic `model_validator(mode="after")`. `ComponentInstance.properties`, `style`, and `data_binding` are JSON objects. Do not type them as `Any`; use a recursive `JsonValue` alias composed of null, boolean, number, string, list, and object.

`ChartSpec` contains:

```python
schema_version: Literal[1] = 1
dataset_id: str
dimensions: tuple[str, ...] = ()
measures: tuple[Measure, ...] = ()
filters: tuple[Filter, ...] = ()
sort: tuple[Sort, ...] = ()
limit: int = Field(default=1000, ge=1, le=5000)
visual: VisualSpec
```

- [ ] **Step 5: Implement dataset and AI contracts**

Use a discriminated `QueryDefinition` union with variants `table`, `sql`, `file`, and `rest`. Define cache modes `disabled`, `ttl`, and `scheduled`. Define refresh modes `manual`, `interval`, and `cron`.

`AnalysisPlan` contains the original question, dataset IDs, dimensions, measures, filters, sort, recommended chart type, assumptions, and `requires_confirmation`. It must not contain executable Python or JavaScript fields.

Use these exact top-level shapes:

```python
class DatasetDefinition(ContractModel):
    schema_version: Literal[1] = 1
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    data_source_id: str | None = None
    query: QueryDefinition
    fields: tuple[DatasetField, ...] = ()
    parameters: tuple[DatasetParameter, ...] = ()
    cache: CachePolicy = CachePolicy()
    refresh: RefreshPolicy = RefreshPolicy()
    max_rows: int = Field(default=5000, ge=1, le=5000)
    timeout_seconds: int = Field(default=30, ge=1, le=300)


class AnalysisPlan(ContractModel):
    schema_version: Literal[1] = 1
    question: str = Field(min_length=1)
    dataset_ids: tuple[str, ...] = Field(min_length=1)
    dimensions: tuple[str, ...] = ()
    measures: tuple[Measure, ...] = ()
    filters: tuple[Filter, ...] = ()
    sort: tuple[Sort, ...] = ()
    recommended_chart: ChartType
    assumptions: tuple[str, ...] = ()
    requires_confirmation: bool = True
```

- [ ] **Step 6: Verify contract behavior and formatting**

Run:

```bash
uv run --package datapulse-server pytest apps/server/tests/contracts -v
uv run --package datapulse-server ruff check apps/server/src/datapulse/contracts apps/server/tests/contracts
uv run --package datapulse-server ruff format --check apps/server/src/datapulse/contracts apps/server/tests/contracts
```

Expected: all contract tests pass and Ruff is clean.

- [ ] **Step 7: Commit**

```bash
git add apps/server/src/datapulse/contracts apps/server/tests/contracts
git commit -m "feat: define core DataPulse contracts"
```

---

### Task 4: Plugin and Embed Contracts

**Files:**
- Create: `apps/server/src/datapulse/contracts/plugin.py`
- Create: `apps/server/src/datapulse/contracts/embed.py`
- Create: `apps/server/src/datapulse/contracts/__init__.py`
- Create: `apps/server/tests/contracts/test_plugin.py`
- Create: `apps/server/tests/contracts/test_embed.py`

**Interfaces:**
- Produces: `PluginManifest`
- Produces: `EmbedTicketClaims`
- Produces: `EmbedMessage` discriminated union
- Produces: `CONTRACT_MODELS: dict[str, type[ContractModel]]`

- [ ] **Step 1: Write failing plugin tests**

Test a manifest with:

```python
{
    "schema_version": 1,
    "id": "com.example.status-card",
    "version": "1.2.0",
    "compatible_api": ">=1.0.0,<2.0.0",
    "name": "Status Card",
    "entry": "bundle.mjs",
    "components": [{
        "type": "example.status-card",
        "name": "Status Card",
        "category": "indicator",
        "property_schema": {"type": "object"},
        "data_schema": {"type": "object"}
    }]
}
```

Assert that IDs use lowercase reverse-domain syntax, versions use `major.minor.patch`, entries are relative `.mjs` paths, and duplicate component types fail validation.

- [ ] **Step 2: Write failing embed tests**

Test `EmbedTicketClaims` with:

- issuer `datapulse`
- audience `datapulse-embed`
- dashboard ID and published version ID
- allowed origin `https://host.example.com`
- expiration later than issued-at
- `ai_enabled=True`
- JSON parameters

Test each message variant: `ready`, `refresh`, `setParameters`, `getParameters`, `fullscreen`, `exportImage`, `error`, and `aiQuestion`. Assert unknown message types and wildcard origins fail validation.

- [ ] **Step 3: Run tests and verify the intended failure**

Run:

```bash
uv run --package datapulse-server pytest apps/server/tests/contracts/test_plugin.py apps/server/tests/contracts/test_embed.py -v
```

Expected: FAIL during collection because `plugin.py` and `embed.py` do not exist.

- [ ] **Step 4: Implement plugin contracts**

Implement `PluginManifest` with tuple-based immutable components and validators for IDs, semantic versions, duplicate component types, and safe relative entry paths. Reject absolute paths and any path containing `..`.

Use these public fields:

```python
class PluginComponent(ContractModel):
    type: str
    name: str
    category: str
    property_schema: dict[str, JsonValue]
    data_schema: dict[str, JsonValue]


class PluginManifest(ContractModel):
    schema_version: Literal[1] = 1
    id: str
    version: str
    compatible_api: str
    name: str
    entry: str
    components: tuple[PluginComponent, ...] = Field(min_length=1)
```

Use compiled regular expressions for reverse-domain IDs and semantic versions. Validate `compatible_api` with `packaging.specifiers.SpecifierSet`; add `packaging>=24,<27` as a direct server dependency.

- [ ] **Step 5: Implement embed contracts**

Implement `EmbedTicketClaims` as data-only claims; signing occurs in the later embedding plan. Require HTTPS origins except `http://localhost` and `http://127.0.0.1` for development. Reject `"*"`.

Implement `EmbedMessage` as a Pydantic discriminated union on `type`. `setParameters` and `aiQuestion` carry request IDs so the host can correlate responses.

Use these common shapes:

```python
class EmbedTicketClaims(ContractModel):
    schema_version: Literal[1] = 1
    issuer: str = "datapulse"
    audience: str = "datapulse-embed"
    dashboard_id: str
    published_version_id: str
    allowed_origin: str
    issued_at: datetime
    expires_at: datetime
    ai_enabled: bool = False
    parameters: dict[str, JsonValue] = Field(default_factory=dict)


class ReadyMessage(ContractModel):
    type: Literal["ready"]


class SetParametersMessage(ContractModel):
    type: Literal["setParameters"]
    request_id: str
    parameters: dict[str, JsonValue]


class AiQuestionMessage(ContractModel):
    type: Literal["aiQuestion"]
    request_id: str
    question: str = Field(min_length=1)


EmbedMessage = Annotated[
    ReadyMessage
    | RefreshMessage
    | SetParametersMessage
    | GetParametersMessage
    | FullscreenMessage
    | ExportImageMessage
    | ErrorMessage
    | AiQuestionMessage,
    Field(discriminator="type"),
]


class EmbedMessageEnvelope(RootModel[EmbedMessage]):
    pass
```

Use `Field(default_factory=dict)` rather than a mutable literal when implementing `parameters`.

- [ ] **Step 6: Export the contract registry**

Create `contracts/__init__.py` and expose:

```python
CONTRACT_MODELS = {
    "analysis-plan": AnalysisPlan,
    "chart-spec": ChartSpec,
    "dashboard-document": DashboardDocument,
    "dataset-definition": DatasetDefinition,
    "embed-message": EmbedMessageEnvelope,
    "embed-ticket-claims": EmbedTicketClaims,
    "plugin-manifest": PluginManifest,
}
```

Use an `EmbedMessageEnvelope` root model for schema generation of the union.

- [ ] **Step 7: Verify and commit**

Run:

```bash
uv run --package datapulse-server pytest apps/server/tests/contracts -v
uv run --package datapulse-server ruff check apps/server
uv run --package datapulse-server ruff format --check apps/server
```

Expected: all contract tests pass and Ruff is clean.

Commit:

```bash
git add apps/server/src/datapulse/contracts apps/server/tests/contracts
git commit -m "feat: define plugin and embed contracts"
```

---

### Task 5: Deterministic JSON Schema and TypeScript Generation

**Files:**
- Modify: `apps/server/pyproject.toml`
- Modify: `apps/web/package.json`
- Modify: `package.json`
- Modify: `pnpm-workspace.yaml`
- Create: `apps/server/tests/contracts/test_exported_schemas.py`
- Create: `packages/schema/package.json`
- Create: `packages/schema/tsconfig.json`
- Create: `packages/schema/src/index.ts`
- Create: `apps/web/src/contracts.ts`
- Create: `tools/export_schemas.py`
- Create: `tools/generate_types.mjs`
- Create: `tools/check_generated.py`
- Generate: `packages/schema/schemas/*.schema.json`
- Generate: `packages/schema/src/generated/*.d.ts`

**Interfaces:**
- Consumes: `datapulse.contracts.CONTRACT_MODELS`
- Produces: `pnpm generate:contracts`
- Produces: `pnpm check:contracts`
- Produces: `@datapulse/schema`

- [ ] **Step 1: Write the failing generated-artifact check**

Create `tools/check_generated.py` that:

1. Runs `tools/export_schemas.py`.
2. Runs `node tools/generate_types.mjs`.
3. Runs `git diff --exit-code -- packages/schema`.
4. Exits non-zero if generation changed tracked artifacts.

Use this process structure:

```python
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run(*command: str) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


if __name__ == "__main__":
    run(sys.executable, "tools/export_schemas.py")
    run("node", "tools/generate_types.mjs")
    run("git", "diff", "--exit-code", "--", "packages/schema")
```

Before adding generators, run:

```bash
uv run python tools/check_generated.py
```

Expected: FAIL because generator files and schema output do not exist.

- [ ] **Step 2: Implement deterministic JSON Schema export**

`tools/export_schemas.py` must:

- Import `CONTRACT_MODELS`.
- Delete only existing `*.schema.json` files inside `packages/schema/schemas`.
- Call `model_json_schema(mode="validation")`.
- Add `$id` equal to `https://datapulse.dev/schemas/v1/{name}.schema.json`.
- Serialize with UTF-8, sorted keys, two-space indentation, and one final newline.
- Write files in sorted registry-key order.

Add `jsonschema>=4.23,<5` to the server development dependencies. Create `apps/server/tests/contracts/test_exported_schemas.py` with a parametrized test that loads every generated schema, calls `Draft202012Validator.check_schema(schema)`, and validates the corresponding model fixture.

The exporter entry point follows this structure:

```python
import json
from pathlib import Path

from datapulse.contracts import CONTRACT_MODELS

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "packages" / "schema" / "schemas"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for old_file in OUTPUT.glob("*.schema.json"):
        old_file.unlink()
    for name, model in sorted(CONTRACT_MODELS.items()):
        schema = model.model_json_schema(mode="validation")
        schema["$id"] = f"https://datapulse.dev/schemas/v1/{name}.schema.json"
        content = json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        (OUTPUT / f"{name}.schema.json").write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Implement TypeScript generation**

Create `packages/schema/package.json`:

```json
{
  "name": "@datapulse/schema",
  "private": true,
  "type": "module",
  "exports": "./src/index.ts",
  "devDependencies": {
    "typescript": "^5.8.0"
  }
}
```

Add `json-schema-to-typescript` as a root development dependency because `tools/generate_types.mjs` is a root-owned script. The generator must enumerate sorted schema files, call `compileFromFile()` with `bannerComment: ""`, and write one `.d.ts` file per schema. `packages/schema/src/index.ts` exports every generated declaration using explicit relative paths.

Use this generator structure:

```js
import { mkdir, readdir, rm, writeFile } from "node:fs/promises";
import { basename, resolve } from "node:path";
import { compileFromFile } from "json-schema-to-typescript";

const root = resolve(import.meta.dirname, "..");
const schemaDir = resolve(root, "packages/schema/schemas");
const outputDir = resolve(root, "packages/schema/src/generated");
await mkdir(outputDir, { recursive: true });
for (const oldFile of await readdir(outputDir).catch(() => [])) {
  if (oldFile.endsWith(".d.ts")) await rm(resolve(outputDir, oldFile));
}
const schemaFiles = (await readdir(schemaDir))
  .filter((file) => file.endsWith(".schema.json"))
  .sort();
const exports = [];
for (const file of schemaFiles) {
  const name = file.replace(".schema.json", "");
  const output = await compileFromFile(resolve(schemaDir, file), { bannerComment: "" });
  await writeFile(resolve(outputDir, `${name}.d.ts`), output);
  exports.push(`export type * from "./generated/${name}";`);
}
await writeFile(resolve(root, "packages/schema/src/index.ts"), `${exports.join("\n")}\n`);
```

- [ ] **Step 4: Add workspace commands**

Add root scripts:

```json
{
  "scripts": {
    "generate:contracts": "uv run --package datapulse-server python tools/export_schemas.py && node tools/generate_types.mjs",
    "check:contracts": "uv run --package datapulse-server python tools/check_generated.py"
  },
  "devDependencies": {
    "json-schema-to-typescript": "^15.0.0"
  }
}
```

Run `pnpm install`, then `pnpm generate:contracts`.

- [ ] **Step 5: Prove TypeScript consumers can use generated types**

Create a compile-only fixture in `packages/schema/src/index.test-d.ts`:

```ts
import type { ChartSpec } from "./index";

const chart: ChartSpec = {
  schema_version: 1,
  dataset_id: "sales",
  dimensions: ["month"],
  measures: [{ field: "amount", aggregation: "sum" }],
  filters: [],
  sort: [],
  limit: 1000,
  visual: { type: "line", title: "月度销售趋势" },
};

void chart;
```

Configure `packages/schema/tsconfig.json` with `strict: true`, `noEmit: true`, and include `src/**/*.ts` plus `src/**/*.d.ts`.

Add `"@datapulse/schema": "workspace:*"` to `apps/web/package.json` and create `apps/web/src/contracts.ts`:

```ts
export type {
  AnalysisPlan,
  ChartSpec,
  DashboardDocument,
  DatasetDefinition,
  EmbedMessageEnvelope,
  EmbedTicketClaims,
  PluginManifest,
} from "@datapulse/schema";
```

Run the Web type check as part of this task to prove a real workspace consumer resolves the package.

- [ ] **Step 6: Verify deterministic generation**

Run:

```bash
pnpm generate:contracts
git add packages/schema
pnpm check:contracts
pnpm --filter @datapulse/schema exec tsc -p tsconfig.json
pnpm --filter @datapulse/web typecheck
uv run --package datapulse-server pytest apps/server/tests/contracts -v
```

Expected: generation produces no diff after staging, TypeScript compiles, and Python contract tests pass.

- [ ] **Step 7: Commit**

```bash
git add apps/server/pyproject.toml apps/web/package.json apps/web/src/contracts.ts uv.lock package.json pnpm-lock.yaml packages/schema tools
git commit -m "feat: generate shared protocol schemas"
```

---

### Task 6: Static Delivery, Docker, CI, and Foundation Acceptance

**Files:**
- Modify: `apps/server/src/datapulse/app.py`
- Create: `apps/server/src/datapulse/static.py`
- Create: `apps/server/tests/test_static.py`
- Create: `Dockerfile`
- Create: `compose.yaml`
- Create: `.dockerignore`
- Create: `.github/workflows/ci.yml`
- Create: `README.md`
- Modify: `package.json`

**Interfaces:**
- Consumes: `apps/web/dist`
- Produces: `create_spa_router(static_dir: Path) -> APIRouter`
- Produces: Docker image exposing port `8000`
- Produces: CI checks `backend`, `web`, `contracts`, and `docker`

- [ ] **Step 1: Write failing SPA delivery tests**

Create `apps/server/tests/test_static.py`:

```python
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from datapulse.static import create_spa_router


def test_spa_serves_assets_and_falls_back_to_index(tmp_path: Path) -> None:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<h1>DataPulse</h1>", encoding="utf-8")
    (tmp_path / "assets" / "app.js").write_text("export {}", encoding="utf-8")
    app = FastAPI()
    app.include_router(create_spa_router(tmp_path))
    client = TestClient(app)

    assert client.get("/assets/app.js").text == "export {}"
    assert "DataPulse" in client.get("/screens/demo").text


def test_spa_does_not_swallow_api_404(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<h1>DataPulse</h1>", encoding="utf-8")
    app = FastAPI()
    app.include_router(create_spa_router(tmp_path))

    assert TestClient(app).get("/api/missing").status_code == 404
```

- [ ] **Step 2: Run tests and verify the intended failure**

Run:

```bash
uv run --package datapulse-server pytest apps/server/tests/test_static.py -v
```

Expected: FAIL during collection because `datapulse.static` does not exist.

- [ ] **Step 3: Implement safe SPA delivery**

Implement `create_spa_router()` so that:

- Existing files under the configured directory are served.
- Resolved asset paths must remain inside the configured directory.
- Missing non-API routes return `index.html`.
- `/api` and `/api/*` are never handled by the SPA router.
- Missing `index.html` produces a clear 404 response.

Use this routing structure:

```python
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse


def create_spa_router(static_dir: Path) -> APIRouter:
    root = static_dir.resolve()
    router = APIRouter(include_in_schema=False)

    @router.get("/{path:path}")
    def spa(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404)
        candidate = (root / path).resolve()
        if candidate.is_relative_to(root) and candidate.is_file():
            return FileResponse(candidate)
        index = root / "index.html"
        if not index.is_file():
            raise HTTPException(status_code=404, detail="Web application is not built")
        return FileResponse(index)

    return router
```

In `create_app()`, include the SPA router only when `Settings.static_dir` exists. Add `static_dir: Path | None = None` and `data_dir: Path = Path("data")` to Settings. The container overrides them with `/app/static` and `/data`.

- [ ] **Step 4: Create the production image**

Use a multi-stage `Dockerfile`:

1. Node 22 stage runs `corepack enable`, `pnpm install --frozen-lockfile`, and `pnpm build:web`.
2. Python 3.13 slim stage installs uv, runs `uv sync --frozen --no-dev --package datapulse-server`, copies the Web build to `/app/static`, creates an unprivileged `datapulse` user, declares `/data` as the persistent directory, and starts:

```text
uv run --no-sync uvicorn datapulse.app:app --host 0.0.0.0 --port 8000
```

Set environment variables:

```text
DATAPULSE_ENVIRONMENT=production
DATAPULSE_STATIC_DIR=/app/static
DATAPULSE_DATA_DIR=/data
```

The Dockerfile must follow this concrete shape, with the resolved lock-file installation command corrected during implementation if uv requires a workspace-specific flag:

```dockerfile
FROM node:22-slim AS web
WORKDIR /src
RUN corepack enable
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY apps/web/package.json apps/web/package.json
COPY packages/schema/package.json packages/schema/package.json
RUN pnpm install --frozen-lockfile
COPY apps/web apps/web
COPY packages/schema packages/schema
RUN pnpm build:web

FROM python:3.13-slim AS runtime
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
COPY apps/server apps/server
RUN uv sync --frozen --no-dev --package datapulse-server
COPY --from=web /src/apps/web/dist /app/static
RUN useradd --create-home --uid 10001 datapulse && mkdir /data && chown datapulse:datapulse /data
USER datapulse
ENV DATAPULSE_ENVIRONMENT=production \
    DATAPULSE_STATIC_DIR=/app/static \
    DATAPULSE_DATA_DIR=/data
EXPOSE 8000
VOLUME ["/data"]
CMD ["uv", "run", "--no-sync", "uvicorn", "datapulse.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

Create `compose.yaml` with one `datapulse` service, port `8000:8000`, a named `datapulse-data` volume, and a health check against `/api/health`.

- [ ] **Step 5: Add root verification scripts and CI**

Add root scripts:

```json
{
  "scripts": {
    "test": "pnpm test:web && uv run --package datapulse-server pytest",
    "typecheck": "pnpm typecheck:web && pnpm --filter @datapulse/schema exec tsc -p tsconfig.json",
    "build": "pnpm build:web",
    "verify": "pnpm check:contracts && pnpm test && pnpm typecheck && pnpm build"
  }
}
```

Create `.github/workflows/ci.yml` triggered by pushes and pull requests. Use Node 22, pnpm 10, Python 3.13, and uv. Run:

```text
uv sync --all-packages --group dev --frozen
pnpm install --frozen-lockfile
pnpm verify
uv run --package datapulse-server ruff check apps/server
uv run --package datapulse-server ruff format --check apps/server
docker build -t datapulse:test .
```

Add a separate Python 3.14 compatibility job that runs backend tests and contract generation without building Docker.

- [ ] **Step 6: Write exact local usage documentation**

README must contain:

- Product vision and current foundation-only status.
- Prerequisites: Git, uv, Node 22, pnpm 10, Docker.
- Backend command: `uv run --package datapulse-server uvicorn datapulse.app:app --reload`.
- Web command: `pnpm dev:web`.
- Full verification command: `pnpm verify`.
- Container command: `docker compose up --build`.
- Architecture link to the approved design document.
- Statement that data sources, editor, embedding, and AI arrive in later plans.

- [ ] **Step 7: Run the complete foundation acceptance gate**

Run from the repository root:

```bash
pnpm generate:contracts
pnpm check:contracts
uv run --package datapulse-server pytest -v
uv run --package datapulse-server ruff check apps/server
uv run --package datapulse-server ruff format --check apps/server
pnpm --filter @datapulse/web test
pnpm --filter @datapulse/web typecheck
pnpm --filter @datapulse/web build
pnpm --filter @datapulse/schema exec tsc -p tsconfig.json
docker build -t datapulse:foundation .
docker run --rm -d --name datapulse-foundation -p 18000:8000 datapulse:foundation
curl --fail http://127.0.0.1:18000/api/health
curl --fail http://127.0.0.1:18000/
docker stop datapulse-foundation
git status --short
```

Expected:

- Contract generation makes no tracked changes.
- All Python and Web tests pass.
- Ruff, TypeScript, and Vue checks pass.
- Docker image builds.
- Health endpoint returns `{"status":"ok","version":"0.1.0"}`.
- Root URL contains `DataPulse`.
- Final `git status --short` is empty.

If the container fails before `docker stop`, stop and remove only the explicitly named `datapulse-foundation` container before retrying.

- [ ] **Step 8: Commit**

```bash
git add apps/server Dockerfile compose.yaml .dockerignore .github README.md package.json
git commit -m "chore: add reproducible foundation delivery"
```

## Completion Criteria

The plan is complete only when:

- A clean checkout can install dependencies using frozen lock files.
- FastAPI health and SPA routes pass tests.
- All six long-lived protocol groups have versioned Python models.
- JSON Schema and TypeScript declarations regenerate without diff.
- Vue consumes the shared schema package successfully.
- Python 3.13 is the locked baseline and Python 3.14 backend compatibility passes.
- The Docker image starts as a non-root user and serves both API and SPA.
- CI runs the same verification commands documented for local development.
- The worktree is clean after the final commit.
