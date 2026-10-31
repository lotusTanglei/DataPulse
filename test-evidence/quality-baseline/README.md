# Quality Baseline

The committed `baseline-2026-09-22.json` is the deterministic fixture rehearsal for the
`gpt-6-astra` target model. It is intentionally reproducible and contains concrete metric
values for the eight golden cases.

Run the same fixture baseline again:

```bash
pnpm quality:baseline -- --provider fixture --model gpt-6-astra --date 2026-09-22
```

Run and archive a real OpenAI-compatible model baseline when credentials are available:

```bash
DATAPULSE_AI_BASE_URL=https://api.openai.com/v1 \
DATAPULSE_AI_API_KEY=... \
DATAPULSE_AI_MODEL=gpt-6-astra \
pnpm quality:baseline -- --provider openai --date 2026-09-22 \
  --output test-evidence/quality-baseline/baseline-2026-09-22-real.json
```

Real-provider output records the model, date, per-case result, latency, usage and calculated
token cost. API keys are read from the environment and are never written to the report.

Compare two or more archived reports, update the trend dashboard, and extract failures into
the versioned regression library:

```bash
pnpm quality:harness -- \
  --report test-evidence/quality-baseline/baseline-current-real.json \
  --report test-evidence/quality-baseline/baseline-candidate-real.json \
  --comparison-output test-evidence/quality-baseline/comparison.json \
  --trend-output test-evidence/quality-baseline/trend.json \
  --dashboard-output test-evidence/quality-baseline/dashboard.html \
  --failures-output fixtures/golden/failures/manifest.json
```

Gate a default-model change. Exit code `0` allows the change; exit code `1` blocks it when
any success, draft, binding, semantic, chart, failure, warning, latency, or cost metric is
worse than the current model:

```bash
pnpm quality:gate -- \
  --baseline test-evidence/quality-baseline/baseline-current-real.json \
  --candidate test-evidence/quality-baseline/baseline-candidate-real.json \
  --output test-evidence/quality-baseline/upgrade-decision.json
```

Fixture reports exercise the tooling but do not count as evidence for a real model upgrade.
