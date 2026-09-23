# Phase Four Ecosystem Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps below track the complete offline ecosystem delivery.

**Goal:** Install and use versioned templates and trusted component plugins through an actual private catalog.

**Architecture:** Strict ZIP validation and atomic filesystem installation; catalog metadata persisted with immutable versions. Runtime serves only authorized document dependencies and loads ES modules through a common component host.

**Tech Stack:** Pydantic/JSON Schema, Python ZIP and hashes, FastAPI, TypeScript SDK, Vue runtime, pytest/Vitest/Playwright.

## Task 1: Package service

Files: create `apps/server/src/datapulse/ecosystem/`, `apps/server/tests/ecosystem/`; extend `apps/server/src/datapulse/contracts/plugin.py` compatibly. Catalog state uses immutable validated filesystem packages and history; no ecosystem database migration was needed. Migration 0021 is reserved for speech leases.

- [x] Write failing tests for a valid package, wrong SHA/version/API, corrupt ZIP, path traversal, duplicate names, symlinks, compressed size limits, immutable same-version installation and failed-install cleanup.
- [x] Implement strict catalog contracts and transactional install/list/detail/remove methods; reserve built-in IDs.
- [x] Test referenced version deletion refusal using both draft and published documents.
- [x] Expose admin catalog endpoints with CSRF for mutations and stable errors. Public module assets require the existing player/Embed authorization and exact dependency checks.
- [x] Run `uv run --package datapulse-server pytest apps/server/tests/ecosystem apps/server/tests/contracts -q`.

## Task 2: Template application

- [x] Test component IDs and digital-human/component interaction references remap on every creation, explicit dataset/asset mappings and secret-bearing manifests rejected.
- [x] Implement installation separate from application; create new screens through existing contracts and resource policy, never auto-publish.
- [x] Verify explicit new-version adoption leaves published dependencies unchanged and failed application leaves no partial screen.

## Task 3: SDK, loader and editor

Files: new `packages/plugin-sdk`, `examples/metric-plugin`, web `features/ecosystem` and runtime plugin host; integrate registry, component library, inspector, player and embedding endpoints.

- [x] Test module contract validation, update/destroy lifecycle, missing plugin, renderer error and props/data validation.
- [x] Implement SDK definition/types and sample build/package commands; module receives host element, instance configuration and QueryResult through an explicit API.
- [x] Implement exact-version loading and common runtime host, then editor library/default props/schema controls.
- [x] Implement catalog list/detail/upload/install/use/uninstall states and confirmations.
- [x] Build sample, install fixture package, add component, configure, publish and run standalone/Embed through three browsers.

## Task 4: Review and docs

- [x] Review spec coverage then code quality, concentrating on code trust, dependency access, atomic installation and immutable publication.
- [x] Write developer and operator guides, regenerate shared contracts and run `pnpm verify` after integration.

## Task 5: Explicit draft version migration

Files: create `apps/web/src/features/ecosystem/migration.ts` and `migration.test.ts`; update `PluginLibrary.vue`, `plugins.ts`, editor `commands.ts`, and SDK/operator documentation.

- [x] Add failing tests for a two-component migration, later-component failure leaving the original unchanged, missing target renderer/schema incompatibility, downgrade, undo/redo, and a draft edit while the target module loads.
- [x] Implement `preparePluginMigration(document, currentPackage, targetPackage, importer)`: import and validate the target API/module, clone each used component's props, call its optional `migrate(props, fromVersion)`, validate target schemas, and return one `migrate_plugin` command only after every component succeeds.
- [x] Apply dependency and complete replacement props in one editor history operation. Reject a command if the document changed since preparation; retain layout, bindings and resource references unless props explicitly migrate them.
- [x] Add explicit per-version actions to PluginLibrary with pending/error/success states and cancellation on unmount. Use normal draft autosave and never publish; allow choosing an older installed version through the same validation path.
- [x] Run scoped Vitest and Vue/SDK typechecks, then document upgrade, undo/downgrade, immutable packages and publication behavior. Remove the SDK's empty test task because lifecycle behavior is tested in the web host.
