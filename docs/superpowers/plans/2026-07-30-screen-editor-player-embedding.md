# DataPulse Screen Editor, Player, and Embedding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `E2` engineering flow from datasets to a drag-and-drop screen editor, draft preview, overwrite publishing, standalone playback, and secure third-party embedding.

**工程里程碑：** `E2` 编辑与交付。它主要完成产品第一阶段的编辑、预览、发布和访问基础，不等同于产品路线中的第二阶段。

**Architecture:** Keep the existing FastAPI modular monolith and Vue SPA. A versioned `DashboardDocument` is the only screen definition, and one Vue component runtime renders editor preview, standalone playback, and embedded playback. Backend screen, asset, query, publishing, display-access, and embedding services share repositories and authorization-neutral domain interfaces while exposing separate admin, display, and embed APIs.

**Tech Stack:** Python 3.13/3.14, FastAPI, Pydantic 2, SQLAlchemy 2 async, Alembic, SQLGlot, PyJWT, cryptography, pytest; Vue 3, TypeScript, Pinia, Vue Router, Apache ECharts 6.1, vue-echarts 8.0, Moveable 0.53, Selecto 1.26, Vitest, Playwright; SQLite, PostgreSQL, MySQL/MariaDB.

## Global Constraints

- Implement against `docs/superpowers/specs/2026-07-30-screen-editor-player-embedding-design.md`.
- Create execution branch `codex/phase-2-screen-runtime` from `main` through the worktree workflow; do not implement directly on `main`.
- Keep Python `>=3.13,<3.15`, Node 22, and pnpm 10.33.0.
- Preserve the repository's existing `snake_case` JSON, Pydantic, JSON Schema, and generated TypeScript field names.
- Keep one administrator account. Do not add users, RBAC, organizations, invitations, OIDC, or collaboration.
- Keep external database access on the existing native SQLite, PostgreSQL, and MySQL/MariaDB connectors. Do not add DuckDB.
- Use one `DashboardDocument` and one component runtime for editor preview, standalone playback, and embed playback.
- Maintain only `draft_document` and `published_document`; do not add publication history or rollback tables.
- The default canvas is `1920 × 1080`; playback scales the full logical canvas proportionally and never reflows components.
- Provide exactly these type IDs: `builtin.kpi`, `builtin.text`, `builtin.image`, `builtin.table`, `builtin.line`, `builtin.bar`, `builtin.pie`, `builtin.progress`, and `builtin.geo_map`.
- Page refresh choices are disabled, 10, 30, 60, or 300 seconds. Do not add server Cron or query-result caching.
- Global parameters are the only interaction bus. Do not add an event graph, arbitrary JavaScript actions, or a filter component.
- Accept only PNG, JPEG, WebP, and valid GeoJSON `FeatureCollection` assets, with a 5 MiB limit.
- Standalone playback uses a revocable per-screen key and a 30-day sliding display session.
- Embed tickets default to one hour, never exceed eight hours, bind one screen and one exact Origin, and allow only declared mutable parameter names.
- A production `DATAPULSE_SIGNING_KEY` is URL-safe Base64 for exactly 32 random bytes.
- Keep Studio warm white and low contrast; keep the canvas theme-independent and dark by default.
- Do not implement AI calls, export, public anonymous links, playlists, device management, plugin SDK loading, or responsive breakpoints.
- Use test-driven development for each behavior: see the focused test fail, implement minimally, and see it pass.
- Regenerate and verify JSON Schema and TypeScript declarations whenever public contracts change.
- Commit after every task only after its focused tests and static checks pass.

---

### Task 1: Converge Phase-Two Public Contracts

**Files:**
- Modify: `apps/server/src/datapulse/contracts/dashboard.py`
- Modify: `apps/server/src/datapulse/contracts/chart.py`
- Modify: `apps/server/src/datapulse/contracts/embed.py`
- Modify: `apps/server/tests/contracts/test_dashboard.py`
- Modify: `apps/server/tests/contracts/test_chart.py`
- Modify: `apps/server/tests/contracts/test_embed.py`
- Modify: `packages/schema/src/index.test-d.ts`
- Regenerate: `packages/schema/schemas/*.schema.json`
- Regenerate: `packages/schema/src/generated/*.d.ts`

**Interfaces:**
- Produces: `DashboardDocument`, `ComponentInstance`, `DashboardParameter`, `ScreenRefreshPolicy`
- Produces: `ChartSpec`, `FilterValue`, `ParameterRef`
- Produces: `EmbedTicketClaims`, `EmbedMessageEnvelope`
- Consumed by every backend and frontend task below

- [ ] **Step 1: Write failing contract tests for the approved document**

```python
def test_dashboard_document_accepts_phase_two_shape() -> None:
    document = DashboardDocument.model_validate(
        {
            "canvas": {"width": 1920, "height": 1080, "background": {}},
            "theme": {"id": "datapulse-dark", "tokens": {}},
            "refresh": {"mode": "interval", "interval_seconds": 30},
            "parameters": [
                {
                    "id": "region",
                    "name": "region",
                    "data_type": "string",
                    "default": "east",
                    "mutable": True,
                }
            ],
            "components": [
                {
                    "id": "chart-1",
                    "type": "builtin.line",
                    "frame": {
                        "x": 40,
                        "y": 40,
                        "width": 640,
                        "height": 320,
                        "z_index": 1,
                    },
                    "state": {"locked": False, "hidden": False},
                    "props": {},
                    "style": {},
                    "data_binding": {},
                    "interactions": [],
                }
            ],
        }
    )
    assert document.refresh.interval_seconds == 30
    assert document.components[0].frame.z_index == 1
```

Also assert that rotation, nested components, duplicate IDs, unsupported refresh intervals, duplicate parameter names, and interactions targeting missing parameters fail validation.

- [ ] **Step 2: Run the focused contract tests and verify failure**

Run:

```bash
uv run --package datapulse-server pytest apps/server/tests/contracts/test_dashboard.py \
  apps/server/tests/contracts/test_chart.py apps/server/tests/contracts/test_embed.py -v
```

Expected: FAIL because the current contract requires `plugin` and `geometry`, lacks refresh and parameter metadata, and still exposes out-of-scope embed messages.

- [ ] **Step 3: Implement the exact v1 models**

Use strict discriminated models:

```python
class ScreenRefreshPolicy(ContractModel):
    mode: Literal["disabled", "interval"] = "disabled"
    interval_seconds: Literal[10, 30, 60, 300] | None = None


class ParameterRef(ContractModel):
    kind: Literal["parameter"] = "parameter"
    name: NonBlankStr


class LiteralValue(ContractModel):
    kind: Literal["literal"] = "literal"
    value: JsonValue = None
```

`Filter.value` is `Annotated[ParameterRef | LiteralValue, Field(discriminator="kind")]`. `EmbedTicketClaims` contains `ticket_id`, `screen_id`, `allowed_origin`, `issued_at`, `expires_at`, `parameters`, and `mutable_parameters`; remove `published_version_id` and `ai_enabled`. Remove `exportImage` and `aiQuestion` from `EmbedMessageEnvelope`, and add a `parameters` response message for `getParameters`.

- [ ] **Step 4: Regenerate and verify shared schemas**

Run:

```bash
pnpm generate:contracts
pnpm check:contracts
pnpm --filter @datapulse/schema exec tsc -p tsconfig.json
```

Update the type fixture to prove a valid `DashboardDocument`, `ChartSpec`, and `EmbedTicketClaims` compile in TypeScript.

- [ ] **Step 5: Run static and focused checks**

```bash
uv run --package datapulse-server ruff check apps/server/src/datapulse/contracts \
  apps/server/tests/contracts
uv run --package datapulse-server pytest apps/server/tests/contracts -v
```

- [ ] **Step 6: Commit**

```bash
git add apps/server/src/datapulse/contracts apps/server/tests/contracts \
  packages/schema/schemas packages/schema/src
git commit -m "feat: align phase two screen contracts"
```

---

### Task 2: Persist Screens and Expose Admin CRUD

**Files:**
- Modify: `apps/server/src/datapulse/metadata/models.py`
- Modify: `apps/server/src/datapulse/metadata/__init__.py`
- Create: `apps/server/migrations/versions/0003_screen_editor.py`
- Create: `apps/server/src/datapulse/screen/__init__.py`
- Create: `apps/server/src/datapulse/screen/models.py`
- Create: `apps/server/src/datapulse/screen/repository.py`
- Create: `apps/server/src/datapulse/screen/service.py`
- Create: `apps/server/src/datapulse/screen/api.py`
- Modify: `apps/server/src/datapulse/lifespan.py`
- Modify: `apps/server/src/datapulse/app.py`
- Create: `apps/server/tests/screen/conftest.py`
- Create: `apps/server/tests/screen/test_repository.py`
- Create: `apps/server/tests/screen/test_service.py`
- Create: `apps/server/tests/screen/test_api.py`
- Modify: `apps/server/tests/metadata/test_migrations.py`

**Interfaces:**
- Produces: `ScreenRepository`
- Produces: `ScreenService.create/list/get/save_draft/copy/delete`
- Produces admin routes under `/api/admin/screens`
- Produces `ScreenResponse` with `draft_revision` and nullable `published_document`

- [ ] **Step 1: Write failing migration and repository tests**

```python
async def test_save_draft_requires_matching_revision(
    screen_repository: ScreenRepository,
) -> None:
    created = await screen_repository.create("Operations", empty_document())
    saved = await screen_repository.save_draft(
        created.id,
        document=document_with_text("Live"),
        expected_revision=0,
    )
    assert saved.draft_revision == 1
    with pytest.raises(ScreenRevisionConflict):
        await screen_repository.save_draft(
            created.id,
            document=document_with_text("Stale"),
            expected_revision=0,
        )
```

Migration assertions must include `screen` with unique `name`, JSON draft/published columns, integer revision, and UTC timestamps.

- [ ] **Step 2: Run tests and verify missing screen domain**

```bash
uv run --package datapulse-server pytest apps/server/tests/screen \
  apps/server/tests/metadata/test_migrations.py -v
```

Expected: FAIL during import because `datapulse.screen` and `ScreenRecord` do not exist.

- [ ] **Step 3: Implement persistence and service interfaces**

Use:

```python
class ScreenService:
    async def create(self, data: ScreenCreate) -> ScreenResponse: ...
    async def list(self) -> tuple[ScreenSummary, ...]: ...
    async def get(self, screen_id: str) -> ScreenResponse: ...
    async def save_draft(
        self,
        screen_id: str,
        data: ScreenDraftUpdate,
    ) -> ScreenResponse: ...
    async def copy(self, screen_id: str) -> ScreenResponse: ...
    async def delete(self, screen_id: str) -> None: ...
```

`copy()` deep-copies the draft, rewrites every component ID and interaction source ID, appends `副本` with a conflict-free numeric suffix, and leaves `published_document` null.

- [ ] **Step 4: Add authenticated CRUD routes**

Routes:

```text
GET    /api/admin/screens
POST   /api/admin/screens
GET    /api/admin/screens/{screen_id}
PATCH  /api/admin/screens/{screen_id}
POST   /api/admin/screens/{screen_id}/copy
DELETE /api/admin/screens/{screen_id}
```

All writes depend on `require_csrf`; all routes depend on `require_admin`. Map not-found, name-conflict, invalid-document, and revision-conflict errors to stable 404, 409, 422, and 409 responses.

- [ ] **Step 5: Wire lifespan and run focused verification**

```bash
uv run --package datapulse-server pytest apps/server/tests/screen \
  apps/server/tests/metadata -v
uv run --package datapulse-server ruff check apps/server
```

- [ ] **Step 6: Commit**

```bash
git add apps/server/src/datapulse/metadata apps/server/src/datapulse/screen \
  apps/server/src/datapulse/lifespan.py apps/server/src/datapulse/app.py \
  apps/server/migrations/versions/0003_screen_editor.py \
  apps/server/tests/screen apps/server/tests/metadata
git commit -m "feat: add screen draft persistence"
```

---

### Task 3: Add Safe Image and GeoJSON Assets

**Files:**
- Modify: `apps/server/pyproject.toml`
- Modify: `uv.lock`
- Modify: `apps/server/src/datapulse/settings.py`
- Modify: `apps/server/src/datapulse/metadata/models.py`
- Modify: `apps/server/src/datapulse/metadata/__init__.py`
- Create: `apps/server/migrations/versions/0004_screen_assets.py`
- Create: `apps/server/src/datapulse/screen/assets.py`
- Create: `apps/server/src/datapulse/screen/asset_api.py`
- Modify: `apps/server/src/datapulse/lifespan.py`
- Modify: `apps/server/src/datapulse/app.py`
- Create: `apps/server/tests/screen/test_assets.py`
- Modify: `apps/server/tests/metadata/test_migrations.py`

**Interfaces:**
- Produces: `AssetService.upload/get/delete/assert_references_exist`
- Produces: `ScreenAssetResponse`
- Produces admin routes under `/api/admin/assets`
- Consumed by image, map, publish, standalone, and embed tasks

- [ ] **Step 1: Write failing validation and path-safety tests**

```python
async def test_geojson_upload_rejects_non_feature_collection(
    asset_service: AssetService,
) -> None:
    with pytest.raises(AssetInvalid, match="FeatureCollection"):
        await asset_service.upload(
            filename="../../map.geojson",
            content_type="application/geo+json",
            content=b'{"type":"Point","coordinates":[0,0]}',
        )


async def test_upload_uses_generated_path(
    asset_service: AssetService,
    assets_dir: Path,
) -> None:
    asset = await asset_service.upload(
        filename="../../logo.png",
        content_type="image/png",
        content=PNG_BYTES,
    )
    assert Path(asset.storage_path).parent == assets_dir
    assert ".." not in Path(asset.storage_path).parts
```

Also test the 5 MiB boundary, unsupported SVG rejection, content hash, and deletion conflict when a draft or published document references an asset.

- [ ] **Step 2: Run tests and verify failure**

```bash
uv run --package datapulse-server pytest apps/server/tests/screen/test_assets.py -v
```

Expected: FAIL because asset models and service do not exist.

- [ ] **Step 3: Add multipart support, persistence, and storage**

```bash
uv add --package datapulse-server "python-multipart>=0.0.20,<1"
```

Add `Settings.resolved_assets_dir() -> Path`, defaulting to `data_dir / "assets"`. Store only generated UUID filenames. Parse GeoJSON before persistence and require:

```python
payload.get("type") == "FeatureCollection" and isinstance(payload.get("features"), list)
```

- [ ] **Step 4: Add admin asset APIs**

```text
POST   /api/admin/assets
GET    /api/admin/assets/{asset_id}
DELETE /api/admin/assets/{asset_id}
```

Use `UploadFile`, stream at most 5 MiB plus one byte, return `413 ASSET_TOO_LARGE`, and serve files with `Content-Disposition: inline`, `X-Content-Type-Options: nosniff`, and immutable ETag based on SHA-256.

- [ ] **Step 5: Run focused verification and commit**

```bash
uv run --package datapulse-server pytest apps/server/tests/screen/test_assets.py \
  apps/server/tests/metadata/test_migrations.py -v
uv run --package datapulse-server ruff check apps/server
git add apps/server/pyproject.toml uv.lock apps/server/src/datapulse/settings.py \
  apps/server/src/datapulse/metadata apps/server/src/datapulse/screen \
  apps/server/src/datapulse/lifespan.py apps/server/src/datapulse/app.py \
  apps/server/migrations/versions/0004_screen_assets.py apps/server/tests
git commit -m "feat: add screen asset storage"
```

---

### Task 4: Compile ChartSpec and Execute Authorized Component Queries

**Files:**
- Create: `apps/server/src/datapulse/screen/chart_query.py`
- Create: `apps/server/src/datapulse/screen/runtime.py`
- Create: `apps/server/src/datapulse/screen/runtime_api.py`
- Modify: `apps/server/src/datapulse/lifespan.py`
- Modify: `apps/server/src/datapulse/app.py`
- Create: `apps/server/tests/screen/test_chart_query.py`
- Create: `apps/server/tests/screen/test_runtime.py`
- Create: `apps/server/tests/screen/test_runtime_api.py`

**Interfaces:**
- Produces: `ChartQueryCompiler.compile(spec, dataset, parameters) -> QueryRequest`
- Produces: `ScreenRuntimeService.query_draft_component(...)`
- Produces: `ScreenRuntimeService.query_published_component(...)`
- Produces admin endpoint `POST /api/admin/screens/{screen_id}/query`

- [ ] **Step 1: Write failing compiler tests**

```python
def test_compiler_wraps_dataset_and_binds_filter_values() -> None:
    compiled = compiler.compile(
        spec=line_spec(
            filters=(
                Filter(
                    field="region",
                    operator="equals",
                    value=ParameterRef(name="region"),
                ),
            )
        ),
        dataset=sql_dataset("SELECT month, amount, region FROM sales"),
        parameters={"region": "east"},
    )
    assert compiled.sql.startswith("SELECT")
    assert "FROM (SELECT month, amount, region FROM sales)" in compiled.sql
    assert compiled.parameters["chart_filter_0"] == "east"
    assert "east" not in compiled.sql
```

Test unknown fields, missing parameters, aggregation aliases, sort, limits, `IN`, `BETWEEN`, null operators, and invalid visual/spec combinations.

- [ ] **Step 2: Run tests and verify failure**

```bash
uv run --package datapulse-server pytest apps/server/tests/screen/test_chart_query.py -v
```

Expected: FAIL because `ChartQueryCompiler` does not exist.

- [ ] **Step 3: Implement SQLGlot outer-query compilation**

Validate every dimension, measure, filter, and sort field against `DatasetDefinition.fields`. Wrap the existing read-only dataset SQL as `dataset_source`; never interpolate a value. Generate collision-free bind names `chart_filter_0`, `chart_filter_1`, and merge existing dataset parameter defaults with validated global parameters.

```python
class ChartQueryCompiler:
    def compile(
        self,
        spec: ChartSpec,
        dataset: DatasetDefinition,
        parameters: Mapping[str, JsonValue],
    ) -> QueryRequest:
        ...
```

- [ ] **Step 4: Authorize by stored document and component ID**

The browser sends only:

```python
class ComponentQueryRequest(ContractModel):
    component_id: NonBlankStr
    parameters: dict[str, JsonValue] = Field(default_factory=dict)
```

`ScreenRuntimeService` loads the draft or published document, finds the component, validates its `data_binding.chart_spec`, and compiles that stored spec. It must reject hidden or missing components and must not accept an arbitrary client-provided dataset ID or SQL.

- [ ] **Step 5: Add admin draft-query API and verify**

```bash
uv run --package datapulse-server pytest apps/server/tests/screen/test_chart_query.py \
  apps/server/tests/screen/test_runtime.py \
  apps/server/tests/screen/test_runtime_api.py -v
uv run --package datapulse-server ruff check apps/server
```

- [ ] **Step 6: Commit**

```bash
git add apps/server/src/datapulse/screen apps/server/src/datapulse/lifespan.py \
  apps/server/src/datapulse/app.py apps/server/tests/screen
git commit -m "feat: execute screen component queries"
```

---

### Task 5: Build the Screen List Workspace

**Files:**
- Create: `apps/web/src/features/screens/types.ts`
- Create: `apps/web/src/features/screens/api.ts`
- Create: `apps/web/src/features/screens/ScreenListView.vue`
- Create: `apps/web/src/features/screens/screen-list.test.ts`
- Modify: `apps/web/src/router/index.ts`
- Modify: `apps/web/src/ui/StudioShell.vue`
- Modify: `apps/web/src/styles/base.css`

**Interfaces:**
- Produces: `listScreens/createScreen/copyScreen/deleteScreen`
- Produces protected route `/studio/screens`
- Consumed by the editor task

- [ ] **Step 1: Write a failing screen-list component test**

```typescript
test("creates and copies a screen from the workspace", async () => {
  stubScreenApi([
    screenSummary({ id: "screen-1", name: "运营总览" }),
  ]);
  const wrapper = mount(ScreenListView, { global: { plugins: [router] } });
  await flushPromises();
  expect(wrapper.text()).toContain("运营总览");
  await wrapper.get('[data-action="copy-screen"]').trigger("click");
  await flushPromises();
  expect(fetch).toHaveBeenCalledWith(
    "/api/admin/screens/screen-1/copy",
    expect.objectContaining({ method: "POST" }),
  );
});
```

Also cover empty, loading, API error, create, delete confirmation, published badge, and modified timestamp.

- [ ] **Step 2: Run the test and verify failure**

```bash
pnpm --filter @datapulse/web test -- src/features/screens/screen-list.test.ts
```

- [ ] **Step 3: Implement typed API and Notion-style list**

Keep the existing warm-white shell. Use rows or restrained document cards, not dark dashboard tiles. Creation uses a small name dialog and redirects to `/studio/screens/{id}/edit`.

- [ ] **Step 4: Replace the temporary route and verify**

```bash
pnpm --filter @datapulse/web test -- src/features/screens/screen-list.test.ts \
  src/App.test.ts src/ui/studio-shell.test.ts
pnpm --filter @datapulse/web typecheck
```

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/features/screens apps/web/src/router/index.ts \
  apps/web/src/ui/StudioShell.vue apps/web/src/styles/base.css
git commit -m "feat: add screen workspace"
```

---

### Task 6: Add Editor Commands, History, and Autosave

**Files:**
- Create: `apps/web/src/features/screens/editor/commands.ts`
- Create: `apps/web/src/features/screens/editor/history.ts`
- Create: `apps/web/src/features/screens/editor/geometry.ts`
- Create: `apps/web/src/features/screens/editor/store.ts`
- Create: `apps/web/src/features/screens/editor/commands.test.ts`
- Create: `apps/web/src/features/screens/editor/store.test.ts`
- Create: `apps/web/src/features/screens/ScreenEditorView.vue`
- Modify: `apps/web/src/features/screens/api.ts`
- Modify: `apps/web/src/router/index.ts`

**Interfaces:**
- Produces: discriminated `EditorCommand`
- Produces: `applyCommand(document, command) -> DashboardDocument`
- Produces: `EditorHistory.execute/undo/redo`
- Produces: `useScreenEditorStore()` with `load`, `dispatch`, `saveNow`

- [ ] **Step 1: Write failing pure command tests**

```typescript
test("undo restores the exact document before a frame update", () => {
  const history = new EditorHistory(documentWithText());
  history.execute({
    type: "update_frame",
    component_ids: ["text-1"],
    patch: { x: 120, y: 80 },
  });
  expect(history.current.components[0].frame.x).toBe(120);
  history.undo();
  expect(history.current.components[0].frame.x).toBe(40);
});
```

Cover add, remove, duplicate, update frame, update props, update style, reorder, lock, hide, canvas, theme, and parameter commands. Commands must be immutable and reject unknown component IDs.

- [ ] **Step 2: Run tests and verify failure**

```bash
pnpm --filter @datapulse/web test -- \
  src/features/screens/editor/commands.test.ts \
  src/features/screens/editor/store.test.ts
```

- [ ] **Step 3: Implement history and store**

The store API:

```typescript
interface ScreenEditorStore {
  screen: Screen | null;
  document: DashboardDocument | null;
  selection: string[];
  saveState: "idle" | "dirty" | "saving" | "saved" | "failed" | "conflict";
  load(screenId: string): Promise<void>;
  dispatch(command: EditorCommand): void;
  undo(): void;
  redo(): void;
  saveNow(): Promise<void>;
}
```

Debounce saves by 800 ms and send `expected_revision`. On `SCREEN_REVISION_CONFLICT`, cancel pending saves, set `conflict`, and never retry silently.

- [ ] **Step 4: Add protected editor route and skeletal view**

Add `/studio/screens/:id/edit`. The skeleton contains toolbar, left panel, canvas host, and inspector regions with accessible labels, but component rendering and drag handles arrive in later tasks.

- [ ] **Step 5: Verify and commit**

```bash
pnpm --filter @datapulse/web test -- src/features/screens/editor
pnpm --filter @datapulse/web typecheck
git add apps/web/src/features/screens apps/web/src/router/index.ts
git commit -m "feat: add screen editor document state"
```

---

### Task 7: Create the Unified Component and Data Runtime

**Files:**
- Modify: `apps/web/package.json`
- Modify: `pnpm-lock.yaml`
- Create: `apps/web/src/features/runtime/types.ts`
- Create: `apps/web/src/features/runtime/registry.ts`
- Create: `apps/web/src/features/runtime/theme.ts`
- Create: `apps/web/src/features/runtime/parameters.ts`
- Create: `apps/web/src/features/runtime/dataRuntime.ts`
- Create: `apps/web/src/features/runtime/ComponentHost.vue`
- Create: `apps/web/src/features/runtime/ScreenRuntime.vue`
- Create: `apps/web/src/features/runtime/runtime.test.ts`
- Create: `apps/web/src/features/runtime/data-runtime.test.ts`

**Interfaces:**
- Produces: `ComponentDefinition` and `ComponentRegistry`
- Produces: `createDataRuntime(queryComponent)`
- Produces: `ScreenRuntime` used in editor preview, standalone, and embed routes

- [ ] **Step 1: Write failing registry and query-deduplication tests**

```typescript
test("shares equal bindings and parameters within one refresh cycle", async () => {
  const query = vi.fn().mockResolvedValue(queryResult());
  const runtime = createDataRuntime(query);
  const binding = chartBinding(lineSpec());
  const [first, second] = await Promise.all([
    runtime.load("a", binding, { region: "east" }),
    runtime.load("b", binding, { region: "east" }),
  ]);
  expect(first).toEqual(second);
  expect(query).toHaveBeenCalledTimes(1);
});
```

Also prove a new parameter generation ignores a slower old response and that one failed key does not reject unrelated components.

- [ ] **Step 2: Run tests and verify failure**

```bash
pnpm --filter @datapulse/web test -- src/features/runtime
```

- [ ] **Step 3: Install ECharts runtime dependencies**

```bash
pnpm add --filter @datapulse/web echarts@^6.1.0 vue-echarts@^8.0.1
```

- [ ] **Step 4: Implement runtime contracts**

```typescript
export interface ComponentDefinition {
  type: BuiltinComponentType;
  label: string;
  defaultFrame: { width: number; height: number };
  defaultProps: Record<string, JsonValue>;
  dataCapability: "none" | "single" | "table" | "series" | "geo";
  component: Component;
}
```

`ScreenRuntime` receives `document`, `mode`, `queryComponent`, and `loadAsset`; it owns parameter state, timer cleanup, manual refresh, proportional scale, and error isolation. `ComponentHost` catches component render errors and shows a safe component-local fallback.

- [ ] **Step 5: Verify and commit**

```bash
pnpm --filter @datapulse/web test -- src/features/runtime
pnpm --filter @datapulse/web typecheck
git add apps/web/package.json pnpm-lock.yaml apps/web/src/features/runtime
git commit -m "feat: add unified screen runtime"
```

---

### Task 8: Implement Text, Image, KPI, Table, and Progress Components

**Files:**
- Create: `apps/web/src/features/runtime/builtins/TextComponent.vue`
- Create: `apps/web/src/features/runtime/builtins/ImageComponent.vue`
- Create: `apps/web/src/features/runtime/builtins/KpiComponent.vue`
- Create: `apps/web/src/features/runtime/builtins/TableComponent.vue`
- Create: `apps/web/src/features/runtime/builtins/ProgressComponent.vue`
- Create: `apps/web/src/features/runtime/builtins/format.ts`
- Create: `apps/web/src/features/runtime/builtins/basic-components.test.ts`
- Modify: `apps/web/src/features/runtime/registry.ts`

**Interfaces:**
- Registers: `builtin.text`, `builtin.image`, `builtin.kpi`, `builtin.table`, `builtin.progress`
- Consumes: `ComponentRenderContext`, query results, and asset loader from Task 7

- [ ] **Step 1: Write failing component behavior tests**

```typescript
test("KPI renders the first measure and the configured empty state", async () => {
  const wrapper = mount(KpiComponent, {
    props: {
      instance: kpiInstance({ label: "销售额", precision: 2 }),
      data: queryResult([["1250.5"]]),
      state: "success",
    },
  });
  expect(wrapper.text()).toContain("销售额");
  expect(wrapper.text()).toContain("1,250.50");
});
```

Cover HTML escaping in text, image object-URL cleanup, table columns/rows, progress clamping, loading, empty, and safe error states.

- [ ] **Step 2: Run tests and verify missing components**

```bash
pnpm --filter @datapulse/web test -- \
  src/features/runtime/builtins/basic-components.test.ts
```

- [ ] **Step 3: Implement and register all five component types**

Use CSS variables only:

```css
color: var(--screen-text-primary);
background: var(--screen-component-surface);
border-color: var(--screen-component-border);
```

Do not introduce editor buttons inside runtime components.

- [ ] **Step 4: Verify and commit**

```bash
pnpm --filter @datapulse/web test -- src/features/runtime
pnpm --filter @datapulse/web typecheck
git add apps/web/src/features/runtime
git commit -m "feat: add core screen components"
```

---

### Task 9: Implement Charts and GeoJSON Map

**Files:**
- Create: `apps/web/src/features/runtime/builtins/chartOptions.ts`
- Create: `apps/web/src/features/runtime/builtins/EChartComponent.vue`
- Create: `apps/web/src/features/runtime/builtins/GeoMapComponent.vue`
- Create: `apps/web/src/features/runtime/builtins/chart-components.test.ts`
- Modify: `apps/web/src/features/runtime/registry.ts`

**Interfaces:**
- Registers: `builtin.line`, `builtin.bar`, `builtin.pie`, `builtin.geo_map`
- Produces: `buildChartOption(instance, result, theme) -> EChartsOption`
- Emits: normalized `{ type: "set_parameter", name, value }` click interaction

- [ ] **Step 1: Write failing option and click tests**

```typescript
test("bar orientation and donut radius are explicit variants", () => {
  expect(buildChartOption(barInstance("horizontal"), result, theme).yAxis)
    .toMatchObject({ type: "category" });
  expect(buildChartOption(pieInstance("donut"), result, theme).series)
    .toMatchObject([{ type: "pie", radius: ["48%", "72%"] }]);
});
```

Cover line/area, vertical/horizontal bar, pie/donut, theme colors, resize, chart disposal, click parameter mapping, GeoJSON registration, region-code join, loading, empty, and failure.

- [ ] **Step 2: Run tests and verify failure**

```bash
pnpm --filter @datapulse/web test -- \
  src/features/runtime/builtins/chart-components.test.ts
```

- [ ] **Step 3: Implement ECharts and map adapters**

Register each GeoJSON map with a per-asset stable name. Never execute formatter strings or JavaScript from the document. Escape text and use only declarative ECharts options.

- [ ] **Step 4: Verify all nine registrations**

```typescript
expect(registry.types()).toEqual([
  "builtin.bar",
  "builtin.geo_map",
  "builtin.image",
  "builtin.kpi",
  "builtin.line",
  "builtin.pie",
  "builtin.progress",
  "builtin.table",
  "builtin.text",
]);
```

Run:

```bash
pnpm --filter @datapulse/web test -- src/features/runtime
pnpm --filter @datapulse/web typecheck
```

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/features/runtime
git commit -m "feat: add chart and map components"
```

---

### Task 10: Complete Canvas Interaction and Inspector UI

**Files:**
- Modify: `apps/web/package.json`
- Modify: `pnpm-lock.yaml`
- Create: `apps/web/src/features/screens/editor/EditorToolbar.vue`
- Create: `apps/web/src/features/screens/editor/ComponentLibrary.vue`
- Create: `apps/web/src/features/screens/editor/LayersPanel.vue`
- Create: `apps/web/src/features/screens/editor/InspectorPanel.vue`
- Create: `apps/web/src/features/screens/editor/ScreenCanvas.vue`
- Create: `apps/web/src/features/screens/editor/canvas.test.ts`
- Create: `apps/web/src/features/screens/editor/inspector.test.ts`
- Modify: `apps/web/src/features/screens/ScreenEditorView.vue`
- Modify: `apps/web/src/styles/base.css`

**Interfaces:**
- Consumes: editor store from Task 6 and runtime registry from Task 7
- Produces: complete drag, resize, multi-select, alignment, layer, lock, hide, copy/paste, zoom, fit, theme, background, data-binding, and interaction UI

- [ ] **Step 1: Write failing canvas and inspector tests**

```typescript
test("drag snaps selected components to the ten-pixel grid", async () => {
  const wrapper = mount(ScreenCanvas, editorHarness());
  wrapper.vm.commitDrag(["text-1"], { dx: 17, dy: 24 });
  expect(store.document.components[0].frame).toMatchObject({ x: 60, y: 60 });
});
```

Cover multi-select bounding boxes, alignment, z-order, locked-item immobility, hidden layers, clipboard ID regeneration, zoom/fit, theme changes, ChartSpec field selection, and click-to-parameter mapping.

- [ ] **Step 2: Run tests and verify missing UI**

```bash
pnpm --filter @datapulse/web test -- src/features/screens/editor
```

- [ ] **Step 3: Install interaction dependencies**

```bash
pnpm add --filter @datapulse/web moveable@^0.53.0 selecto@^1.26.3
```

- [ ] **Step 4: Implement the three-column editor**

Moveable and Selecto emit geometry intents only; translate them into `EditorCommand` objects. The runtime remains unaware of selection. Keyboard shortcuts:

```text
Cmd/Ctrl+Z        undo
Cmd/Ctrl+Shift+Z  redo
Cmd/Ctrl+C        copy
Cmd/Ctrl+V        paste
Delete/Backspace  remove unlocked selection
```

The inspector loads datasets and fields, constructs a validated `ChartSpec`, and dispatches one `update_data_binding` command.

- [ ] **Step 5: Verify and commit**

```bash
pnpm --filter @datapulse/web test -- src/features/screens src/features/runtime
pnpm --filter @datapulse/web typecheck
pnpm --filter @datapulse/web build
git add apps/web/package.json pnpm-lock.yaml apps/web/src/features/screens \
  apps/web/src/styles/base.css
git commit -m "feat: complete screen editor canvas"
```

---

### Task 11: Publish Safely and Preview Drafts

**Files:**
- Create: `apps/server/src/datapulse/screen/publishing.py`
- Modify: `apps/server/src/datapulse/screen/api.py`
- Modify: `apps/server/src/datapulse/lifespan.py`
- Create: `apps/server/tests/screen/test_publishing.py`
- Modify: `apps/server/tests/screen/test_api.py`
- Create: `apps/web/src/features/player/types.ts`
- Create: `apps/web/src/features/player/api.ts`
- Create: `apps/web/src/features/player/PlayerView.vue`
- Create: `apps/web/src/features/player/player.test.ts`
- Modify: `apps/web/src/features/screens/editor/EditorToolbar.vue`
- Modify: `apps/web/src/router/index.ts`

**Interfaces:**
- Produces: `PublishingService.publish(screen_id, expected_revision)`
- Produces: `POST /api/admin/screens/{screen_id}/publish`
- Produces: protected draft preview `/studio/screens/{screen_id}/preview`
- Produces: shared `PlayerView` shell for all playback modes

- [ ] **Step 1: Write failing atomic-publication tests**

```python
async def test_failed_validation_preserves_previous_snapshot(
    publishing_service: PublishingService,
    screen_repository: ScreenRepository,
) -> None:
    before = await publish_valid_screen(publishing_service)
    await corrupt_draft_asset_reference(screen_repository)
    with pytest.raises(PublishValidationError):
        await publishing_service.publish(before.id, expected_revision=1)
    after = await screen_repository.get(before.id)
    assert after.published_document == before.published_document
```

Validate component type IDs, datasets, assets, document schema, and revision before one transaction copies the draft and sets `published_at`.

- [ ] **Step 2: Run backend tests and verify failure**

```bash
uv run --package datapulse-server pytest apps/server/tests/screen/test_publishing.py -v
```

- [ ] **Step 3: Implement publish API and editor confirmation**

The editor must call `saveNow()`, then show:

```text
发布将覆盖当前线上大屏，且无法直接回滚。
如需备份，请先复制大屏。
```

Only the explicit confirmation button calls publish. A failed publish leaves the editor and draft unchanged.

- [ ] **Step 4: Add authenticated full-screen draft preview**

`PlayerView` accepts `mode: "preview" | "standalone" | "embed"` and delegates all rendering to `ScreenRuntime`. Preview loads the draft through the admin API and uses admin component-query and asset endpoints.

- [ ] **Step 5: Verify and commit**

```bash
uv run --package datapulse-server pytest apps/server/tests/screen -v
pnpm --filter @datapulse/web test -- src/features/player src/features/screens
pnpm --filter @datapulse/web typecheck
git add apps/server/src/datapulse/screen apps/server/src/datapulse/lifespan.py \
  apps/server/tests/screen apps/web/src/features apps/web/src/router/index.ts
git commit -m "feat: publish and preview screens"
```

---

### Task 12: Add Revocable Standalone Playback

**Files:**
- Modify: `apps/server/src/datapulse/settings.py`
- Modify: `apps/server/src/datapulse/metadata/models.py`
- Modify: `apps/server/src/datapulse/metadata/__init__.py`
- Create: `apps/server/migrations/versions/0005_display_access.py`
- Create: `apps/server/src/datapulse/display/__init__.py`
- Create: `apps/server/src/datapulse/display/repository.py`
- Create: `apps/server/src/datapulse/display/tokens.py`
- Create: `apps/server/src/datapulse/display/service.py`
- Create: `apps/server/src/datapulse/display/api.py`
- Modify: `apps/server/src/datapulse/lifespan.py`
- Modify: `apps/server/src/datapulse/app.py`
- Modify: `apps/server/src/datapulse/static.py`
- Create: `apps/server/tests/display/test_tokens.py`
- Create: `apps/server/tests/display/test_api.py`
- Modify: `apps/server/tests/test_static.py`
- Modify: `apps/server/tests/metadata/test_migrations.py`
- Modify: `apps/web/src/features/player/api.ts`
- Modify: `apps/web/src/features/player/PlayerView.vue`
- Modify: `apps/web/src/router/index.ts`
- Create: `apps/web/src/features/player/standalone-player.test.ts`

**Interfaces:**
- Produces: `DisplayAccessService.generate_key/exchange/authenticate`
- Produces admin key route and public player document/query/asset routes
- Produces public SPA route `/play/:screenId`

- [ ] **Step 1: Write failing key lifecycle tests**

```python
async def test_rotating_key_invalidates_existing_display_session(
    display_service: DisplayAccessService,
) -> None:
    first = await display_service.generate_key("screen-1")
    session = await display_service.exchange("screen-1", first.plaintext)
    await display_service.generate_key("screen-1")
    assert await display_service.authenticate("screen-1", session) is False
```

Assert only hashes persist, plaintext is returned once, session claims contain screen ID and key version, sliding expiry is 30 days, unpublished screens reject access, and CSP is `frame-ancestors 'none'`.

- [ ] **Step 2: Run tests and verify failure**

```bash
uv run --package datapulse-server pytest apps/server/tests/display -v
```

- [ ] **Step 3: Implement display access and routes**

```text
POST /api/admin/screens/{screen_id}/display-key
POST /api/player/screens/{screen_id}/session
GET  /api/player/screens/{screen_id}
POST /api/player/screens/{screen_id}/query
GET  /api/player/screens/{screen_id}/assets/{asset_id}
```

The session endpoint sets `datapulse_display` as HttpOnly, SameSite=Lax, path-scoped to `/api/player`, and Secure in production. Every runtime request checks the current key version and renews the signed session expiry.

Sign display-session payloads with an explicit HMAC-SHA256 codec implemented from the Python standard library; the codec contains `screen_id`, `key_version`, `issued_at`, and `expires_at` and verifies the signature with `hmac.compare_digest`.

Extend the production SPA router with a dedicated `/play/{screen_id}` HTML response registered before the catch-all. It serves the same `index.html` but sets `Content-Security-Policy: frame-ancestors 'none'`, `Cache-Control: no-store`, and `X-Content-Type-Options: nosniff`. The CSP assertion belongs in `apps/server/tests/test_static.py`; setting CSP only on JSON APIs is insufficient.

- [ ] **Step 4: Implement standalone frontend flow**

`/play/:screenId?key=...` exchanges the key, calls `history.replaceState` immediately, loads only the published document, and never resolves the admin auth store. Missing, revoked, or invalid access renders a neutral full-page error without Studio navigation.

- [ ] **Step 5: Verify and commit**

```bash
uv run --package datapulse-server pytest apps/server/tests/display \
  apps/server/tests/screen apps/server/tests/metadata -v
pnpm --filter @datapulse/web test -- src/features/player
pnpm --filter @datapulse/web typecheck
git add apps/server/src/datapulse apps/server/migrations/versions/0005_display_access.py \
  apps/server/tests apps/web/src/features/player apps/web/src/router/index.ts
git commit -m "feat: add standalone screen playback"
```

---

### Task 13: Issue and Enforce Secure Embed Tickets

**Files:**
- Modify: `apps/server/pyproject.toml`
- Modify: `uv.lock`
- Modify: `apps/server/src/datapulse/settings.py`
- Modify: `apps/server/src/datapulse/metadata/models.py`
- Modify: `apps/server/src/datapulse/metadata/__init__.py`
- Create: `apps/server/migrations/versions/0006_embed_access.py`
- Create: `apps/server/src/datapulse/embedding/__init__.py`
- Create: `apps/server/src/datapulse/embedding/repository.py`
- Create: `apps/server/src/datapulse/embedding/tokens.py`
- Create: `apps/server/src/datapulse/embedding/service.py`
- Create: `apps/server/src/datapulse/embedding/api.py`
- Create: `apps/server/src/datapulse/embedding/page.py`
- Modify: `apps/server/src/datapulse/lifespan.py`
- Modify: `apps/server/src/datapulse/app.py`
- Modify: `apps/server/src/datapulse/static.py`
- Create: `apps/server/tests/embedding/test_tokens.py`
- Create: `apps/server/tests/embedding/test_api.py`
- Modify: `apps/server/tests/metadata/test_migrations.py`

**Interfaces:**
- Produces: `EmbedService.rotate_api_key/issue_ticket/authorize`
- Produces server-to-server ticket endpoint
- Produces embed document/query/asset routes

- [ ] **Step 1: Write failing ticket and Origin tests**

```python
def test_ticket_binds_screen_origin_parameters_and_expiry() -> None:
    ticket = tokens.issue(
        screen_id="screen-1",
        allowed_origin="https://host.example.com",
        parameters={"region": "east"},
        mutable_parameters=("region",),
        lifetime=timedelta(hours=1),
    )
    claims = tokens.verify(ticket)
    assert claims.screen_id == "screen-1"
    assert claims.allowed_origin == "https://host.example.com"
    assert claims.mutable_parameters == ("region",)
```

Test malformed signing keys, wrong audience, wrong screen, expired tokens, HTTP non-local origins, path-bearing origins, more than eight hours, unauthorized parameters, API Key rotation, and redacted logs.

- [ ] **Step 2: Run tests and verify failure**

```bash
uv run --package datapulse-server pytest apps/server/tests/embedding -v
```

- [ ] **Step 3: Add PyJWT and implement secrets**

```bash
uv add --package datapulse-server "PyJWT[crypto]>=2.10,<3"
```

Hash the host API Key with SHA-256, return plaintext only on rotation, and compare with `hmac.compare_digest`. Validate `DATAPULSE_SIGNING_KEY` as URL-safe Base64 for 32 bytes before enabling display or embed signing.

- [ ] **Step 4: Add server and runtime routes**

```text
POST /api/admin/embed/api-key
POST /api/embed/tickets
GET  /api/embed/screens/{screen_id}
POST /api/embed/screens/{screen_id}/query
GET  /api/embed/screens/{screen_id}/assets/{asset_id}
```

`POST /api/embed/tickets` accepts `Authorization: Bearer <api-key>` and is not callable with the admin Session alone. Runtime routes accept only the short ticket. Set `Cache-Control: no-store`, `Referrer-Policy: no-referrer`, `Content-Security-Policy: frame-ancestors <exact-origin>`, and redact the `ticket` query parameter from access logs.

Register `GET /embed/{screen_id}?ticket=...` before the SPA catch-all in production. `embedding.page` verifies the Ticket and matching screen before returning `index.html`, and the HTML response—not merely the JSON APIs—sets the exact `frame-ancestors` CSP. Add a Uvicorn access-log filter that replaces the `ticket` query value with `[REDACTED]` before formatting the record. Invalid, expired, wrong-screen, or wrong-Origin tickets never receive the player HTML.

- [ ] **Step 5: Verify and commit**

```bash
uv run --package datapulse-server pytest apps/server/tests/embedding \
  apps/server/tests/display apps/server/tests/screen \
  apps/server/tests/metadata -v
uv run --package datapulse-server ruff check apps/server
git add apps/server/pyproject.toml uv.lock apps/server/src/datapulse \
  apps/server/migrations/versions/0006_embed_access.py apps/server/tests
git commit -m "feat: secure embedded screen access"
```

---

### Task 14: Add Embed Player Messaging and JavaScript SDK

**Files:**
- Create: `packages/embed-sdk/package.json`
- Create: `packages/embed-sdk/tsconfig.json`
- Create: `packages/embed-sdk/src/index.ts`
- Create: `packages/embed-sdk/src/protocol.ts`
- Create: `packages/embed-sdk/src/index.test.ts`
- Modify: `apps/web/src/features/player/api.ts`
- Modify: `apps/web/src/features/player/PlayerView.vue`
- Create: `apps/web/src/features/player/embedBridge.ts`
- Create: `apps/web/src/features/player/embed-player.test.ts`
- Modify: `apps/web/src/router/index.ts`
- Modify: `pnpm-lock.yaml`

**Interfaces:**
- Produces: `DataPulseEmbed.mount(element, options) -> EmbeddedScreen`
- Produces: `EmbeddedScreen.refresh/setParameters/getParameters/fullscreen/destroy`
- Produces public route `/embed/:screenId`

- [ ] **Step 1: Write failing SDK Origin and request-correlation tests**

```typescript
test("ignores messages from the wrong origin", async () => {
  const embedded = DataPulseEmbed.mount(container, {
    url: "https://data.example.com/embed/screen-1",
    ticket: "short-ticket",
  });
  dispatchMessage("https://evil.example.com", {
    type: "ready",
    instance_id: embedded.instanceId,
  });
  expect(embedded.ready).toBe(false);
});
```

Also test explicit `targetOrigin`, request IDs, parameter responses, error propagation, fullscreen requests, listener cleanup, and two independent embeds on one page.

- [ ] **Step 2: Run tests and verify missing package**

```bash
pnpm --filter @datapulse/embed-sdk test
pnpm --filter @datapulse/web test -- src/features/player/embed-player.test.ts
```

- [ ] **Step 3: Implement the SDK**

```typescript
export interface EmbeddedScreen {
  readonly instanceId: string;
  refresh(): void;
  setParameters(values: Record<string, JsonValue>): Promise<void>;
  getParameters(): Promise<Record<string, JsonValue>>;
  fullscreen(enabled?: boolean): Promise<void>;
  onError(listener: (error: EmbedError) => void): () => void;
  destroy(): void;
}
```

The iframe URL contains the Ticket only for bootstrap. The player stores it only in memory, immediately removes it with `history.replaceState`, and passes it as a Bearer token to embed APIs. Never use Local Storage, Session Storage, or cookies for the Ticket.

- [ ] **Step 4: Implement the iframe bridge**

The player validates `event.origin` against ticket claims and `event.source === window.parent`. It accepts only the generated `EmbedMessageEnvelope` variants. `setParameters` validates mutable names before updating runtime parameters. On ticket expiry it stops new queries and sends `EMBED_TICKET_EXPIRED`.

- [ ] **Step 5: Verify and commit**

```bash
pnpm --filter @datapulse/embed-sdk test
pnpm --filter @datapulse/web test -- src/features/player src/features/runtime
pnpm typecheck
pnpm build
git add packages/embed-sdk apps/web/src/features/player \
  apps/web/src/router/index.ts pnpm-lock.yaml
git commit -m "feat: add DataPulse embed SDK"
```

---

### Task 15: Complete End-to-End, Security, and Visual Regression Coverage

**Files:**
- Create: `apps/web/e2e/screen-editor.spec.ts`
- Create: `apps/web/e2e/screen-playback.spec.ts`
- Create: `apps/web/e2e/embed-host.html`
- Modify: `apps/web/playwright.config.ts`
- Modify: `tools/prepare_e2e.py`
- Modify: `apps/web/e2e/runtime-config.ts`
- Modify: `.env.example`
- Modify: `README.md`

**Interfaces:**
- Verifies the entire approved phase-two user journey
- Documents required signing and asset configuration

- [ ] **Step 1: Extend deterministic E2E data**

Generate a URL-safe 32-byte signing key inside each isolated E2E run and expose it only to the backend process:

```python
signing_key = base64.urlsafe_b64encode(b"e2e-signing-key-material-32-byte").decode()
```

Extend the SQLite fixture with month, region, amount, target, and area-code data used by all nine components.

- [ ] **Step 2: Write the editor-to-standalone E2E test**

The test must:

```text
initialize and log in
create a screen
add all nine component types
bind a dataset
drag and resize components
undo and redo
reload and prove autosave
preview the draft
publish after confirmation
generate a display key
open standalone playback
observe timer refresh and parameter interaction
```

Use role- and label-based locators. Never assert implementation class names when an accessible name is available.

- [ ] **Step 3: Write the host-to-embed E2E test**

The test host obtains a Ticket through its backend fixture, mounts the SDK, waits for `ready`, changes `region`, refreshes, requests fullscreen, and receives an error for a forbidden parameter. A second test proves wrong Origin, expired Ticket, and a rotated API Key are rejected.

- [ ] **Step 4: Add screenshot assertions**

Capture stable screenshots for:

- editor shell at `1920 × 1080`;
- dark player at 16:9;
- light theme;
- one component error while other components render;
- letterboxed playback in a non-16:9 viewport.

Mask timestamps and request IDs. Store Playwright baselines under `apps/web/e2e/snapshots`.

- [ ] **Step 5: Document configuration and run full verification**

Document:

```text
DATAPULSE_SIGNING_KEY=<urlsafe-base64-32-bytes>
DATAPULSE_DATA_DIR=/data
```

Run:

```bash
pnpm check:contracts
pnpm test
pnpm typecheck
pnpm build
pnpm test:integration
pnpm test:e2e
git diff --check
```

Expected: all contract, backend, frontend, type, build, connector integration, editor, standalone, embed, security, and screenshot tests pass.

- [ ] **Step 6: Commit**

```bash
git add apps/web/e2e apps/web/playwright.config.ts tools/prepare_e2e.py \
  apps/web/e2e/runtime-config.ts .env.example README.md
git commit -m "test: verify phase two screen delivery"
```

---

## Execution Checkpoints

Review and run the cumulative fast suite after Tasks 4, 10, and 14:

```bash
pnpm check:contracts
pnpm test
pnpm typecheck
pnpm build
```

Run connector integration tests after Task 4 and again in Task 15:

```bash
pnpm test:integration
```

Run the full Playwright suite after Tasks 11, 12, 14, and 15:

```bash
pnpm test:e2e
```

Do not merge the execution branch until Task 15 passes the complete verification command and a final code review has no unresolved high-priority findings.
