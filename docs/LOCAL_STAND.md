# Local Windows stand

Start from the repository root after installing dependencies:

```powershell
& '.venv/local-runtime/python/Scripts/python.exe' scripts/local_stand.py
```

The launcher uses an isolated PostgreSQL cluster in `.venv/local-runtime/pgdata`,
bound to `127.0.0.1:5433`. It creates tables only in this local database and seeds
a local demo account. Login details are in ignored `.venv/local-runtime/stand.json`.
BHAPI and Apify review credentials are read from local, git-ignored `backend/.env.review`. Create this file locally; credentials are not distributed with the repository.
Ignored `backend/.env` can override them and supplies existing GigaChat credentials
and other local settings. No credentials are embedded in the launcher.

- Interface: http://localhost:5173
- Backend health: http://127.0.0.1:8000/health
- ML health: http://127.0.0.1:8001/health (ready when `status` is `ok`)

The current integration uses BHAPI WB search sorted by rating (`rate`), one outfit,
and Apify reviews only for selected products. Real requests consume provider quotas.
Size recommendations still use the existing approximation; seller measurement tables
and ML fit signals do not yet adjust the selected size.

Watch requests and results:

```powershell
Get-Content -LiteralPath 'logs/local/backend.log' -Encoding UTF8 -Tail 80 -Wait
```

`generation_search_plan` records generation ID, category and the cleaned GigaChat
search phrase. `bhapi_search` records the outgoing search payload, including price
bounds and sorting. `bhapi_search_result` records usable card count. `provider_request`
records HTTP status and the request counter without authorization headers.

BHAPI requests use `X-BHAPI-Error-Format: problem-v1`. Errors log allowlisted
`code`, `request_id`, `retry.action` and delay, without free-form upstream bodies.
Temporary 502/503/504 errors with explicit `retry.action=wait` get at most three
attempts, with 2/4 second fallback delays or the provider's delay. A delay above
30 seconds is not shortened: the call fails instead. Quota, authentication,
ambiguous outcomes and network failures are never retried automatically.
Each actual attempt consumes the generation's call budget and may be billed.
After exhausted retries, an unavailable card is skipped. Three consecutive
temporary card failures stop that category's collection; existing valid candidates
are retained. If all cards failed, the error propagates rather than becoming an
apparently successful empty search. Search-level failure remains fatal.

Other logs: `logs/local/ml.log`, `frontend.log`, `postgres.log`.
The first ML startup downloads FashionCLIP and the translation model. Windows short
paths are used for PostgreSQL and SentencePiece compatibility with Cyrillic paths.
Runtime data, logs, local `.env` and `backend/.env.review` remain git-ignored.
Services run in the background.
