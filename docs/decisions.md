# SpecWatch Platform - Key Decisions

## Phase 1 Specific Decisions

### Why `schedule` Library Instead of Prefect/Airflow?

**Decision**: Use simple `schedule` library for Phase 1, defer to Prefect/Airflow in Phase 2.

**Rationale**:
- **Simplicity**: `schedule` is 200 lines of code, Prefect is 50K+ LOC
- **Learning curve**: Zero learning curve for `schedule.every().day.at("10:00")`
- **Overhead**: Prefect requires server/database, overkill for 2 APIs
- **Migration path**: Easy to swap scheduler without changing pipeline logic

**Phase 1 Implementation**:
```python
import schedule
import time

def run_pipeline():
    # Execute discovery → ingest → normalize → diff → classify → alert
    pass

schedule.every().day.at("10:00").do(run_pipeline)

while True:
    schedule.run_pending()
    time.sleep(60)
```

**When to migrate**: When you need:
- DAG visualization
- Dynamic task dependencies
- Distributed execution
- Retry policies more complex than exponential backoff

**Cost**: $0 (vs Prefect Cloud at $10/month minimum)

---

### Why Local Filesystem for Phase 1 Storage?

**Decision**: Use `storage/` directory with JSON files instead of S3 for Phase 1.

**Rationale**:
- **Iteration speed**: No AWS setup, no credentials, immediate feedback
- **Debugging**: Can inspect files with `cat`, `jq`, VSCode
- **Cost**: $0 vs S3 at ~$2/month
- **Abstraction**: Build storage interface that can swap FS ↔ S3 with env var

**Implementation**:
```python
# specwatch/storage/version_store.py
class VersionStore:
    def store_snapshot(self, api_name: str, data: dict):
        if os.getenv("STORAGE_BACKEND") == "s3":
            self._s3_client.put_object(...)
        else:
            path = f"storage/normalized-store/{api_name}/{timestamp}.json"
            with open(path, 'w') as f:
                json.dump(data, f)
```

**Migration trigger**: When `storage/` exceeds 1GB or you need multi-machine access.

---

### Why Skip Impact Engine in Phase 1?

**Decision**: Phase 1 alerts include "Affected services: TBD", implement impact mapping in Phase 2.

**Rationale**:
- **Complexity**: Requires repo scanning, dependency graph building, call tracing
- **MVP blocker**: Can prove value (detect changes) without impact analysis
- **Scope creep**: Impact engine is a separate project (requires access to internal codebases)

**Phase 1 workaround**:
- Alerts say: "Breaking change detected. Manually check services using Stripe API."
- Engineers triage based on knowledge of their systems

**Phase 2 approach**:
- Scan repos for SDK imports: `grep -r "from stripe import" repos/`
- Build dependency graph: `service-a → uses → stripe.customers.create`
- Tag alerts: "Impacts: service-a, service-b"

---

## Why Tavily for Discovery?

### Decision
Use Tavily as the primary discovery mechanism for finding API documentation sources.

### Rationale
**Evaluated Alternatives**:
1. **Manual source configuration** - High maintenance, doesn't scale
2. **Google Custom Search API** - Inferior freshness, poor ranking for technical docs
3. **Bing Web Search** - Weaker results for GitHub repos and technical content
4. **Algolia DocSearch** - Limited to sites that opt-in

**Why Tavily Wins**:
- **Fresh content**: Optimized for recent documentation updates
- **Developer-focused**: Better at finding OpenAPI specs, SDK repos, changelogs
- **Structured output**: Returns ranked results with metadata (last-modified, confidence)
- **Cost-effective**: $1/1000 queries vs Google's $5/1000
- **GitHub integration**: Native understanding of repo structure

**Tradeoffs**:
- **Vendor lock-in**: Switching cost if Tavily degrades or pivots
- **Rate limits**: 1000 queries/day on free tier
- **Dependency**: Service outage blocks discovery (mitigated by cached sources)

**Mitigation**:
- Cache discovery results with 7-day TTL
- Fallback to manual config file if Tavily fails
- Monitor query quota, alert at 80% usage

---

## Why Versioned Storage Instead of Git?

### Decision
Store API snapshots in S3/GCS as timestamped JSON files instead of Git commits.

### Rationale
**Evaluated Alternatives**:
1. **Git repository per API** - Natural versioning, easy diffs
2. **Database with JSONB columns** - Query-friendly, no file I/O
3. **Event stream (Kafka)** - Real-time, but overkill for daily snapshots

**Why Object Storage Wins**:
- **Cost**: S3 Standard-IA is ~$0.0125/GB/month vs Git LFS at ~$0.50/GB/month
- **Scale**: No repo size limits, handles 1000s of APIs without performance degradation
- **Simplicity**: No merge conflicts, no branch management
- **Immutability**: Append-only model prevents accidental overwrites
- **Lifecycle policies**: Auto-archive to Glacier for cost optimization

**Tradeoffs**:
- **No native diffing**: Must implement custom diff logic (vs `git diff`)
- **Query overhead**: Can't SQL query across versions (vs database)
- **No atomic transactions**: Potential for partial writes during failures

**Mitigation**:
- Use DynamoDB for metadata indexing (timestamps, checksums)
- Implement two-phase commit: write to temp path, then atomic rename
- Compress old snapshots (gzip), reducing storage cost by 70%

**Why Not Git Specifically**:
- Git's data model (content-addressable) creates overhead for large JSON blobs
- Snapshot sizes (100KB-5MB) exceed GitHub file size soft limits quickly
- Merge conflicts from concurrent updates are non-sensical for automated snapshots
- No branching needed—linear history suffices

---

## Why JSON Diffing Over Semantic Versioning?

### Decision
Compute diffs from raw JSON snapshots instead of relying on API providers' semantic version numbers.

### Rationale
**Problem with Semantic Versioning**:
- **Inconsistent adherence**: Not all APIs follow semver strictly (e.g., Stripe uses dated versions like "2026-01-15")
- **Silent breaking changes**: Providers may increment patch version despite breaking changes
- **Undocumented changes**: Version bump without changelog explanation
- **Deprecation lag**: Features marked deprecated but still work for months

**Why Structural Diffing Wins**:
- **Ground truth**: Detects actual changes, not what provider claims changed
- **Catches omissions**: Finds undocumented behavior changes
- **Vendor-agnostic**: Works regardless of versioning scheme
- **Automation-friendly**: No manual changelog parsing

**Diff Algorithm Choice**: dictdiffer (Python library)
- Handles nested JSON structures
- Produces minimal diff (only changed paths)
- Supports list reordering detection (important for parameter arrays)

**Tradeoffs**:
- **Noise**: May flag cosmetic changes (description rewording)
- **Compute cost**: O(n) comparison on every snapshot pair
- **False positives**: Type coercion changes (int→float) may not be breaking

**Mitigation**:
- LLM classifier filters noise from structural diff
- Cache diff results by snapshot hash to avoid re-computation
- Heuristic rules for common non-breaking patterns (e.g., adding optional params)

---

## Why LLM Classification Instead of Rules Engine?

### Decision
Use Claude Sonnet 4.5 to classify change severity instead of hardcoded if/then rules.

### Rationale
**Evaluated Alternatives**:
1. **Rules engine** (e.g., "required param removed → breaking")
2. **ML classifier** (train on labeled dataset of API changes)
3. **Hybrid** (rules for obvious cases + LLM for edge cases)

**Why LLM Wins**:
- **Context awareness**: Understands domain-specific terminology (e.g., "idempotency key" removal is critical)
- **Reasoning**: Explains *why* a change is breaking, not just *that* it is
- **Edge cases**: Handles ambiguous scenarios (e.g., "default value changed from 10 to 100")
- **No training data**: Rules-based needs exhaustive enumeration, ML needs labeled corpus
- **Natural language input**: Can process changelog prose, not just schema diffs

**Why Not Rules**:
- Maintenance nightmare: 100+ rules for comprehensive coverage
- Brittleness: Fails on unforeseen patterns (e.g., "parameter renamed but functionally identical")
- No explanatory power: Can't tell user *why* it classified as breaking

**Why Not Traditional ML**:
- Insufficient training data: Would need 10K+ labeled API changes
- Poor generalization: Overfits to common APIs (REST), fails on GraphQL/gRPC
- Requires ongoing retraining as API patterns evolve

**Cost Analysis** (Claude Sonnet 4.5):
- Avg diff: 500 tokens input + 200 tokens output
- Cost: $0.001/1K input tokens + $0.003/1K output = $0.0011 per classification
- 2 APIs × 10 changes/day × 30 days = 600 classifications/month = **$0.66/month**

**Tradeoffs**:
- **Latency**: 2-5s per LLM call vs instant rules
- **Non-determinism**: Same diff may get slightly different confidence scores
- **API dependency**: Anthropic outage blocks classification

**Mitigation**:
- Async processing: Don't block on LLM response
- Confidence thresholds: Auto-escalate if confidence <0.8
- Fallback heuristics: If LLM fails, use basic rules (required param removed → breaking)
- Caching: Identical diffs get cached classification (Redis with 7-day TTL)

---

## Why Async Pipeline Instead of Synchronous Processing?

### Decision
Use event-driven architecture with message queues for processing steps instead of sequential execution.

### Rationale
**Evaluated Alternatives**:
1. **Synchronous DAG** (Airflow with sequential tasks)
2. **Batch processing** (cron job that runs all steps in order)
3. **Lambda chaining** (Step Functions for orchestration)

**Why Async Wins**:
- **Parallelism**: Ingest multiple APIs concurrently (20 APIs × 5 sources = 100 parallel fetches)
- **Failure isolation**: Ingestion failure doesn't block normalization of already-fetched data
- **Backpressure handling**: Queue depth indicates system load, can scale workers
- **Retries**: Dead letter queue for transient failures, exponential backoff
- **Observability**: Each message is a trace point for debugging

**Architecture**:
```
Scheduler → [Discovery Queue] → Discovery Workers → [Ingestion Queue] → Ingestion Workers → ...
```

**Tradeoffs**:
- **Complexity**: More moving parts than synchronous script
- **Eventual consistency**: Snapshot may be written before diff completes
- **Debugging**: Harder to trace end-to-end flow across multiple workers

**Mitigation**:
- Correlation IDs for request tracing across queue boundaries
- Health checks on each worker type
- SLA monitoring: Alert if any queue depth >100 for >5 minutes

**Why Not Lambda/Step Functions**:
- Cold start latency unacceptable for LLM calls (2-5s)
- Step Functions cost ($25/million transitions) adds up at scale
- Vendor lock-in to AWS

**Queue Choice**: SQS (AWS) or Pub/Sub (GCP)
- At-least-once delivery semantics (acceptable for idempotent operations)
- Native integration with CloudWatch/Stackdriver
- DLQ support for poison messages

---

## Rejected Approaches

### 1. Real-time API Traffic Monitoring
**Approach**: Instrument client SDKs to detect API changes via runtime behavior.

**Why Rejected**:
- Requires SDK changes (can't do for third-party SDKs)
- Only detects changes *after* production impact
- High operational overhead (log ingestion, anomaly detection)
- Doesn't help with proactive planning

### 2. Blockchain for Immutable Audit Trail
**Approach**: Store API snapshots on blockchain for tamper-proof history.

**Why Rejected**:
- Massive overkill for read-heavy workload
- Write latency (block confirmation) is unacceptable
- Cost is 100x higher than S3
- No threat model requiring cryptographic proof (we control the data)

### 3. Manual Changelog Parsing
**Approach**: Scrape changelog pages, use regex to extract version info.

**Why Rejected**:
- Changelog formats are wildly inconsistent (Markdown, HTML, PDF, video)
- Many APIs don't publish changelogs (e.g., undocumented Twitter API changes)
- Can't detect changes not mentioned in changelog
- Maintenance nightmare (one regex per API)

### 4. Crowd-sourced Change Reporting
**Approach**: Let developers report API changes they encounter.

**Why Rejected**:
- Reactive, not proactive (change already caused incident)
- Low signal-to-noise (duplicate reports, false positives)
- Requires community adoption to be useful
- No standardized change format

---

## Cost Controls

### Phase 1 Budget: $50/month
| Component | Cost | Justification |
|-----------|------|---------------|
| Tavily API | $10/month | 1000 queries × 2 APIs × $0.001/query × 30 days = $60 → use free tier + cache |
| Claude API | $1/month | 600 classifications × $0.0011 = $0.66 |
| S3 storage | $2/month | 60 snapshots × 500KB × $0.023/GB = $0.69, round up for metadata |
| EC2 compute | $15/month | t3.small spot instance (0.5 vCPU, 2GB RAM) running 10 hrs/day |
| SQS | $0.50/month | 10K messages × $0.00000040/request = $0.004, round up |
| CloudWatch | $5/month | Logs + metrics |
| Buffer | $16.50/month | Unexpected overages |

### Cost Optimization Strategies
1. **Use free tiers**: Tavily (1000 queries/day), AWS Free Tier (750 hrs EC2)
2. **Spot instances**: 70% cheaper than on-demand
3. **Snapshot compression**: Gzip reduces storage by 70%
4. **LLM batching**: Group 10 diffs per API call (10x reduction in requests)
5. **Lazy evaluation**: Only run LLM classification if structural diff is non-trivial

### Cost Triggers
- Alert if daily spend >$2 (indicates runaway loop)
- Weekly cost reports to eng-leads channel
- Hard quota: Kill workers if monthly spend >$75

---

## Caching Strategy

### Discovery Cache
- **Key**: `discovery:{api_name}`
- **Value**: Source URLs + Tavily confidence
- **TTL**: 7 days
- **Invalidation**: Manual trigger if source URL becomes 404

### Diff Cache
- **Key**: `diff:{snapshot_hash_1}:{snapshot_hash_2}`
- **Value**: Structural diff JSON
- **TTL**: 90 days (matches snapshot retention)
- **Invalidation**: Never (diffs are immutable for given snapshot pair)

### Classification Cache
- **Key**: `classification:{diff_hash}`
- **Value**: LLM classification result
- **TTL**: 7 days
- **Invalidation**: On LLM prompt version change (forces reclassification)

### Snapshot Metadata Cache
- **Key**: `metadata:{api_name}:latest`
- **Value**: Timestamp + S3 path of most recent snapshot
- **TTL**: 1 hour
- **Invalidation**: On new snapshot write

**Cache Backend**: Redis (ElastiCache in production, local for dev)
- Persistence disabled (cache is non-critical)
- Eviction policy: LRU
- Max memory: 512MB (estimated 10K cache entries × 50KB avg)

---

## Phase 1 Implementation Tradeoffs

### Synchronous vs Async Pipeline

**Decision**: Use async for I/O (fetching), sync for everything else in Phase 1.

**Why**:
- Fetching 5 sources per API is I/O-bound → async gives 5x speedup
- Diff/classification are CPU-bound → async adds complexity without benefit
- LLM calls are sequential (one classification per diff) → no parallelism opportunity

**Code pattern**:
```python
# Async for I/O
async def fetch_all_sources(urls: list[str]) -> list[bytes]:
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_url(session, url) for url in urls]
        return await asyncio.gather(*tasks)

# Sync for processing
def normalize(raw_data: bytes) -> NormalizedAPI:
    # CPU-bound, no benefit from async
    pass
```

---

### Error Handling Philosophy

**Decision**: Fail loud in Phase 1, graceful degradation in Phase 2.

**Why**:
- **Phase 1**: You're debugging, need to see errors immediately
- **Phase 2**: Production system, can't crash on single API failure

**Phase 1 approach**:
```python
def run_pipeline():
    try:
        discovery = discover_sources("stripe")  # raises on failure
        raw = fetch(discovery.urls)  # raises on timeout
        normalized = normalize(raw)  # raises on parse error
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise  # Re-raise, don't swallow
```

**Phase 2 approach**:
```python
def run_pipeline():
    try:
        discovery = discover_sources("stripe")
    except DiscoveryError:
        discovery = load_cached_discovery("stripe")  # Fallback
    
    # Continue even if normalization fails
    try:
        normalized = normalize(raw)
    except NormalizationError as e:
        log_failure(e)
        return  # Skip this API, continue with others
```

---

### Logging Strategy

**Decision**: Structured JSON logs from day 1, even in Phase 1.

**Why**:
- Easy to grep: `cat logs/app.log | jq 'select(.level == "ERROR")'`
- Forwards to CloudWatch/Datadog without schema changes
- Correlation IDs enable request tracing

**Implementation** (`specwatch/utils/logger.py`):
```python
import structlog

logger = structlog.get_logger()

# Usage
logger.info("fetching_source", api="stripe", url=url, correlation_id=req_id)
logger.error("classification_failed", diff=diff, error=str(e), correlation_id=req_id)
```

**Log format**:
```json
{
  "event": "fetching_source",
  "api": "stripe",
  "url": "https://...",
  "correlation_id": "abc-123",
  "timestamp": "2026-01-15T10:00:00Z",
  "level": "info"
}
```

---

### Testing Strategy for Phase 1

**Decision**: Focus on integration tests over unit tests initially.

**Why**:
- **Unit tests** are brittle during rapid iteration (schema changes)
- **Integration tests** verify end-to-end behavior (real value)
- **Time-boxed**: 7 days to working prototype, can't test every edge case

**Test coverage targets**:
- **Week 1**: 0 tests (pure exploration)
- **Week 2**: 1 integration test (end-to-end pipeline)
- **Week 3**: 5 integration tests + critical unit tests (diff logic, normalization)
- **Week 4**: 50% coverage (pytest-cov)

**Example integration test**:
```python
# tests/test_end_to_end.py
def test_stripe_breaking_change_detection():
    # Given: Two snapshots with known breaking change
    old = load_fixture("stripe_2026_01_01.json")
    new = load_fixture("stripe_2026_01_02.json")
    
    # When: Run diff + classification
    diff = compute_diff(old, new)
    classification = classify_change(diff)
    
    # Then: Expect breaking change classification
    assert classification.severity == "breaking"
    assert "required parameter removed" in classification.reasoning
```

---

## Open Questions & Future Decisions

1. **Should we deduplicate identical snapshots?**
   - Pro: Saves storage if API hasn't changed in days
   - Con: Breaks assumption of daily snapshot cadence
   - **Decision**: No for Phase 1, revisit if storage cost >$50/month

2. **How to handle API version branches (v1 vs v2)?**
   - Option A: Track each version separately
   - Option B: Only track latest production version
   - **Decision**: B for Phase 1 (simplicity), A for Phase 2 if needed

3. **Should we expose a public API for query?**
   - Use case: Other teams query "Is Stripe v1/charges endpoint deprecated?"
   - **Decision**: Phase 3 feature, not MVP blocker

4. **How to handle rate-limited APIs?**
   - Respect Retry-After headers, exponential backoff
   - Store rate limit metadata (X-RateLimit-Remaining)
   - **Decision**: Best-effort for Phase 1, formal quota management in Phase 2

5. **Should we version our own normalization schema?**
   - If we improve schema, old snapshots become incompatible
   - **Decision**: Yes—include `schema_version` field, support backward compat for 1 major version
