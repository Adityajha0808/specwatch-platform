# SpecWatch Platform - Architecture

## Problem Statement

Third-party API changes (breaking changes, deprecations, silent behavior modifications) frequently cause production incidents because:

1. **Discovery Gap**: No systematic way to track when APIs publish changes
2. **Signal-to-Noise**: Changelog noise makes it hard to identify critical changes
3. **Impact Blindness**: Teams don't know which services are affected until runtime failures
4. **Reactive Response**: Changes are discovered through incidents, not proactively
5. **Version Drift**: No historical context of API evolution for debugging

**Target**: Detect and classify API changes before they reach production, with actionable intelligence about internal impact.

## Project Structure Mapping

```
specwatch-platform/
├── specwatch/               # Core library (importable package)
│   ├── discovery/          → Discovery Layer (Tavily integration)
│   ├── ingestion/          → Ingestion Layer (fetchers, parsers)
│   ├── normalization/      → Normalization Layer (schema mapping)
│   ├── diff/               → Diff Engine (change detection)
│   ├── classification/     → Change Classifier (LLM integration)
│   ├── impact/             → Impact Engine (Phase 2)
│   ├── alerting/           → Alerting Layer (Slack, GitHub)
│   ├── storage/            → Storage abstraction layer
│   ├── orchestration/      → Pipeline orchestration (scheduler, workers)
│   ├── config/             → Configuration management
│   └── utils/              → Shared utilities
├── pipelines/              # Workflow definitions (DAGs)
├── schemas/                # JSON schemas for validation
├── storage/                # Local storage (dev) / mount point (prod)
├── docs/                   # Documentation
├── tests/                  # Unit + integration tests
└── scripts/                # DevOps automation
```

## System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      DISCOVERY LAYER                             │
│  ┌──────────┐                                                    │
│  │  Tavily  │──► API docs, changelogs, OpenAPI specs, repos     │
│  └──────────┘                                                    │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      INGESTION LAYER                             │
│  Parallel fetchers:                                              │
│  ├─ HTML/Markdown scraper                                        │
│  ├─ OpenAPI spec parser                                          │
│  ├─ GitHub API client (SDK repos)                                │
│  └─ RSS/Atom changelog watcher                                   │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                   NORMALIZATION LAYER                            │
│  Transforms heterogeneous sources into canonical schema          │
│  ├─ Endpoint extraction                                          │
│  ├─ Parameter type inference                                     │
│  ├─ Response schema parsing                                      │
│  └─ Metadata standardization                                     │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                   VERSION STORAGE (S3/GCS)                       │
│  api_name/                                                       │
│    ├─ snapshots/                                                 │
│    │   ├─ 2024-01-15T10:00:00Z.json                              │
│    │   ├─ 2024-01-16T10:00:00Z.json                              │
│    │   └─ ...                                                    │
│    └─ metadata.json (discovery config, last fetch, etc)          │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                        DIFF ENGINE                               │
│  Structural diffing:                                             │
│  ├─ Endpoint presence changes (added/removed)                    │
│  ├─ Parameter schema changes (type, required, default)           │
│  ├─ Response structure changes                                   │
│  ├─ Auth requirement changes                                     │
│  └─ Semantic diffing (LLM-assisted for prose changes)            │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                   CHANGE CLASSIFIER (LLM)                        │
│  Input: Structural diff + context                                │
│  Output:                                                         │
│    ├─ Classification: breaking | deprecation | additive | minor  │
│    ├─ Confidence score: 0.0-1.0                                  │
│    ├─ Reasoning: natural language explanation                    │
│    └─ Affected operations: list of impacted endpoints            │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      IMPACT ENGINE                               │
│  (Phase 2 - placeholder in Phase 1)                              │
│  Maps changes to internal systems via:                           │
│  ├─ Dependency graph (which services use which APIs)             │
│  ├─ Code scanning (SDK usage detection)                          │
│  └─ Call trace analysis (runtime API usage)                      │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ALERTING LAYER                              │
│  ├─ Slack webhook (immediate for breaking changes)               │
│  ├─ GitHub Issues (tracking for deprecations)                    │
│  ├─ Email digest (weekly summary)                                │
│  └─ Future: CI pipeline integration, webhooks                    │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Module Mapping

| Layer | Module | Files | Responsibilities |
|-------|--------|-------|------------------|
| **Discovery** | `specwatch.discovery` | `tavily_client.py`, `source_resolver.py` | Query Tavily API, resolve source URLs, cache discovery results |
| **Ingestion** | `specwatch.ingestion` | `fetcher.py`, `parser.py` | Async HTTP fetching, content parsing (HTML/JSON/YAML) |
| **Normalization** | `specwatch.normalization` | `normalizer.py`, `schema_mapper.py` | Convert heterogeneous sources to canonical schema |
| **Storage** | `specwatch.storage` | `raw_discovery_store.py`, `normalized_store.py`, `version_store.py`, `diff_store.py` | Abstract storage operations (local FS for dev, S3 for prod) |
| **Diff** | `specwatch.diff` | `diff_engine.py`, `diff_rules.py` | JSON diffing, heuristic filtering |
| **Classification** | `specwatch.classification` | `llm_client.py`, `change_classifier.py` | Claude API integration, prompt engineering |
| **Alerting** | `specwatch.alerting` | `slack_notifier.py`, `github_notifier.py` | Notification delivery |
| **Orchestration** | `specwatch.orchestration` | `scheduler.py`, `queue.py`, `worker.py` | Cron scheduling, async task queue |
| **Pipelines** | `pipelines/` | `*_pipeline.py`, `main_pipeline.py` | Workflow DAGs, compose modules into end-to-end flows |

## Component Responsibilities

### 1. Discovery Layer
**Input**: API names (e.g., "Stripe", "Twilio", "OpenAI")
**Process**:
- Query Tavily to find authoritative sources
- Prioritize: OpenAPI specs > official docs > changelogs > SDK repos
- Store source URLs with metadata (trust score, last-modified)

**Output**: `discovery_config.json` per API
```json
{
  "api_name": "Stripe",
  "sources": {
    "openapi": "https://raw.githubusercontent.com/stripe/openapi/master/openapi/spec3.json",
    "docs": "https://stripe.com/docs/api",
    "changelog": "https://stripe.com/docs/upgrades",
    "sdk_repo": "https://github.com/stripe/stripe-python"
  },
  "discovered_at": "2024-01-15T10:00:00Z",
  "tavily_confidence": 0.95
}
```

**Failure Modes**:
- Tavily returns no results → fallback to manual config
- Multiple conflicting sources → rank by domain authority + freshness

### 2. Ingestion Layer
**Input**: Source URLs from discovery
**Process**:
- Parallel async fetchers (aiohttp)
- Content-type specific parsers:
  - OpenAPI: YAML/JSON schema validation
  - HTML: BeautifulSoup + readability extraction
  - Markdown: frontmatter + body parsing
- Rate limiting per domain (respect robots.txt)
- Retry logic: exponential backoff, 3 attempts

**Output**: Raw versioned files in object storage
```
s3://api-snapshots/stripe/raw/2024-01-15T10:00:00Z/
  ├─ openapi.json
  ├─ docs.html
  ├─ changelog.md
  └─ sdk_readme.md
```

**Failure Modes**:
- Rate limiting → queue for retry, alert if persistent
- Content format changes → log for manual normalization rule update
- Auth required → store credentials in secrets manager

### 3. Normalization Layer
**Input**: Raw heterogeneous content
**Process**:
1. **OpenAPI Priority**: If OpenAPI spec exists, it's ground truth
2. **Doc Parsing**: Extract endpoint patterns via regex + LLM validation
3. **Schema Inference**: Build JSON schema from examples
4. **Unification**: Merge all sources into canonical format

**Output**: `normalized.json`
```json
{
  "version_timestamp": "2024-01-15T10:00:00Z",
  "endpoints": [
    {
      "path": "/v1/customers",
      "method": "POST",
      "auth": "bearer",
      "parameters": [
        {
          "name": "email",
          "location": "body",
          "type": "string",
          "required": true,
          "description": "Customer email address"
        }
      ],
      "response": {
        "200": {
          "schema": {
            "type": "object",
            "properties": {
              "id": {"type": "string"},
              "email": {"type": "string"}
            }
          }
        }
      },
      "deprecated": false,
      "source_confidence": 0.98
    }
  ]
}
```

**Failure Modes**:
- Schema ambiguity → flag for human review, continue with best-effort
- Missing critical info → use previous version as template, mark uncertainty

### 4. Version Storage
**Storage**: S3/GCS with lifecycle policies
**Structure**: storage/raw/raw_discovery

**Metadata tracking**:
- Fetch timestamps
- Source URLs
- Normalization version (schema evolution)
- Compression (gzip for older snapshots)

**Retention**: 
- Daily snapshots for 90 days
- Weekly snapshots for 1 year
- Monthly snapshots indefinitely

### 5. Diff Engine
**Input**: Two normalized snapshots (t1, t2)
**Process**:
1. **Structural Diff**: JSON deep diff
   - Endpoint additions/removals
   - Parameter changes (type, required flag, constraints)
   - Response schema changes
2. **Semantic Diff**: LLM for description/behavior changes
   - Detect silent logic changes from changelog prose
   - Identify deprecation warnings

**Output**: `diff.json`
```json
{
  "from_version": "2024-01-15T10:00:00Z",
  "to_version": "2024-01-16T10:00:00Z",
  "changes": [
    {
      "type": "parameter_removed",
      "endpoint": "/v1/customers",
      "method": "POST",
      "details": {
        "parameter": "description",
        "was_required": false,
        "previous_type": "string"
      }
    },
    {
      "type": "parameter_type_changed",
      "endpoint": "/v1/charges",
      "method": "POST",
      "details": {
        "parameter": "amount",
        "old_type": "integer",
        "new_type": "string",
        "reason": "supports decimal currencies"
      }
    }
  ]
}
```

**Algorithms**:
- Tree diffing (Myers' diff algorithm)
- Type coercion detection (int → string is breaking if strict validation)

### 6. Change Classifier (LLM)
**Model**: Claude Sonnet 4.5 (cost-effective, fast)
**Prompt Strategy**:
```
You are an API compatibility expert. Given this diff:
{diff}

And this context:
- API: {api_name}
- Previous version date: {t1}
- New version date: {t2}

Classify each change as:
- "breaking": Existing clients will fail
- "deprecation": Works now, will break in future
- "additive": New functionality, backward compatible
- "minor": Documentation/metadata only

For each change, provide:
1. Classification
2. Confidence (0.0-1.0)
3. Reasoning (one sentence)
4. Affected client operations
```

**Output**: `classification.json`
```json
{
  "classifications": [
    {
      "change_id": "param_removed_customers_description",
      "classification": "breaking",
      "confidence": 0.92,
      "reasoning": "Required parameter removal will cause validation errors",
      "affected_operations": ["POST /v1/customers"],
      "migration_path": "Remove 'description' from request body"
    }
  ],
  "overall_severity": "high",
  "breaking_count": 1,
  "deprecation_count": 0
}
```

**Cost Control**:
- Batch multiple diffs per LLM call
- Cache classifications for identical diffs
- Use structured output (JSON mode) to reduce token usage

### 7. Impact Engine (Phase 2)
**Placeholder in Phase 1**: Store classifications without impact mapping

**Future Design**:
- Scan internal repos for SDK imports
- Build dependency graph (service → API endpoints)
- Runtime call tracing integration
- Impact scoring: `severity × usage_frequency × blast_radius`

### 8. Alerting Layer
**Inputs**: Classifications + impact data
**Logic**:
- **Breaking changes**: Immediate Slack alert to #eng-alerts
- **Deprecations**: GitHub issue with 30-day SLA
- **Additive/Minor**: Weekly digest email

**Slack Alert Format**:
```
🚨 Breaking API Change Detected

API: Stripe
Change: Required parameter 'email' removed from POST /v1/customers
Severity: High (confidence: 0.92)
Detected: 2024-01-16 10:05 UTC

Action Required:
- Update request payloads to remove 'email' parameter
- Affected services: [TBD - Phase 2]

Details: https://api-changes.internal/stripe/diff/abc123
```

**Delivery**:
- Slack webhook (primary)
- Fallback to email if webhook fails
- Log all alerts to audit trail

## Data Flow

```
1. Scheduler triggers daily cron
   ↓
2. Discovery Layer queries Tavily for each tracked API
   ↓
3. Ingestion Layer fetches all sources in parallel
   ↓
4. Normalization Layer converts to canonical schema
   ↓
5. Storage Layer persists snapshot with timestamp
   ↓
6. Diff Engine compares with previous snapshot
   ↓
7. If changes detected:
   ├─ Change Classifier (LLM) analyzes severity
   ├─ Impact Engine (Phase 2) maps to internal services
   └─ Alerting Layer dispatches notifications
   ↓
8. Log metrics (latency, cost, detection accuracy)
```

**Async Pipeline**: All steps after ingestion are event-driven (message queue)

## Failure Points & Mitigations

| Failure Point | Impact | Mitigation |
|---------------|--------|------------|
| Tavily unavailable | No new discoveries | Fallback to cached source URLs, alert ops |
| Source URL 404 | Incomplete snapshot | Mark as stale, retry with exponential backoff, alert after 3 failures |
| Normalization error | No diff possible | Skip diff, log error, use previous snapshot as baseline |
| LLM API timeout | No classification | Queue for retry, use heuristic rules as fallback |
| Storage write failure | Lost snapshot | Multi-region replication, retry with jitter |
| Alert delivery failure | Missed notification | Dual-channel (Slack + email), dead letter queue for retries |

**Monitoring**:
- End-to-end pipeline latency (target: <5 min for critical changes)
- Classification accuracy (human feedback loop)
- False positive rate (deprecations that don't break)
- Cost per API per day

## Scaling Path

### Phase 1 (2 APIs)
- Single EC2 instance / Cloud Run job
- S3 for storage
- Synchronous LLM calls

### Phase 2 (10-20 APIs)
- Message queue (SQS/Pub/Sub) for async processing
- Parallel workers for ingestion
- LLM request batching

### Phase 3 (100+ APIs)
- Kubernetes for orchestration
- Distributed diff engine (Apache Beam)
- LLM caching layer (Redis)
- Multi-tenant storage partitioning

**Cost Projections** (per API per day):
- Storage: ~$0.01 (1MB compressed snapshot)
- LLM: ~$0.05 (avg 10 changes × 500 tokens × $0.001/1K tokens)
- Compute: ~$0.10 (15 min runtime on spot instances)
- **Total**: ~$0.16/API/day → $58/API/year

For 20 APIs: ~$1,200/year infrastructure cost.

## Technology Stack (Phase 1)

| Layer | Technology | Implementation Details |
|-------|-----------|----------------------|
| **Language** | Python 3.11+ | Type hints, async/await, dataclasses |
| **Discovery** | Tavily API | `tavily-python` SDK, free tier (1000 queries/day) |
| **HTTP Client** | `aiohttp` | Async fetching, connection pooling, retry middleware |
| **Parsing** | `beautifulsoup4`, `pyyaml`, `pydantic` | HTML scraping, OpenAPI parsing, validation |
| **Storage (Dev)** | Local filesystem | JSON files in `storage/` directory |
| **Storage (Prod)** | AWS S3 + DynamoDB | Versioned snapshots (S3), metadata index (DynamoDB) |
| **Diff** | `dictdiffer` | Nested JSON comparison, minimal diffs |
| **LLM** | Anthropic Claude API | `anthropic` Python SDK, Sonnet 4.5 model |
| **Alerting** | Slack Webhooks | `slack_sdk`, incoming webhook URL in `.env` |
| **Orchestration** | `schedule` library | Simple cron-like scheduler (upgrade to Prefect in Phase 2) |
| **Config** | `pydantic-settings` | Type-safe env var loading, `.env` file support |
| **Logging** | `structlog` | JSON logs, correlation IDs, ECS format |
| **Testing** | `pytest`, `pytest-asyncio` | Unit tests, async fixture support |

### Key Dependencies (`requirements.txt`)
```
# Core
pydantic>=2.0
pydantic-settings>=2.0
aiohttp>=3.9
beautifulsoup4>=4.12
pyyaml>=6.0
dictdiffer>=0.9

# External APIs
tavily-python>=0.3
anthropic>=0.40
slack-sdk>=3.27

# Storage (production)
boto3>=1.34  # AWS S3/DynamoDB
# google-cloud-storage>=2.10  # Alternative: GCS

# Orchestration
schedule>=1.2  # Phase 1
# prefect>=2.0  # Phase 2

# Utils
structlog>=24.1
python-dotenv>=1.0
tenacity>=8.2  # Retry logic

# Dev/Test
pytest>=8.0
pytest-asyncio>=0.23
pytest-cov>=4.1
black>=24.0
ruff>=0.1
mypy>=1.8
```

## Phase 1 Implementation Roadmap

### Week 1: Foundation (Days 1-7)
**Goal**: End-to-end skeleton pipeline for 1 API

**Day 1-2: Environment Setup**
- Initialize Git repo, create `.env` from `.env.example`
- Set up virtual environment: `python -m venv venv`
- Install dependencies: `pip install -r requirements.txt`
- Get API keys: Tavily (free tier), Anthropic (credits), Slack webhook
- Test connections: write `tests/test_connections.py` to verify API keys work

**Day 3-4: Discovery + Ingestion**
- Implement `specwatch/discovery/tavily_client.py`:
  - `discover_sources(api_name: str) -> DiscoveryResult`
  - Cache results to `storage/raw/raw_discovery/{api_name}/discovery.json`
- Implement `specwatch/ingestion/fetcher.py`:
  - `fetch_url(url: str) -> bytes` with aiohttp
  - Rate limiting, retry logic (use `tenacity`)
- Write pipeline: `pipelines/discovery_pipeline.py`
  - Hard-code Stripe as test API
  - Fetch OpenAPI spec from discovered URL
  - Save to `storage/raw/raw_discovery/stripe/YYYY-MM-DD.json`

**Day 5-6: Normalization**
- Define canonical schema in `schemas/api_schema.json`:
  ```json
  {
    "endpoints": [
      {
        "path": "/v1/customers",
        "method": "POST",
        "parameters": [...],
        "response": {...}
      }
    ]
  }
  ```
- Implement `specwatch/normalization/normalizer.py`:
  - `normalize_openapi(spec: dict) -> NormalizedAPI`
  - Extract endpoints, parameters, responses
- Save normalized snapshot to `storage/normalized-store/stripe/YYYY-MM-DD.json`

**Day 7: First Integration Test**
- Run full pipeline manually: `python pipelines/main_pipeline.py --api stripe`
- Verify files created in `storage/`
- Debug issues, add logging

### Week 2: Diff + Classification (Days 8-14)
**Goal**: Detect changes and classify with LLM

**Day 8-9: Diff Engine**
- Implement `specwatch/diff/diff_engine.py`:
  - `compute_diff(old: NormalizedAPI, new: NormalizedAPI) -> Diff`
  - Use `dictdiffer.diff()`
  - Filter noise (e.g., timestamp changes in metadata)
- Write test with synthetic snapshots that have known differences

**Day 10-11: LLM Classification**
- Implement `specwatch/classification/llm_client.py`:
  - `classify_change(diff: Diff) -> Classification`
  - Prompt engineering (see `docs/prompts.md`)
  - Handle rate limits, timeouts
- Test with real Stripe API diffs (manually create v1 vs v2 snapshots)

**Day 12-13: Alerting**
- Implement `specwatch/alerting/slack_notifier.py`:
  - `send_alert(classification: Classification) -> None`
  - Format message with emoji, severity, link to diff
- Test with dummy breaking change

**Day 14: End-to-End Test**
- Create two synthetic Stripe snapshots with intentional breaking change
- Run: `python pipelines/main_pipeline.py --api stripe --compare 2024-01-01 2024-01-02`
- Verify Slack alert received

### Week 3-4: Automation + Second API (Days 15-28)
**Goal**: Add scheduler, onboard OpenAI API

**Day 15-17: Orchestration**
- Implement `specwatch/orchestration/scheduler.py`:
  - Daily cron: `schedule.every().day.at("10:00").do(run_pipeline)`
  - Job: discover → ingest → normalize → diff → classify → alert
- Run scheduler in background: `python main.py`

**Day 18-20: Second API (OpenAI)**
- Add OpenAI to config: `config/apis.yaml`
- Run discovery for OpenAI
- Handle different doc structure (OpenAI uses custom docs, not OpenAPI spec)
- Update normalizer to support multiple source types

**Day 21-23: Storage Abstraction**
- Implement `specwatch/storage/version_store.py`:
  - `store_snapshot(api_name, data) -> None`
  - `get_latest(api_name) -> Snapshot`
  - Abstract FS vs S3 (use environment variable to switch)
- Migrate existing code to use `version_store` instead of direct file I/O

**Day 24-26: Robustness**
- Add comprehensive error handling
- Implement dead letter queue for failed jobs (store in `storage/failed-jobs/`)
- Add metrics logging (pipeline duration, API response times)

**Day 27-28: Documentation + Demo**
- Write `README.md` with setup instructions
- Record demo video showing breaking change detection
- Prepare for Phase 2 planning

## Phase 1 Success Metrics

1. **Coverage**: All APIs (Stripe, Twilio, OpenAI) ingested daily
2. **Latency**: Pipeline completes in <10 minutes
3. **Accuracy**: LLM correctly classifies 90%+ of changes (manual validation)
4. **Reliability**: <1% failure rate on ingestion
5. **Cost**: <$20/month total spend

## Security Considerations

- **API Keys**: Store in `.env`, never commit to Git
- **Secret Rotation**: Tavily, Anthropic, Slack keys rotated every 90 days
- **Data Sensitivity**: Don't store actual API request/response data, only schemas
- **Access Control**: `.env` file permissions set to `600` (owner read/write only)
- **Audit Trail**: All classifications logged to `logs/audit.jsonl`

## Development Workflow

1. **Feature branches**: `git checkout -b feat/diff-engine`
2. **Type checking**: `mypy specwatch/` before commit
3. **Formatting**: `black specwatch/ && ruff check specwatch/`
4. **Tests**: `pytest tests/ -v --cov=specwatch`
5. **PR reviews**: At least one approval before merge

## Future Enhancements (Beyond Phase 3)

1. **ML-based anomaly detection**: Detect undocumented changes via traffic analysis
2. **Auto-remediation**: Generate PR drafts for breaking changes
3. **Impact simulation**: Run integration tests against new API versions
4. **Community intelligence**: Crowdsource change interpretations
5. **Multi-cloud support**: Track AWS/GCP/Azure service API changes
