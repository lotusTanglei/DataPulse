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
