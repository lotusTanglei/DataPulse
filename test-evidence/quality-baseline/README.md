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
pnpm quality:baseline -- --provider openai --date 2026-11-11 \
  --budget-usd 1.00 --max-output-tokens 512 \
  --output test-evidence/quality-baseline/baseline-2026-11-11-real.json
```

Real-provider output records the model, date, per-case result, latency, usage and calculated
token cost. API keys are read from the environment and are never written to the report.

The real runner accepts a positive budget up to USD 1.00, requires known model pricing,
sets `max_tokens`, and makes at most eight requests without retries. Before each request it
reserves the price of the serialized UTF-8 request bytes plus 1,024 framing tokens and the
configured maximum output. Insufficient remaining budget prevents the request. Valid usage
replaces that reservation with reported cost; timeout, HTTP failure or missing/malformed
usage retains the reservation and stops later requests. Usage above the reserved input or
output bounds is recorded at its actual reported cost and stops later requests.

This protection is conditional on a byte-based tokenizer, provider framing within the
allowance, the provider honoring `max_tokens`, and configured prices covering billable
usage. It cannot guarantee a monetary hard cap for arbitrary compatible providers, hidden
fees or unreported tokens. The price registry is project configuration, not a current
supplier quote. Confirm the provider's model version, prices and token-limit behavior before
an authorized real run. A supplier account monetary limit is an optional additional control.

Real reports include `budget` and per-case `cost_audit`. `metrics.token_cost.usd` uses
reported cost plus retained reservations; `reported_cost_usd` is `null` when usage is
incomplete. Do not describe this value as a supplier bill. A budget or usage halt archives
the report and exits `1`; configuration rejection exits `2`. Fixture report fields and
deterministic results are unchanged.

The runner measures a structured binding summary from fields and five sample rows. It does
not execute the complete product Plan, compile, draft persistence, query or rendering flow,
so even a real report cannot independently close M1/M2. Full acceptance boundaries and the
2026-11-11 user deferral of real evaluation are recorded in
[`../maintenance-20261111/README.md`](../maintenance-20261111/README.md).

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
