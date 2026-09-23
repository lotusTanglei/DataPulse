# Backup and restore

This CLI supports offline, single-instance SQLite deployments on Linux/macOS. Stop the API, all speech workers, and external writers of managed SQLite sources/files before running it. `--maintenance` explicitly acknowledges this requirement. API/worker runtime leases also prevent backup while a cooperating process is active. The lease is advisory: it cannot stop an old release or a third-party process that ignores it. All processes sharing a database must use the same canonical data directory and maintenance window.

The archive contains a SQLite backup-API snapshot, referenced uploaded files/media and thumbnails, referenced SQLite data sources, installed ecosystem package records plus their declared content, and immutable package uninstall history. SQLite source snapshots include committed WAL content. Unreferenced uploads, package staging, lock files, `.env`, deployment key files, logs and browser cookies are outside the backup scope. External PostgreSQL/MySQL/HTTP datasource contents are not copied; their configuration and encrypted credentials are retained. Back those systems up separately.

Completed speech tasks retain their history when cached audio is deleted. Backup creation clears missing asset IDs only for terminal task cache entries in its private database snapshot; it leaves source history and task outcomes unchanged. Missing media used by a draft or published screen still fails verification. Installed templates are checked against the document contract and must retain every exact plugin version they declare.

Every member has a SHA-256 and byte size. The manifest records the archive schema, application version, Alembic revision, creation time, member count, total uncompressed bytes and an HMAC fingerprint of the encryption dependency. Archives are created with mode `0600` in a private staging directory and published without replacing an existing file. The archive is **not encrypted or cryptographically signed**: it contains application data, account password hashes and credential ciphertext. Keep it in restricted, encrypted backup storage; checksums detect accidental corruption and do not authenticate an archive from an untrusted sender.

## Create and verify

Run from the repository with the original deployment settings in a restricted environment. Never pass keys as command-line literals or place them in the archive. Provision `DATAPULSE_MASTER_KEY` independently from the secret manager; ciphertext backups require that key and verify decryption before creation. Signing keys remain outside the archive too.

```sh
uv run --package datapulse-server datapulse-operations backup create \
  --archive /srv/backups/datapulse-2026-09-21.zip --maintenance
uv run --package datapulse-server datapulse-operations backup verify \
  --archive /srv/backups/datapulse-2026-09-21.zip
uv run --package datapulse-server datapulse-operations backup inspect \
  --archive /srv/backups/datapulse-2026-09-21.zip
```

The equivalent module entrypoint is `python -m datapulse.operations.cli`. Commands return JSON on success, exit `1` with a stable `BACKUP_FAILED` diagnostic on operational failure, and exit `2` on CLI usage errors. `inspect` performs full verification before returning the manifest. Verification does not require the master key; restoration does when ciphertext exists.

Configured metadata DB, assets or sources outside `DATAPULSE_DATA_DIR` cause a safe failure unless `--include-external-paths` is supplied to `create`. This option includes only referenced data inside those explicitly configured roots. It never grants permission to copy arbitrary paths or follow symlinks. A reference outside its configured root, a missing file, changed file hash, malformed package or missing document dependency fails the whole backup. Stop external writers of those configured roots as well.

Limits are 20,000 ZIP entries including the manifest, 1 GiB per member, 10 GiB aggregate expanded data and archive size, a 200:1 compression ratio, and a 4 MiB manifest. Creation uses stored ZIP members; verification also safely supports bounded compressed members. Traversal, absolute/Windows paths, backslashes, control characters, duplicates, links, unexpected entries, mismatched checksums, incompatible versions, malformed DB schema, SQLite integrity/foreign-key failures and unresolved data/media/plugin references are rejected. Verification validates names/limits and streams all checksums before writing any archive member to a private temporary directory.

## Restore and rehearse

Restore using the **same application release and Alembic head** that created the archive. First restore, verify and boot that release; upgrade the recovered instance afterwards using the normal release migration process. Restore never silently migrates an old archive to the current schema.

```sh
uv run --package datapulse-server datapulse-operations backup restore \
  --archive /srv/backups/datapulse-2026-09-21.zip \
  --target /srv/datapulse-rehearsal --maintenance
```

The target must be nonexistent or empty; its parent must exist and must not contain symlinks. Verification, decryption checks, reference remapping and credential invalidation occur in staging. A same-filesystem directory rename makes the completed instance visible atomically. Failure before finalization removes staging and preserves the target. Allow disk space for the archive plus two expanded copies during restoration, and use a private temporary-filesystem location via `TMPDIR` when required by your environment.

The restored database is always `<target>/datapulse.db`; uploaded files, media, SQLite sources and ecosystem state are under `<target>/files`, `assets`, `sources` and `ecosystem`. File/media/thumbnail absolute paths are rewritten. SQLite source configs point to the restored source snapshots using paths relative to `sources`. Before booting, set `DATAPULSE_DATA_DIR` to the target; unset old `DATAPULSE_DATABASE_URL`, `DATAPULSE_ASSETS_DIR` and `DATAPULSE_SOURCES_DIR`, or explicitly point them to these restored locations. Do not retain paths to the source instance.

All administrator sessions, setup codes, display access keys and embed access keys are invalidated. Account records, roles, grants, ownership, documents and encrypted provider/datasource credentials survive. Supply the original master key separately, retain a protected signing key or provision a new one, then sign in again and issue fresh display/embed credentials. Existing deployment bootstrap overrides must be removed before starting a restored uninitialized instance; otherwise operator-supplied bootstrap configuration can intentionally recreate that override.

For a rehearsal, boot the restored data in an isolated API/worker deployment, sign in, query a file dataset and restored SQLite datasource, read a published screen and media/thumbnail, load its exact plugin dependency, and test provider credential decryption using a non-billable test flow. Restart and repeat the query and resource requests. Keep the original instance stopped or keep the rehearsal isolated from providers, scheduled speech and production endpoints. Promote the rehearsed directory by deployment configuration only after these checks. Rollback means stopping the new instance and pointing the matching old release back at the preserved old directory; never restore over a running or populated target.

Automated local evidence is in `apps/server/tests/operations/test_backup.py`: real Alembic migrations, media/file/publication fixtures, restored CSV/source querying, credential decryption, ecosystem package/history recovery, CLI roundtrips, archive attacks, resource limits and failure preservation. This is local functional coverage; production storage durability, offsite retrieval, operator key custody, network providers and target-device playback require a deployment rehearsal.

The independent HTTP-and-CLI rehearsal on 2026-09-21 also passed (`1 passed in 11.77s`): 2 accounts, 2 datasets, 1 published screen, media and an exact plugin dependency survived empty-directory restoration and two application starts. CLI restore took 1.138 seconds for 8 members / 287,201 archive bytes; this small local fixture is not a production recovery-time estimate. It verified login, preserved editor grants, editing/publication, real SQL/CSV results, Display/Embed queries and media/plugin bytes, old credential revocation and separately provisioned keys. See [the detailed local record](restore-rehearsal-local.md) and [redacted measurements](../../test-evidence/phase-four/local-20260921/restore-rehearsal.json). Target deployment gates remain blocked.

## PostgreSQL metadata deployments

The automatic CLI deliberately refuses PostgreSQL metadata databases. The following is a native maintenance procedure, not a claim of a tested PostgreSQL restore drill:

1. Record the application image/release and `alembic_version`. Stop the API, every worker and every managed-file writer for the entire database-and-files capture. Prevent new connections/writers through your deployment controls.
2. Using PostgreSQL client tools compatible with the server, run `pg_dump --format=custom --no-owner --file=/restricted/metadata.dump "$DATAPULSE_PG_DSN"`. The DSN should contain no password; use a restricted `PGPASSFILE` or equivalent managed credentials. Capture the complete application schema/data, including `alembic_version`; preserve required roles/privileges separately through approved DBA procedures. Verify command exit status and inspect `pg_restore --list /restricted/metadata.dump`.
3. In the same stopped maintenance window, copy the explicitly configured uploaded files, assets, SQLite sources and `ecosystem/packages` plus `ecosystem/history` into restricted storage. Preserve a path map and checksums. Do not copy `.env`, signing/master keys, caches, locks or arbitrary contents of the deployment root. Independently back up external datasource systems. Keep encryption/signing keys in separate custody.
4. Provision an empty PostgreSQL database with the same extension/version prerequisites. Run `pg_restore --exit-on-error --single-transaction --no-owner --dbname="$DATAPULSE_RESTORE_PG_DSN" /restricted/metadata.dump`. Restore managed files to the documented target locations. A DBA must rewrite `file_asset.storage_path`, `screen_asset.storage_path` and `screen_asset.thumbnail_path` to those locations and reconcile SQLite `data_source.config_json` paths when moved; this CLI does not perform that transformation for PostgreSQL.
5. Before boot, in a transaction delete `admin_session`, `display_access` and `embed_access` rows and set `system_state.setup_code_hash`/`setup_code_expires_at` to NULL. Retain accounts/roles/grants. Configure the separately held master key and signing key, remove bootstrap overrides, verify the matching Alembic revision, all file/hash references and credential decryption, then run the isolated rehearsal described above. Upgrade only after the matching release boots successfully.
6. Keep old DB/files untouched for rollback. Record actual restore time, dump/file checksums, row counts, verification queries and observed failures. A successful `pg_dump` alone does not demonstrate that the combined database/files deployment can be recovered.
