# Phase Four Identity Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans. Track each step below; scope excludes conversational digital humans.

**Goal:** Migrate the existing administrator into a multi-user system with server-enforced resource sharing and immediate revocation.

**Architecture:** Extend the existing account/session tables; resource grants and ownership use separate tables. One policy service serves API routes and list filtering; embedded viewers retain the existing authorization path.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, Vue 3, Vitest, pytest.

## Task 1: Accounts and sessions

Files: modify `apps/server/src/datapulse/metadata/models.py`, `auth/api.py`, `auth/session.py`, `auth/repository.py`; create `apps/server/src/datapulse/identity/` and migration `apps/server/migrations/versions/0020_identity.py`; test `apps/server/tests/identity/` and existing auth/migration suites.

- [x] Add failing HTTP tests: admin creates editor, editor logs in, editor cannot create users, account disabling/role change/password reset invalidates the session; last admin cannot be disabled or demoted.
- [x] Run `uv run --package datapulse-server pytest apps/server/tests/identity -q` and confirm missing endpoints/behavior fail.
- [x] Implement strict account contracts, transactional lifecycle and audit. Account responses contain only id, username, role, active and timestamps; password is input-only.
- [x] Extend session response with id and role; preserve username and auth cookie/CSRF semantics.
- [x] Run auth, identity and migration tests; migrate a pre-0020 database with an existing admin.

## Task 2: Resource policy

Files: identity policy/repository plus datasource/dataset/filedata/screen/runtime/asset/AI/display/embedding/speech API modules; tests under identity.

- [x] Add two-client tests for hidden lists, neutral missing resource responses, denied writes, read/write/publish grants, revoke-after-query, dataset/asset reference injection and inaccessible AI context.
- [x] Implement ownership registration, grant CRUD, per-request policy and filtered lists; deny unknown admin routes to non-admin by default.
- [x] Validate dependencies before creation/save/preview/query and publish. Preserve Ticket and display-key authorization independent of Studio roles.
- [x] Run `uv run --package datapulse-server pytest apps/server/tests/identity apps/server/tests/auth apps/server/tests/screen apps/server/tests/embedding apps/server/tests/display -q`.

## Task 3: User and sharing interfaces

Files: `apps/web/src/stores/auth.ts`, new `apps/web/src/features/identity/`, router and Studio navigation, settings integration.

- [x] Write component tests for list/create/edit/disable/reset, error/empty states, secret clearing and grant/revoke; verify non-admin management access is rejected.
- [x] Implement typed requests and accessible forms using existing UI styles. Hide unauthorized navigation without relying on that for security.
- [x] Add a two-user browser test proving share/edit/conflict/revoke semantics with fixture-only accounts.
- [x] Run `pnpm test:web`, `pnpm typecheck` and the targeted browser test; integrate exported contracts using existing generators.

## Task 4: Review

- [x] Review requirements against implementation, then code correctness and privilege escalation paths; fix findings.
- [x] Record actual commands, counts and evidence in `docs/PHASE_FOUR_PROGRESS.md`; do not close target environment gates from local results.
