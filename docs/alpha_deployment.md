# Closed Alpha deployment runbook

## Release contract

- Python: 3.12
- Streamlit: 1.63.0 (pinned in `requirements.txt`)
- Data store: PostgreSQL compatible with the existing `public.v2_*` schema
- AI provider: Gemini through `google-genai`
- Entry point: `streamlit run app.py`

This release does not include a schema migration. Apply no migration or existing-user data rewrite as part of routine deployment.

## Required secrets

Create `.streamlit/secrets.toml` locally from `.streamlit/secrets.toml.example`, or configure the same keys in the deployment platform's secret manager.

- `DATABASE_URL`: PostgreSQL connection URL, including TLS options required by the provider.
- `GEMINI_API_KEYS`: one or more Gemini API keys in the format already expected by the application.

Optional controls:

- `DEV_AI_MOCK`: must be omitted or `false` in production. It is only for zero-cost QA.
- `DEV_AI_MOCK_DELAY`: mock-only artificial delay.
- `DIALOGUE_SCENE_RUNTIME_V1`: defaults to `true`; set `false` only for explicit legacy presentation QA.

Never commit `.streamlit/secrets.toml`, `.env`, database URLs, or Gemini keys.

## Local reproducibility

PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip check
$env:DEV_AI_MOCK = "1"
$env:DEV_AI_MOCK_DELAY = "0"
streamlit run app.py
```

POSIX shell:

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
DEV_AI_MOCK=1 DEV_AI_MOCK_DELAY=0 streamlit run app.py
```

Live mode must be a deliberate, separately approved smoke test:

```powershell
Remove-Item Env:DEV_AI_MOCK -ErrorAction SilentlyContinue
streamlit run app.py
```

## Pre-deploy gate

1. Confirm `git status --short` contains only reviewed release files.
2. Run the V3 regression QA suite and related `py_compile` checks.
3. Run `python -m pip check` and `git diff --check`.
4. Run a mock E2E smoke test covering login, Story, manual progression, quiz, completion, and Story Choice.
5. Confirm narrow viewports (390, 430, and 768 px) and desktop have no horizontal overflow or browser console errors.
6. Confirm `.streamlit/secrets.toml`, `.env`, archives, database dumps, and generated migration helpers are excluded from the release commit.
7. Perform the separately approved minimal Gemini live smoke test only after all zero-cost gates pass.

## Post-deploy smoke

- App starts without an import, secrets, or database connection error.
- Authentication succeeds with a dedicated alpha test account.
- Existing World resumes without data loss.
- Chapter Story opens at Scene 1 with autoplay off and manual Next working.
- Quiz answer, chapter completion, Story Choice, and next Story Block generation work.
- `v2_user_events` receives the expected product events.
- `v2_ai_generation_logs` records provider, model, success/failure, latency, retry data, and generation context.
- No raw exception details or credentials appear in the UI or browser console.

## Rollback and incident handling

Keep the previously deployed application revision available. If the new revision fails startup, authentication, persistence, or core learning progression, route traffic back to that revision and preserve the database unchanged. Do not run `git reset`, delete user rows, or reverse data manually as an incident shortcut.

For AI failures, inspect `v2_ai_generation_logs` and application logs. For event-delivery failures, preserve the learning flow: analytics insertion is best-effort and must not block the user. Rotate any credential immediately if exposure is suspected, then redeploy with the rotated secret.

## Known closed-alpha debt

- `use_container_width` remains in active UI code and should be migrated in a dedicated compatibility change, not this release gate.
- The current product event set covers the core funnel but not every navigation, retry, or abandonment point.
- Gemini behavior, quota, and latency require one small approved live smoke test; mock QA cannot establish provider-side behavior.
- Deployment-platform-specific health checks and rollback automation are not yet codified in the repository.
