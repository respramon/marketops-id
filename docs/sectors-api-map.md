# Sectors API v2 Map

Verified on **2026-08-26 (Asia/Jakarta)** against the current official documentation at `docs.sectors.app`.

MarketOps ID uses only Sectors Financial API v2. API v1 is discontinued and `/v1/*` returns HTTP 410 Gone. The production base URL is:

```text
https://api.sectors.app
```

## Authentication

Every endpoint below is authenticated with the Sectors API key as the raw value of the `Authorization` request header:

```http
Authorization: <SECTORS_API_KEY>
```

Do not add a `Bearer` prefix. The key must come from an environment variable or secret store and must never be written to logs, artifacts, fixtures, or source control.

Official sources:

- [Sectors Financial API v2 overview](https://docs.sectors.app/get-started/v2/overview)
- [Sectors Financial API v2 changelog](https://docs.sectors.app/api-references/v2/changelog)

## Verified Endpoint Summary

| Capability | Method | Exact path | Documented successful-call cost |
|---|---|---|---:|
| IDX insider/shareholder filings | `GET` | `/v2/filings/` | 1 credit |
| IDX stock suspensions | `GET` | `/v2/suspensions/` | 1 credit |
| Top market movers | `GET` | `/v2/companies/top-changes/` | 1 credit per requested classification x period combination |
| IDX news | `GET` | `/v2/news/` | 1 credit |
| Daily foreign flow by symbol | `GET` | `/v2/foreign-flow/{symbol}/` | 1 credit |
| Corporate actions by symbol | `GET` | `/v2/company/corporate-actions/{symbol}/` | 1 credit |

## Shared Billing and Failure Semantics

The v2 documentation standardizes billing by HTTP response status:

| Response | Credit behavior | Client behavior |
|---|---|---|
| `2xx` | Charge the endpoint's stated cost. | Parse the response. Empty list/filter results are valid, billable responses. |
| `404` | Charge 1 credit. | Treat as a completed lookup for a missing addressed resource, not as a retryable outage. |
| `400` | Free, except the documented natural-language Company Screener exception, which MarketOps ID does not use. | Reject or correct invalid parameters; do not retry unchanged. |
| `401` / `403` | Free. | Authentication/subscription failure; do not retry unchanged or expose the key. |
| `429` | Free. | Retry with bounded exponential backoff and jitter. |
| `5xx` | Free. | Retry boundedly; return a partial run if the source remains unavailable. |

Additional documented behavior:

- Empty list, filter, ranking, and date-range results return `200` with an empty collection and still consume credits.
- Database failures may return `503` with code `service_unavailable`; clients should retry.
- Structured middleware error codes include `subscription_does_not_allow`, `subscription_not_active`, `monthly_limit_exceeded`, `insufficient_credits`, and `service_unavailable`.
- The documented 429 example uses `error: RATE_LIMIT_EXCEEDED`.
- Transport failures with no HTTP response, including client-side timeouts, have no documented billing guarantee. MarketOps ID records only documented response-based charges in `estimated_api_credits`; the pre-call guard still prevents any *known-cost* request from starting above the configured budget.

Source: [Sectors API v2 changelog and billing standardization](https://docs.sectors.app/api-references/v2/changelog).

## 1. Company Filings

```http
GET https://api.sectors.app/v2/filings/
```

Purpose: broad discovery of IDX insider and major-shareholder buy/sell filings.

### Parameters

| Name | Location | Type/default | Notes |
|---|---|---|---|
| `symbol` | query | string, optional | One IDX symbol; four letters with optional `.jk`, case-insensitive. |
| `sector` | query | string, optional | Kebab-case sector slug. |
| `sub_sector` | query | string, optional | Kebab-case subsector slug. |
| `start` | query | `YYYY-MM-DD`, optional | Inclusive lower timestamp bound; independent of `end`. |
| `end` | query | `YYYY-MM-DD`, optional | Upper timestamp bound; future dates return 400. |
| `limit` | query | integer, default 20 | Minimum 1, maximum 30. |
| `offset` | query | integer, default 0 | Minimum 0. |
| `transaction_type` | query | enum, optional | `buy`, `sell`, or `others`. |
| `tags` | query | string, optional | Comma-separated tag slugs. |
| `holder_type` | query | enum, optional | `corporate-investor`, `insider`, or `institution`; case-insensitive. |

### Response contract

Top-level object:

- `results`: filing records.
- `pagination`: `total_count`, `showing`, `limit`, `offset`, `has_next`, `has_previous`, `next_offset`, `previous_offset`.

Each result can contain:

- Provenance/content: `title`, `body`, `source`, `timestamp`.
- Classification: `sector`, `sub_sector`, `tags`, `symbol`.
- Transaction: `transaction_type`, `holder_type`, `holder_name`, `holding_before`, `holding_after`, `amount_transaction`, `price`, `transaction_value`, `price_transaction`.
- Ownership: `share_percentage_before`, `share_percentage_after`, `share_percentage_transaction`.
- Entity links: `idx_investor_slug`, `idx_conglomerates_group_slug`.

Most content and transaction fields are nullable. `price_transaction` is not given a strict item schema; the official example shows records containing `date`, `type`, `price`, and `amount_transacted`. The v2 response does not document a stable event ID, so MarketOps ID must generate its own deterministic fingerprint.

### Cost and failures

- Cost: **1 credit** per successful request.
- Invalid filter parameters return 400.
- A future `end` date returns 400.
- Rate limiting returns 429.

Source: [Company Filings](https://docs.sectors.app/api-references/v2/indonesia/news/filings).

## 2. Stock Suspensions

```http
GET https://api.sectors.app/v2/suspensions/
```

Purpose: broad discovery of current and historical IDX suspension notices.

### Parameters

| Name | Location | Type/default | Notes |
|---|---|---|---|
| `symbol` | query | string, optional | IDX symbol, case-insensitive. |
| `start` | query | `YYYY-MM-DD`, optional | Inclusive lower bound on `suspension_date`; independent of `end`. |
| `end` | query | `YYYY-MM-DD`, optional | Upper bound; future dates return 400. |
| `limit` | query | integer, default 20 | Minimum 1, maximum 30. |
| `offset` | query | integer, default 0 | Minimum 0. |

### Response contract

Top-level `results` and the same `pagination` structure used by filings. Each result contains:

- `symbol`: IDX symbol with `.JK` suffix.
- `suspension_date`: date the suspension took effect.
- `reason`: nullable official reason.
- `pdf_url`: nullable link to the official IDX PDF notice.

No stable event ID is documented; the normalized event fingerprint must use the canonical symbol, suspension date, and source/reference fields.

### Cost and failures

- Cost: **1 credit** per successful request.
- A future `end` date returns 400.
- Rate limiting returns 429.
- A valid date window with no rows returns a billable 200 with empty `results`.

Source: [Stock Suspensions](https://docs.sectors.app/api-references/v2/indonesia/news/suspensions).

## 3. Top Company Movers

```http
GET https://api.sectors.app/v2/companies/top-changes/
```

Purpose: broad discovery of the largest positive and negative price movements.

### Parameters

| Name | Location | Type/default | Notes |
|---|---|---|---|
| `sub_sector` | query | string, optional | Kebab-case subsector slug. |
| `n_stock` | query | integer, default 5 | Minimum 1, maximum 10 per period. |
| `classifications` | query | comma-separated array, default all | `top_gainers`, `top_losers`; default requests both. |
| `periods` | query | comma-separated array, default all | `1d`, `7d`, `14d`, `30d`, `365d`; default requests all five. |
| `min_mcap_billion` | query | integer, default 5000 | Minimum 0; unit is billion IDR. |

MarketOps ID must explicitly request:

```text
classifications=top_gainers,top_losers&periods=1d
```

This avoids the expensive default of two classifications across five periods.

### Response contract

The response has `top_gainers` and `top_losers`; each is keyed by requested period. Each mover contains:

- `name`
- `symbol`
- `price_change`
- `last_close_price`
- `latest_close_date`

`price_change` is a decimal fraction, so `0.05` means `+5%` and `-0.05` means `-5%`.

### Cost and failures

- Cost: **1 credit per classification x period combination**.
- MarketOps ID's two classifications for only `1d` cost **2 credits**.
- The endpoint default costs **10 credits** (`2 x 5`) and must not be used implicitly.
- Invalid classifications or periods return 400.
- Rate limiting returns 429.

Source: [Top Company Movers](https://docs.sectors.app/api-references/v2/indonesia/ranking/top-changes).

## 4. News Articles

```http
GET https://api.sectors.app/v2/news/
```

Purpose: selectively enrich the candidate universe with related IDX news.

### Parameters

| Name | Location | Type/default | Notes |
|---|---|---|---|
| `extension` | query | enum, default `idx` | `idx` or `mining`. MarketOps ID uses `idx`. |
| `start` | query | `YYYY-MM-DD`, optional | Independent lower timestamp bound. |
| `end` | query | `YYYY-MM-DD`, optional | Independent upper bound; future dates return 400. |
| `limit` | query | integer, default 20 | Minimum 1, maximum 30. |
| `offset` | query | integer, default 0 | Minimum 0. |
| `keyword` | query | string, optional | Case-insensitive substring match on title; valid for both extensions. |
| `sector` | query | string, optional | IDX only; comma-separated sector slugs. |
| `sub_sector` | query | string, optional | IDX only; comma-separated subsector slugs. |
| `tags` | query | string, optional | IDX only; comma-separated tag slugs. |
| `symbols` | query | string, optional | IDX only; comma-separated IDX symbols, e.g. `BBCA,BBRI`. |
| `commodity_type` | query | enum, optional | Mining only; not used by MarketOps ID. |

Important: filings use `symbol` singular, while news uses `symbols` plural.

### Response contract

Top-level `results` and `pagination`. An IDX news item can contain:

- `title`
- `body`
- `source`
- `timestamp`
- `sector`
- `sub_sector[]`
- `tags[]`
- `symbols[]`
- `thumbnail`
- `dimension`

Only `title`, `source`, and `timestamp` are required by the documented schema. Other fields must be parsed defensively. `dimension` does not have a detailed field contract and is not used as an input to the Research Attention Score.

### Cost and failures

- Cost: **1 credit** per successful request.
- Mixing IDX-only and mining-only parameters returns 400.
- Invalid date formats and future `end` dates return 400.
- Rate limiting returns 429.

Source: [News Articles](https://docs.sectors.app/api-references/v2/indonesia/news/news).

## 5. Daily Net Foreign Inflow

```http
GET https://api.sectors.app/v2/foreign-flow/{symbol}/
```

Purpose: selectively enrich one candidate ticker with foreign-broker net flow history.

### Parameters

| Name | Location | Type/default | Notes |
|---|---|---|---|
| `symbol` | path | string, required | Four-letter IDX symbol; optional `.jk`, case-insensitive. |
| `start` | query | `YYYY-MM-DD`, optional | Default is 30 days before `end`. |
| `end` | query | `YYYY-MM-DD`, optional | Default is today. |

Maximum date range: **90 days**.

### Response contract

- `symbol`
- `start`
- `end`
- `data[]`, with each point containing:
  - `date`
  - `net_foreign_inflow`: integer IDR; positive means foreign brokers were net buyers and negative means net sellers.

Only foreign flow is returned because the documented domestic net flow is always its inverse for the same symbol and date.

The API does **not** return an anomaly ratio. MarketOps ID must calculate its configured 2x/4x anomaly heuristic locally from the returned time series and document the chosen deterministic baseline.

### Cost and failures

- Cost: **1 credit** per symbol request.
- An unknown symbol in broker data returns 404 and consumes 1 credit under the shared billing rules.
- Rate limiting returns 429.

Source: [Daily Net Foreign Inflow](https://docs.sectors.app/api-references/v2/indonesia/brokers/foreign-flow-by-symbol).

## 6. Corporate Actions

```http
GET https://api.sectors.app/v2/company/corporate-actions/{symbol}/
```

Purpose: selectively enrich one candidate ticker with corporate-action history and upcoming events.

### Parameters

| Name | Location | Type/default | Notes |
|---|---|---|---|
| `symbol` | path | string, required | Four-letter IDX symbol; optional `.jk`, case-insensitive. |

There are no documented query parameters.

### Response contract

The response contains `symbol` and `corporate_actions`, grouped into:

- `dividend`
- `upcoming_dividend`
- `stock_split`
- `right_issue`
- `warrant`
- `bonus`
- `agm`

The official OpenAPI schema deliberately leaves the item objects untyped. Its example shows, but does not contractually guarantee:

- AGM: `agm_date`, `agm_time`, `agm_place`, `agm_result`.
- Dividend: `ex_date`, `payment_date`, `dividend_yield`, `dividend_amount`.
- Stock split: `date`, `split_ratio`.

The official example also uses `null` for some categories even though the outer schema describes arrays. The client must therefore accept `null | list[object]`, preserve the raw record for auditability, and only normalize known date fields. The "upcoming within 7 days" score rule can be applied only when a parseable event date is present; unknown shapes must not be invented.

### Cost and failures

- Cost: **1 credit** per symbol request.
- An unknown symbol returns 404 and consumes 1 credit under the shared billing rules.
- Rate limiting returns 429.

Source: [Corporate Actions](https://docs.sectors.app/api-references/v2/indonesia/company/corporate-actions).

## Per-Run Credit Budget

MarketOps ID follows **discover broadly, enrich selectively** and limits enrichment to at most five candidate symbols.

| Stage | Request strategy | Maximum estimated credits |
|---|---|---:|
| Filing discovery | One 30-record page of `/v2/filings/` | 1 |
| Suspension discovery | One 30-record page of `/v2/suspensions/` | 1 |
| Mover discovery | Both classifications, only `1d` | 2 |
| News enrichment | One request with up to five comma-separated `symbols` | 1 |
| Foreign-flow enrichment | One request per candidate, maximum five | 5 |
| Corporate-action enrichment | One request per candidate, maximum five | 5 |
| **Maximum planned total** | **Five candidates** | **15 credits** |

Operational constraints:

- `MARKETOPS_MAX_API_CREDITS_PER_RUN` is a hard guard, not an advisory metric.
- The client reserves the documented endpoint cost before starting a logical operation.
- No enrichment request starts if its reservation would exceed the configured remaining budget.
- The workflow explicitly supplies mover classifications and periods; it never relies on the 10-credit default.
- News for all selected candidates is combined into one `symbols` request.
- The client can follow documented `next_offset` pagination when explicitly asked for more than 30 records and when budget remains. The scheduled default intentionally caps each list source at one 30-record page; a `has_next` response is recorded as a source gap and makes the run `PARTIAL`.
- Estimated and observed request outcomes are written to run metadata. No API key is logged.

At the recommended default of 15 credits, discovery and enrichment for five candidates fit exactly. A lower configured limit causes later enrichment to be skipped fail-soft; the queue is still generated from the evidence already collected and the run status records the missing source.
