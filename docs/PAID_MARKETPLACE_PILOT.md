# Paid marketplace pilot: WB first

Implemented catalog source: BHAPI WB. Reviews: Apify (Zen Studio), tested live on WB and Ozon.
A legacy MPDown adapter exists but is disabled locally. WBCON remains an alternative candidate.
Ozon catalog adapter is deliberately not enabled yet: validate its variant/size contract first.
Legacy Yandex source remains the default. No paid requests run on application startup.

## Configure

Register at https://bhapi.ru/ for WB access. Do not subscribe to MPDown for this pilot:
its homepage currently reports unavailable WB collection, and production access has not been verified.
For reviews, use Apify after the bounded probe described below. WBCON can be contacted
via https://api.wbcon.ru/ as an alternative after a trial.
The WB demo specification https://fb.wbcon.su/openapi.json lists a dedicated-server plan
at 5,000 RUB/month, excluded from the generic per-request plan; confirm current terms directly.
Do not enable REVIEWS_PROVIDER=mpdown just because the adapter exists.
A subscription is not a guarantee of source availability. Confirm quotas, rate limits,
latency and text/size fields before committing to a longer subscription.

Put keys in local backend/.env, never in frontend or version control:
```dotenv
CATALOG_PROVIDER=bhapi_wb
REVIEWS_PROVIDER=apify
BHAPI_WB_TOKEN=your-key
APIFY_API_TOKEN=your-key
APIFY_RUN_CAP_USD=0.15
APIFY_GENERATION_CAP_USD=1.0
APIFY_REVIEWS_TIMEOUT_SECONDS=90
APIFY_ALLOW_GROUP_REVIEWS=false
# MPDOWN_API_KEY is retained only for the legacy adapter; not required for this pilot.
OUTFIT_COUNT=1
MARKETPLACE_SEARCH_LIMIT=20
MARKETPLACE_MAX_CALLS=150
MARKETPLACE_REVIEW_LIMIT=20
MARKETPLACE_REVIEW_MAX_PAGES=2
# WB_PICKUP_POINT_ID=validated-numeric-id
```
Use REVIEWS_PROVIDER=none for a catalog-only test without a reviews subscription.
The Apify adapter uses one bounded asynchronous run per selected product, polls for completion,
fetches the dataset and normalizes buyer text/pros/cons. Seller answers and author profiles are excluded.
Each run has an upstream maxTotalChargeUsd cap; the generation reserves the full cap per start.
No paid start is retried automatically. A timed-out run is aborted best-effort; its configured
upstream timeout remains a second limit if the backend terminates before cleanup.
Credits, partial datasets and source restrictions must be checked separately from SUCCEEDED status.
A mismatched WB catalog/Yandex reviews configuration fails explicitly.

## Live checks on 2026-11-12

- BHAPI: one WB search + three cards succeeded in 15.16 seconds (four calls).
  All three returned image URLs responded with HTTP 200 and image/webp.
- GigaChat: authorization and model listing succeeded; GigaChat-2 returned a structured
  two-item search plan. Credentials are local only. Bare budget amounts in generated queries
  are removed by the backend; regression checks cover the observed issue.
- WBCON WB free demo: allowed article 117220345, task 226, completed successfully.
  Result contained 71 reviews, 41 nonempty fb_text values and 71 populated size fields.
  No author identifiers were persisted. This checks the demo, not arbitrary production articles.
  Demo allows two requests per minute and only three documented articles. The first result
  fetch received HTTP 429; after waiting, the fetch succeeded. Production polling must be bounded.
- WBCON Ozon OpenAPI documents an asynchronous task API returning review strings;
  purchased-size metadata is not established. No Ozon collection was tested.

### Apify live results (same date)

- WB actor zen-studio/wildberries-detail-scraper, reviewMode=true: three known clothing
  SKUs, maxReviewsPerProduct=20. Returned 60 review rows in 14.315 seconds, cost $0.138.
  33 distinct nonempty text/pros/cons reviews remained (10, 11, 12 per requested SKU),
  all with a purchased size. All 60 source rows had a size. Remaining rows had no usable text.
- Ozon actor zen-studio/ozon-product-reviews-scraper: the Free plan processed only the
  first URL of an initial three-URL run, returning five review rows plus a rating overview
  in 9.827 seconds, cost $0.02151. Two separate follow-up runs covered the other URLs:
  16.991 / 8.779 seconds, $0.02151 each, five reviews per run.
- Total across four runs: $0.20253 (catalog/GigaChat/ML excluded). Source fees can change.
- Ozon requested SKUs: 815637393, 4339634448, 2154086641. Exact-SKU filtering retained
  0, 1, 0 texts out of 15 source reviews; the other 14 referred to neighboring variant IDs.
  No purchased-size field was returned. Do not treat these as 15 exact-SKU fit examples.
- Ozon Free restrictions: one URL per run and up to five reviews per URL in the actual test;
  the actor README also lists ten lifetime runs and 100 lifetime reviews.
- APIFY_ALLOW_GROUP_REVIEWS=false is deliberate. Setting true includes reviews returned
  for the requested product group and records reviews_scope=product_group. This changes
  the evidence scope and must be evaluated separately; it does not create purchased-size data.
- Probe run metadata and summaries are local under .venv/apify-probe (ignored by Git).
  Credentials stay in backend/.env. No production subscriptions were purchased.

WBCON would need a separate asynchronous create-task/poll-results adapter. Do not substitute its
demo server for production. Confirm time to first 20 reviews, task/status billing, SKU grouping,
support and production authentication before payment. Existing ReviewsProvider isolates this change.

The environment settings must be added to backend .env (not just the shell of the ML container).
Full stack: from backend, run
`docker compose -f docker-compose.yml -f docker-compose.full.yml up -d --build`.
ML model weights download on first start. Both backend ML URLs must target port 8001.

## Minimal live probe

For Apify reviews alone, from backend (reads APIFY_API_TOKEN from process environment
or local backend/.env; no GigaChat/database/catalog call):
```powershell
python scripts/probe_reviews.py --market wildberries --sku 32395071 --limit 20 --cap-usd 0.15
python scripts/probe_reviews.py --market ozon --sku 4339634448 --limit 5 --cap-usd 0.10
```
These commands start billable runs within the explicit cap. Free platform credits are still
consumed. Output contains counts, scope, source limitations and cost, not keys/author profiles.
Do not pass --allow-group-reviews unless variant-group evidence is explicitly intended.

The standalone probe reads process environment, NOT .env. Export the keys in your local
terminal/session using your preferred secret manager. Then from backend:
```powershell
python scripts/probe_marketplace.py --query "футболка женская" --category top --limit 3 --max-calls 10
python scripts/probe_marketplace.py --query "футболка женская" --category top --limit 3 --max-calls 10 --reviews
```
One search + up to three cards; reviews are fetched only for the first result.
The probe prints product data, call count and review counts, never keys or review authors.
It does not validate ML; run an authenticated generation through the local UI afterwards.

## Pipeline

GigaChat plan -> bounded WB search -> card normalization -> all-candidate FashionCLIP ranking
-> category-complete one-outfit selection within total budget -> selected products' reviews
-> existing B2 Size Shift -> persisted result.
Required categories come from the generated plan; shoes are no longer forced for a top/bottom request.
The backend sends outfit_count=1, while the ML API retains its legacy default of five for old clients.
Only the selected outfit contributes products to review collection.

BHAPI search summaries may lack usable images/sizes. For this pilot each candidate card
is hydrated before ML (up to MARKETPLACE_SEARCH_LIMIT per search). Do not claim that
30 fully described products cost one API call. A generation shares an attempted-call budget;
network failures count toward the local budget even if the provider does not bill them.
BHAPI temporary 502/503/504 errors are retried up to three attempts only with
explicit `retry.action=wait`; see `LOCAL_STAND.md` for cooldown and skip rules.
There are no automatic whole-generation retries, paid price-range expansion,
or unbounded pagination. Each retry reserves another attempted HTTP call.
Card cache exists only inside one generation, with no long-lived stock cache.

The card's sizes persisted in Product.sizes contain only explicitly available, priced variants.
All source variants, unknown availability, provider observation timestamp and region stay in
Product.raw_data. Displayed product price is the minimum among available priced variants,
not a promise of the price for a user's selected size. Personalized discounts are not guaranteed.
With no pickup point, the provider's default region applies. Live stock is an observation,
not a reservation: it can change before checkout.

Reviews: GET /api/v1/reviews/{sku}, market=wb, media=0, only_sku=1.
Deduplicate text+ordered size; do not keyword-filter the B2 sample. Missing size stays null.
Never substitute BHAPI review_scope tags for source text. The reviews API's optional size
field still needs live verification. ML receives up to 20 distinct texts per product.
Product.raw_data.reviews_fetch_status distinguishes available, empty and unavailable.
An unavailable reviews source or fit service does not discard a successfully assembled outfit.

## Verification and limits

Offline checks use mocked provider responses and ML encoders, with no API key or downloads:
backend: python -m pytest tests
ml: python -m unittest discover -s tests -p test_api.py
ml: python -m unittest discover -s tests -p test_single_outfit.py

Confirm: region, image accessibility, nonempty titles/prices, available size variants,
product IDs in reviews, number of calls and p50/p95 latency on real queries.
Only product data is sent to catalog/review providers; body measurements remain in StyleLink.

Still required before production:
- persistent stage checkpoints and a durable worker (current FastAPI BackgroundTasks is process-local);
- per-account provider spending limits, cross-process rate limiting and provider quota telemetry;
- persistent review snapshots/cache and precise selected-size price snapshots;
- validation of Ozon's live catalog contract and a separate adapter;
- live acceptance test with subscription keys.
Completed generations are not re-run and search-plan rows are reused. Failed/restarted
generations can still repeat upstream search/card calls; the local call cap is per attempt,
not a persistent billing ledger. Do not automatically retry the whole generation.
# Review access

Create `backend/.env.review` locally with your BHAPI_WB_TOKEN and APIFY_API_TOKEN.
This file is git-ignored; credentials are not included in the repository.
The Windows review launcher loads it before local `.env`; regular backend startup
does not load this file automatically. Existing production defaults remain
Yandex Market and five outfits. For manual review, explicitly use
`uvicorn app.main:app --env-file .env.review` from `backend`.
Local settings and process environment variables take precedence in the launcher.
These keys use real provider quotas. Never commit or share this file through Git.
Copy `.env.example` to `.env` for local database and other settings.
The currently implemented catalog is WB only; Ozon catalog search is not connected.
