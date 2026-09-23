# Phase Four Operations Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans. External target gates remain separate from local implementation.

**Goal:** Deliver verifiable backup/restore and operational tooling without claiming unperformed production validation.

**Architecture:** Offline maintenance CLI snapshots SQLite and explicit managed directories, verifies archive checksums, and stages restores into empty directories. Existing worker/monitoring paths are extended only after testing actual gaps.

**Tech Stack:** Python standard archive/sqlite tools, SQLAlchemy, existing migrations, pytest, Docker/Prometheus, Playwright.

## Task 1: Backup and restore

Files: create `apps/server/src/datapulse/operations/backup.py`, `operations/cli.py`, `apps/server/tests/operations/test_backup.py`, and `docs/operations/backup-restore.md`; CLI registration integrated in server pyproject.

- [x] Write failing tests using an actual migrated fixture database, uploaded media/files and separate secret keys: create/verify/restore into a new root, remap storage references and reject wrong/missing decryption dependencies.
- [x] Add corrupt checksum, path traversal, duplicates, symlink, archive bomb, non-empty destination, partial failure and unsupported database tests.
- [x] Implement explicit maintenance-mode requirement, consistent snapshot, member manifest, secure modes and exclusion of secrets/transient files.
- [x] Implement inspect/verify before extraction, staged restore, version/reference validation and atomic finalization; restored sessions/setup credentials are invalidated.
- [x] Run `uv run --package datapulse-server pytest apps/server/tests/operations -q` and a CLI roundtrip with a separately created fixture.
- [x] Document offline topology and PostgreSQL native backup/restore, independent key custody, upgrade and rollback procedures.

## Task 2: Security and worker audit

- [x] Trace existing worker claim/recovery/quota and media/file pipeline with CodeGraph; record concrete gaps before changes.
- [x] Add behavioral regressions for observed restart/concurrency flaws; implement real configurable scanner invocation and timeout/failed-scan rejection where absent.
- [x] Integrate scanner before persistence/processing and document real deployment isolation. Fake scanner success is not P4-DH-004 evidence.
- [x] Verify structured log redaction and request IDs, available metric alerts and production configuration validation.

## Task 3: Integration and evidence

- [x] Execute `pnpm verify`, `pnpm test:integration`, `pnpm test:e2e`, `pnpm test:e2e:cross-browser` on the integrated code.
- [x] Build/start Docker with isolated data, restore fixture backup and verify core routes and resource retrieval after restart.
- [ ] Execute physical display and 28,800-second soak only when genuine target conditions are present; preserve all 8 gate identifiers and report unmet prerequisites.
- [x] Review coverage and security, then write `docs/PHASE_FOUR_CLOSEOUT.md` with exact passes/failures/skips/blockers and update progress, README, DP-005 and ISS-022 accurately.

目标环境未准备，物理显示与 28,800 秒 soak 未执行；此项保持未勾选，不能由本地结果关闭。最终结果见 `docs/PHASE_FOUR_CLOSEOUT.md`。
