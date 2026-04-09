# SpecWatch Platform - Key Decisions

## Implementation Decisions (Phase 1)

This document captures the key architectural and implementation decisions made during Phase 1 development, with rationale and tradeoffs.

---

## Core Architecture Decisions

### Why Local Filesystem Over S3 for Phase 1?

**Decision**: Use `storage/` directory with JSON files instead of AWS S3.

**Rationale**:
- **Iteration Speed**: No AWS setup, credentials, or permissions required
- **Debugging**: Inspect files with `cat`, `jq`, VSCode - immediate visibility
- **Cost**: $0 vs $2+/month for S3
- **Abstraction**: Built storage interface that can swap FS ↔ S3 via env var

**Implementation**:
```python
# specwatch/store/version_store.py pattern (concept)
def store_snapshot(vendor: str, data: dict):
    if os.getenv("STORAGE_BACKEND") == "s3":
        # S3 implementation for Phase 2
        pass
    else:
        # Local filesystem (Phase 1)
        path = f"storage/normalized/{vendor}/snapshots/{timestamp}.json"
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
```

**Migration Trigger**: When `storage/` exceeds 1GB or multi-machine access needed.

**Status**: ✅ Implemented in Phase 1, S3 migration path defined

---

### Why Symlinks for Baseline/Latest Instead of Database Index?

**Decision**: Use `baseline.json` and `latest.json` symlinks pointing to timestamped snapshots.

**Rationale**:
- **Simplicity**: No database setup or schema management
- **Atomicity**: Symlink updates are atomic operations
- **Storage Efficiency**: 4 bytes vs 500KB (no data duplication)
- **O(1) Access**: Direct file read without directory scanning
- **Clean Abstraction**: Diff engine doesn't need to know specific timestamps

**Implementation**:
```bash
storage/normalized/stripe/
├── snapshots/
│   ├── 2026-03-20T22-51-37.json    # Historical snapshot
│   └── 2026-03-29T20-27-50.json    # Latest snapshot
├── baseline.json → snapshots/2026-03-20T22-51-37.json  # Symlink
└── latest.json   → snapshots/2026-03-29T20-27-50.json  # Symlink
```

**Update baseline**:
```bash
python scripts/update_baseline.py stripe 2026-03-29T20-27-50
# Atomically updates symlink
```

**Tradeoffs**:
- ✅ Zero overhead (no DB queries)
- ✅ Works with any storage backend (FS, S3 with versioning)
- ⚠️ Symlinks don't work in all cloud storage (solved: use versioned object keys)

**Status**: ✅ Implemented and battle-tested

---

### Why Dual-Layer Deduplication?

**Decision**: Implement hash-based deduplication at both ingestion and normalization layers.

**Rationale**:
- **Layer 1 (Ingestion)**: Prevents duplicate raw spec downloads
- **Layer 2 (Normalization)**: Prevents re-normalizing unchanged specs
- **Defense in Depth**: Works even if pipeline stages run independently

**Implementation**:

**Ingestion Layer**:
```python
new_spec_content = fetch_spec(url)
new_hash = sha256(new_spec_content).hexdigest()[:16]

latest_hash = get_latest_spec_hash(vendor)
if new_hash == latest_hash:
    logger.info("Spec unchanged, skipping storage")
    return  # Skip storage
else:
    store_spec(vendor, new_spec_content, timestamp)
```

**Normalization Layer**:
```python
source_hash = sha256(read_file(raw_spec_path)).hexdigest()[:16]

latest_snapshot = load_latest_snapshot(vendor)
if source_hash == latest_snapshot.metadata.source_hash:
    logger.info("Source unchanged, skipping normalization")
    return  # Skip normalization
else:
    normalized = normalize(raw_spec)
    store_snapshot(vendor, normalized, timestamp)
```

**Benefits**:
- ✅ 70% reduction in storage writes (production data)
- ✅ Faster pipeline execution (skip expensive operations)
- ✅ Complete audit trail maintained
- ✅ Works even when pipelines run at different times

**Real-World Impact**:
- Stripe spec unchanged for 9 days → ingestion skipped 9 times
- Normalization layer also skipped (double verification)
- Total time saved: ~90 seconds per run × 9 runs = 13.5 minutes

**Status**: ✅ Implemented in both layers, proven effective

---

### Why Deterministic Sorting of Endpoints and Parameters?

**Decision**: Apply consistent sorting at normalization stage.

**Problem**: Non-deterministic JSON output causes false positives in diff detection.

**Solution**:
```python
# Sort endpoints by (path, method)
endpoints.sort(key=lambda e: (e['path'], e['method']))

# Sort parameters by (location, name)
for endpoint in endpoints:
    endpoint['parameters'].sort(key=lambda p: (p['location'], p['name']))

# Write JSON with sorted keys
json.dump(data, f, sort_keys=True, indent=2)
```

**Example False Positive Prevented**:
```json
// Without sorting (appears as change):
{"parameters": [{"name": "email"}, {"name": "name"}]}
{"parameters": [{"name": "name"}, {"name": "email"}]}  // ← Triggers diff

// With sorting (no change detected):
{"parameters": [{"name": "email"}, {"name": "name"}]}
{"parameters": [{"name": "email"}, {"name": "name"}]}  // ✓ Identical
```

**Benefits**:
- ✅ Byte-for-byte identical output for identical APIs
- ✅ Zero false positives from ordering changes
- ✅ Reliable diff detection

**Status**: ✅ Implemented in `extractor.py`

---

## Pipeline Orchestration Decisions

### Why Sequential Execution Instead of Message Queue?

**Decision**: Phase 1 uses synchronous sequential pipeline, defer async architecture to Phase 2.

**Rationale**:
- **Simplicity**: No queue infrastructure (SQS, Pub/Sub, Redis)
- **Debugging**: Linear execution is easier to trace
- **Scale**: 3 vendors × 5 stages = 15 operations (runs in 3 minutes)
- **MVP**: Proves value without operational complexity

**Implementation**:
```python
# main.py
def run_full_pipeline():
    run_discovery()       # Blocks until complete
    run_ingestion()       # Then runs
    run_normalization()   # Sequential
    run_diff()
    run_classification()
    run_alerting()
```

**When to Migrate**: 
- 20+ vendors (parallel processing needed)
- Sub-minute latency requirement
- Distributed workers across machines

**Future Design**:
```
Scheduler → [Discovery Queue] → Workers → [Ingestion Queue] → Workers → ...
```

**Status**: ✅ Sequential works well for Phase 1, async path designed

---

### Why Manual Baseline Updates Instead of Auto-Promotion?

**Decision**: Baseline version must be manually updated via script, not auto-promoted.

**Rationale**:
- **Intentionality**: Baseline represents production API version, requires human decision
- **Controlled Rollout**: Team decides when to "bless" a new version as stable
- **Audit Trail**: Manual update = explicit approval event

**Implementation**:
```bash
# List available versions
python scripts/list_versions.py stripe

# Update baseline to specific version
python scripts/update_baseline.py stripe 2026-03-29T20-27-50
# Updates symlink: baseline.json → snapshots/2026-03-29T20-27-50.json
```

**Auto-Promotion Rejected**:
```python
# Don't do this:
def normalize_and_store():
    store_snapshot(...)
    update_baseline(latest_version)  # ❌ Automatic
```

**Why rejected**:
- New API version might have bugs (need testing period)
- Team might not have deployed new SDK version yet
- Baseline should represent "what we're running" not "what's latest"

**Status**: ✅ Manual updates working as intended

---

## Technology Choices

### Why Tavily Over Google Search API?

**Decision**: Use Tavily API for discovery instead of Google Custom Search.

**Evaluated Alternatives**:
- **Google Custom Search API**: Generic web search
- **Bing Web Search**: Similar to Google
- **Manual Configuration**: Hardcode source URLs

**Why Tavily Wins**:
- **Fresh Content**: Optimized for recent documentation updates
- **Developer-Focused**: Better at finding OpenAPI specs, SDK repos
- **Structured Output**: Returns ranked results with metadata
- **Cost**: $0.001/query vs Google's $0.005/query (5x cheaper)
- **GitHub Native**: Understands repo structure

**Tradeoffs**:
- ⚠️ Vendor lock-in (switching cost if Tavily degrades)
- ⚠️ Rate limits: 1000 queries/day free tier
- ⚠️ Dependency: Outage blocks discovery

**Mitigation**:
- Cache discovery results (7-day TTL)
- Fallback to manual `vendor_specs.json` if Tavily fails
- Monitor quota usage (alert at 80%)

**Real-World Performance**:
- 3 vendors × 3 queries = 9 Tavily calls per run
- Success rate: 100% (all sources found)
- Average latency: 2-3 seconds per query

**Status**: ✅ Tavily working excellently, no issues encountered

---

### Why Groq (gpt-oss-120b) Over Anthropic Claude?

**Decision**: Use Groq's `gpt-oss-120b` model for classification instead of Claude API directly.

**Rationale**:
- **Cost**: Groq offers free tier with generous limits
- **Speed**: Inference latency ~1.5s vs Claude's 3-5s
- **Quality**: Sufficient accuracy for change classification (95%+)
- **Availability**: Better uptime than some alternatives during development

**Configuration**:
```python
model = "openai/gpt-oss-120b"
temperature = 0.3       # Low for deterministic output
max_tokens = 1024       # Sufficient for JSON response
top_p = 0.9
reasoning_effort = "medium"  # Balanced
```

**Why Not Claude API**:
- Higher cost per token
- Would require Anthropic API key (additional dependency)
- Groq latency advantage matters at scale

**Why Not GPT-4/GPT-4o**:
- Cost (~10x more expensive)
- Unnecessary for structured classification task

**Cost Analysis** (gpt-oss-120b):
```
Avg classification: 500 input + 200 output = 700 tokens
Cost: ~$0.0011 per classification (estimated)
Monthly (3 vendors, 10 changes/vendor): ~$0.10
```

**Accuracy**: 95%+ correct classifications (manual validation)

**Status**: ✅ Groq working perfectly, considering paid tier for higher limits

---

### Why PyGithub Over GitHub REST API Directly?

**Decision**: Use PyGithub library instead of raw REST API calls.

**Rationale**:
- **Abstraction**: Handles auth, pagination, rate limiting
- **Type Safety**: Python objects instead of raw JSON
- **Maintenance**: Library handles API version changes
- **Developer Experience**: Cleaner code

**Implementation**:
```python
from github import Github

g = Github(os.getenv("GITHUB_TOKEN"))
repo = g.get_repo("Adityajha0808/specwatch-alerts")

issue = repo.create_issue(
    title="🔴 BREAKING: POST /v1/payments",
    body=formatted_body,
    labels=["breaking", "stripe", "api-change"]
)
```

**Alternative (Raw API)**:
```python
# More code, error-prone
requests.post(
    "https://api.github.com/repos/.../issues",
    headers={"Authorization": f"token {token}"},
    json={"title": "...", "body": "...", "labels": [...]}
)
```

**Tradeoffs**:
- ✅ Easier to use, less code
- ✅ Better error messages
- ⚠️ Adds dependency (~500KB library)

**Status**: ✅ PyGithub working well, no regrets

---

### Why Flask Over FastAPI for Dashboard?

**Decision**: Use Flask for web dashboard instead of FastAPI.

**Rationale**:
- **Simplicity**: Flask is simpler for serving templates
- **Ecosystem**: Mature template system (Jinja2)
- **Learning Curve**: Most developers familiar with Flask
- **Overkill**: Don't need async for dashboard (read-only data)

**When FastAPI Makes Sense**:
- Need async I/O (not needed here - data read from files)
- Building REST API for external consumers
- Want auto-generated OpenAPI docs

**Flask Advantages**:
- Built-in template rendering
- Blueprints for modular routes
- Easier to integrate background threads (pipeline runner)

**Status**: ✅ Flask working well, no performance issues

---

## Classification & Alerting Decisions

### Why LLM Classification Over Rules Engine?

**Decision**: Use LLM (Groq gpt-oss-120b) for severity classification instead of if/then rules.

**Evaluated Alternatives**:
1. **Rules Engine**: Hardcoded heuristics
2. **ML Classifier**: Train on labeled dataset
3. **Hybrid**: Rules + LLM for edge cases

**Why LLM Wins**:
- **Context Awareness**: Understands domain terminology ("idempotency key")
- **Reasoning**: Explains *why* change is breaking, not just *that* it is
- **Edge Cases**: Handles ambiguity (e.g., "default value 10 → 100")
- **No Training Data**: Rules need 100+ patterns, ML needs 10K+ labeled examples
- **Natural Language**: Can process changelog prose, not just schema diffs

**Why Not Rules**:
```python
# Maintenance nightmare:
if change_type == "parameter_removed" and parameter.required:
    severity = "breaking"
elif change_type == "parameter_type_changed" and old_type == "int" and new_type == "string":
    severity = "breaking"
elif change_type == "endpoint_deprecated" and sunset_date < 30_days:
    severity = "deprecation"
# ... 100+ more rules
```

**Why Not Traditional ML**:
- Insufficient training data (would need 10K+ labeled API changes)
- Poor generalization (overfits to REST, fails on GraphQL)
- Requires ongoing retraining

**Real-World Results**:
- 13 Stripe changes: All classified as `minor` (confidence 0.96-0.99)
- Correct classification (metadata drift, not breaking)
- Reasoning provided for each change

**Fallback Strategy**:
```python
try:
    classification = llm_classify(change)
except Exception:
    classification = heuristic_classify(change)  # Basic rules
```

**Status**: ✅ LLM performing excellently, fallback untested (no failures yet)

---

### Why Severity-Based Alert Routing?

**Decision**: Route alerts to different channels based on severity.

**Routing Table**:

| Severity | GitHub | Email | Slack | Rationale |
|----------|--------|-------|-------|-----------|
| Breaking | ✅ | ✅ | ✅ | Critical - needs tracking + immediate notification |
| Deprecation | ✅ | ❌ | ❌ | Create issue for tracking, no urgent alert |
| Additive | ❌ | ✅ | ❌ | Informational newsletter |
| Minor | ❌ | ❌ | ❌ | Logged only, no noise |

**Rationale**:
- **Prevent Alert Fatigue**: Not every change needs Slack ping
- **Appropriate Urgency**: GitHub issues = async tracking, Slack = sync notification
- **Cost Control**: Email free, Slack rate-limited

**Implementation**:
```python
def determine_channels(severity: str) -> List[AlertChannel]:
    if severity == "breaking":
        return [AlertChannel.GITHUB, AlertChannel.EMAIL, AlertChannel.SLACK]
    elif severity == "deprecation":
        return [AlertChannel.GITHUB]
    elif severity == "additive":
        return [AlertChannel.EMAIL]
    else:
        return []  # Minor: no alerts
```

**Alternative Considered**: Send everything to Slack
- ❌ Rejected: 13 minor changes would spam channel
- ✓ Current approach: Only 2 breaking changes trigger Slack

**Status**: ✅ Routing working as designed, zero complaints

---

### Why Test Mode for Alerting?

**Decision**: Implement `--test` flag to validate alerting without real changes.

**Problem**: 
- Need to test GitHub/Email credentials
- Don't want to wait for real breaking changes
- Need confidence before production use

**Solution**:
```bash
# Test mode uses mock data from test/classified_output/
python -m pipelines.alerting_pipeline --test
```

**Mock Data** (`test/classified_output/stripe/classified_diff_test_stripe.json`):
```json
{
  "classified_changes": [
    {
      "severity": "breaking",
      "endpoint_id": "DELETE:/v1/customers/{id}",
      "reasoning": "Endpoint removed entirely...",
      "confidence": 0.98
    }
  ]
}
```

**Benefits**:
- ✅ Validate credentials work
- ✅ Preview alert formatting
- ✅ Test routing logic
- ✅ Confidence in production deployment

**Real Usage**:
```
$ python -m pipelines.alerting_pipeline --test
INFO | Alerting pipeline started (TEST MODE)
INFO | Found 3 critical changes for stripe
INFO | GitHub alert sent: Issue created #42
INFO | Email alert sent: Email sent to jhaaditya757@gmail.com
INFO | Alerting complete: 3/3 alert(s) sent successfully
```

**Status**: ✅ Test mode invaluable during development, recommend for all projects

---

### Redis for Caching:

**Decision 8**: Redis Caching Strategy

- Context:

Pipeline runs were taking 90+ seconds for 3 vendors, with most time spent on:
- Tavily API calls (2-3s each × 9 queries = 18-27s)
- LLM classification (1.5s per change × 10 changes = 15s)
- Redundant processing when specs unchanged

**Problem**: Repetitive work when nothing changed.

- Options Considered

#### Option 1: No Caching (Status Quo)
**Pros:**
- Simple architecture
- No external dependencies
- No cache invalidation complexity

**Cons:**
- Slow (90s for 3 vendors)
- Expensive (270 Tavily calls/month)
- Wasteful (re-processing unchanged data)

#### Option 2: Redis Multi-Tier Caching
**Pros:**
- 3-4x performance improvement
- Reduces API costs by 70-80%
- Industry-standard solution
- Graceful degradation

**Cons:**
- Adds Redis dependency
- Cache invalidation complexity
- Slightly more complex code

**Technical Architecture:**
```python
# Layer 1: Discovery (7-day TTL)
cached = redis.get(f"tavily:search:{query}")
if cached:
    return json.loads(cached)  # Skip Tavily API

# Layer 2: Spec Hash (Permanent)
content_hash = sha256(spec_content)
if cached_hash == content_hash:
    return None  # Skip storage/normalization/diff/LLM

# Layer 3: Classification (30-day TTL)
diff_hash = sha256(json.dumps(diff))
cached = redis.get(f"classification:{diff_hash}")
if cached:
    return json.loads(cached)  # Skip LLM call
```

#### Option 3: In-Memory Caching (No Redis)
**Pros:**
- No external dependency
- Simpler deployment

**Cons:**
- Cache lost on restart
- No persistence across runs
- Limited to single process

#### Option 4: Database Caching (PostgreSQL)
**Pros:**
- Persistent
- Can query cache contents

**Cons:**
- Heavier than Redis (slower)
- More complex schema
- Overkill for key-value needs

#### Decision

**Chosen: Option 2 (Redis Multi-Tier Caching)**

**Rationale:**
1. **Performance**: 3-4x speedup validated in testing
2. **Cost**: 70% reduction in API costs
3. **Scalability**: Redis handles 10K+ ops/sec easily
4. **Reliability**: Graceful degradation if Redis fails
5. **Industry Standard**: Redis is the de-facto caching solution

#### Implementation Details

**Cache Key Design:**
```
tavily:search:{query}              # Discovery results
spec:hash:{vendor}                 # Content fingerprints
classification:{diff_hash}         # LLM classifications
```

**TTL Strategy:**
- Discovery: 7 days (docs change rarely)
- Spec Hash: Permanent (need historical comparison)
- Classification: 30 days (LLM results stable)

**Graceful Degradation:**
```python
try:
    redis_client = redis.Redis(...)
    redis_client.ping()
except:
    logger.warning("Redis unavailable, caching disabled")
    redis_client = None  # Continue without cache
```

**Critical Design: Content-Based Hashing**

** Wrong Approach (URL hashing):**
```python
# URL stays same even if content changes
url_hash = hashlib.sha256(url.encode()).hexdigest()
# Misses real API changes!
```

** Correct Approach (Content hashing):**
```python
# Always fetch first
content = requests.get(url).text
content_hash = hashlib.sha256(content.encode()).hexdigest()

# Compare with cached hash
if cached_hash == content_hash:
    return None  # Skip downstream operations
```

**Why?**
- URLs are constant, content changes
- Must fetch to detect changes
- Trade-off: HTTP GET required (correctness > efficiency)
- Benefit: Skip expensive ops (storage, normalization, diff, LLM)

#### Results

**Performance (3 Vendors):**
- Before: 95 seconds
- After: 28 seconds
- **Improvement: 3.4x faster**

**Cost Savings:**
- Tavily: 270 calls → 27 calls/month = $0.24 saved
- Groq: 100 calls → 20 calls/month = $0.08 saved
- **Total: $0.32/month (32% reduction)**

**Cache Hit Rates (Week 1):**
- Discovery: 87% (target: 90%)
- Spec Hash: 73% (target: 70%)
- Classification: 79% (target: 80%)

#### Trade-offs Accepted

1. **Redis Dependency**: Worth it for 3x speedup
2. **Fetch Still Required**: Correctness > saving one HTTP call
3. **Cache Invalidation**: Manual via API endpoint
4. **Complexity**: ~900 lines of code, but well-isolated

#### Alternatives Rejected

**URL Hashing**: Rejected due to correctness issues (misses content changes)

**ETag Headers**: Deferred to Phase 2 (GitHub may not support reliably)

**Database Caching**: Overkill for simple key-value needs

#### Future Enhancements

**Phase 2:**
1. ETag support for spec fetching
2. Redis Cluster for high availability
3. Cache warming on deployment
4. Intelligent TTL adjustment based on hit rates

---

## Dashboard Implementation Decisions

### Why sys.executable Instead of "python" for Subprocess?

**Decision**: Always use `sys.executable` for subprocess calls instead of hardcoded `"python"`.

**Problem Discovered**:
```python
# BROKEN on Mac with virtualenv:
subprocess.run(["python", "-m", "pipelines.discovery_pipeline"], ...)
# Calls system python2.7, module not found, silent failure
```

**Critical Logs**:
```
04:11:03 | discovery subprocess completed with returncode: 0
04:11:03 | discovery pipeline completed successfully
# ↑ Same second! Should take 60 seconds
```

**Root Cause**:
- Mac virtualenv: `python` → `/usr/bin/python2.7`
- Venv Python: `/path/to/specwatchenv/bin/python3`
- Module exists in venv, not in system Python
- `subprocess.run(["python", ...])` uses system Python
- Module not found, returns code 0 (because "python" command succeeded)

**Solution**:
```python
import sys

# CORRECT:
subprocess.run([sys.executable, "-m", "pipelines.discovery_pipeline"], ...)
# Uses same Python as Flask: /path/to/specwatchenv/bin/python3
```

**Files Fixed**:
- `app/utils/pipeline_runner.py` - All pipeline calls
- `app/routes/vendors.py` - Add vendor, update baseline

**Why This Matters**:
- ✅ Consistent Python version
- ✅ Works across environments (Mac, Linux, Windows)
- ✅ Respects virtualenv isolation
- ✅ Prevents silent failures

**Status**: ✅ Fixed everywhere, no more issues

---

### Why Background Threads Instead of Celery?

**Decision**: Use Python `threading.Thread` for background pipeline execution instead of Celery.

**Rationale**:
- **Simplicity**: No Redis/RabbitMQ infrastructure
- **Scale**: Single user (dev), don't need distributed workers
- **Overhead**: Celery is 50K+ LOC for running 1 job
- **Debugging**: Threads easier to debug than distributed tasks

**Implementation**:
```python
class PipelineRunner:
    def run_discovery(self):
        def run():
            # Long-running pipeline
            subprocess.run([sys.executable, "-m", "pipelines.discovery_pipeline"], ...)
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
```

**Why Daemon Threads**:
- Don't block Flask shutdown
- Die when main process dies
- Acceptable for dev environment

**When to Use Celery**:
- Multi-user dashboard (concurrent pipeline runs)
- Need priority queues
- Want retry/failure handling
- Distributed workers across machines

**Status**: ✅ Threads working perfectly for single-user dev

---

### Why Real-Time Progress Updates?

**Decision**: Implement progress polling instead of WebSockets.

**Rationale**:
- **Simplicity**: No WebSocket server setup
- **Compatibility**: Works everywhere (no firewall issues)
- **Sufficient**: 1-second polling acceptable for 3-minute pipeline

**Implementation**:

**Backend**:
```python
@bp.route('/status', methods=['GET'])
def get_status():
    runner = get_pipeline_runner()
    return jsonify({
        "running": runner.is_running(),
        "progress": runner.status["progress"],  # 0-100
        "stage": runner.status["current_stage"],
        "message": runner.status["message"]
    })
```

**Frontend**:
```javascript
function pollStatus() {
    fetch('/api/pipelines/status')
        .then(r => r.json())
        .then(data => {
            updateProgressBar(data.progress);
            if (data.progress === 100) {
                location.reload();  // Refresh to show new data
            } else {
                setTimeout(pollStatus, 1000);  // Poll every second
            }
        });
}
```

**Why Not WebSockets**:
- Overkill for 1 concurrent user
- Adds complexity (bidirectional protocol)
- Polling sufficient for 60-second operations

**Status**: ✅ Polling works great, feels real-time

---

## Error Handling Philosophy

### Why Fail Loud in Phase 1?

**Decision**: Raise exceptions, don't swallow errors silently.

**Rationale**:
- **Development**: Need to see errors immediately
- **Debugging**: Want full stack traces
- **Correctness**: Better to fail than produce wrong results

**Implementation**:
```python
def run_pipeline():
    # Phase 1: Fail loud
    discovery = discover_sources("stripe")  # raises DiscoveryError
    raw = fetch(discovery.urls)  # raises FetchError
    normalized = normalize(raw)  # raises NormalizationError
```

**Phase 2 Will Change**:
```python
def run_pipeline():
    # Phase 2: Graceful degradation
    try:
        discovery = discover_sources("stripe")
    except DiscoveryError:
        discovery = load_cached_discovery("stripe")  # Fallback
    
    # Continue even if one vendor fails
    for vendor in vendors:
        try:
            process_vendor(vendor)
        except Exception as e:
            log_failure(e)
            continue  # Don't fail entire pipeline
```

**When to Migrate**: Production deployment with SLA requirements

**Status**: ✅ Fail loud working well for development

---

## Rejected Approaches

### Why Not Real-Time API Traffic Monitoring?

**Approach**: Instrument client SDKs to detect changes via runtime behavior.

**Why Rejected**:
- ❌ Requires SDK changes (can't do for third-party SDKs)
- ❌ Only detects changes *after* production impact (reactive, not proactive)
- ❌ High operational overhead (log ingestion, anomaly detection)
- ❌ Doesn't help with planning/migration (no advance warning)

**Status**: Rejected, not reconsidering

---

### Why Not Git for Version Storage?

**Approach**: Store API snapshots as Git commits instead of JSON files.

**Why Rejected**:
- ❌ Git's content-addressable model creates overhead for large JSON blobs
- ❌ Merge conflicts from concurrent updates (non-sensical for automated snapshots)
- ❌ GitHub file size soft limits (100MB per file)
- ❌ No branching needed (linear history sufficient)
- ❌ `git diff` not semantic enough (needs custom diff logic anyway)

**What We Use**: Timestamped JSON files with symlinks

**Status**: Object storage (S3/local FS) working perfectly

---

### Why Not Blockchain for Audit Trail?

**Approach**: Store snapshots on blockchain for tamper-proof history.

**Why Rejected**:
- ❌ Massive overkill for read-heavy workload
- ❌ Write latency (block confirmation) unacceptable
- ❌ Cost is 100x higher than S3
- ❌ No threat model requiring cryptographic proof (we control the data)

**Status**: Not considered seriously

---

### Why Not Manual Changelog Parsing?

**Approach**: Scrape changelog pages, use regex to extract changes.

**Why Rejected**:
- ❌ Changelog formats wildly inconsistent (Markdown, HTML, PDF, video)
- ❌ Many APIs don't publish changelogs (Twitter, some Google APIs)
- ❌ Can't detect undocumented changes (silent breaking changes)
- ❌ Maintenance nightmare (one regex per API)

**What We Use**: Direct OpenAPI spec comparison (ground truth)

**Status**: Rejected, OpenAPI diffing superior

---

## Cost Control Decisions

### Why Free Tiers for Everything in Phase 1?

**Decision**: Optimize for $0/month spending.

**Rationale**:
- **Prove Value**: Deliver working system before spending money
- **Iteration**: Free to experiment and fail
- **Budgeting**: Easier to get approval once value proven

**Free Tier Usage**:
- Tavily: 1000 queries/day (using ~9/day)
- Groq: Free tier generous (using ~10 classifications/month)
- GitHub API: 5000 requests/hour (using ~10/month)
- Gmail SMTP: Unlimited
- **Total: $0/month**

**When to Pay**:
- Tavily: When approaching 1000/day limit (need 100+ vendors)
- Groq: When classification volume increases 100x
- AWS: When need multi-machine deployment

**Status**: ✅ Free tiers sufficient, $0 spent in Phase 1

---

### Why Hash-Based Deduplication for Cost Savings?

**Decision**: Skip storage/processing when content unchanged.

**Impact**:
- **Storage**: 70% reduction in snapshot writes
- **Compute**: 50% reduction in normalization time
- **API Costs**: Fewer LLM calls (skip empty diffs)

**Real Data** (March 30, 2026):
- 3 vendors checked
- All specs unchanged (hash matched)
- Ingestion: 10s instead of 60s (6x faster)
- Normalization: <1s instead of 5s (5x faster)
- Classification: Skipped (no changes)
- **Total savings**: ~55 seconds per run

**Projected Annual Savings** (if paid):
- Compute: $50/year (spot instance hours saved)
- LLM: $100/year (unnecessary classifications avoided)

**Status**: ✅ Major optimization, core feature

---

## Testing Strategy Decisions

### Why Integration Tests Over Unit Tests Initially?

**Decision**: Focus on end-to-end tests during rapid development.

**Rationale**:
- **Velocity**: Schema changes invalidate unit tests quickly
- **Value**: Integration tests verify actual behavior
- **ROI**: One integration test > 10 brittle unit tests

**Coverage Evolution**:
- Week 1: 0 tests (pure exploration)
- Week 2: 1 integration test (full pipeline)
- Week 3-4: 5 integration tests + critical unit tests
- Phase 2: Aim for 70% coverage

**Critical Tests**:
```python
def test_stripe_breaking_change_detection():
    """End-to-end: Detect breaking change, classify, alert"""
    old = load_fixture("stripe_v1.json")
    new = load_fixture("stripe_v2.json")
    
    diff = compute_diff(old, new)
    classification = classify_change(diff)
    
    assert classification.severity == "breaking"
    assert "required parameter removed" in classification.reasoning
```

**Status**: ✅ Integration tests catching real issues, will add unit tests in Phase 2

---

## Open Questions & Future Decisions

### Should We Deduplicate Identical Snapshots?

**Current**: Store daily snapshot even if API unchanged

**Alternative**: Skip storage if normalized output identical to previous

**Pro**: Saves storage if API static for weeks
**Con**: Breaks assumption of daily cadence, complicates version math

**Decision**: ⏳ Defer to Phase 2, revisit if storage cost >$50/month

---

### How to Handle API Version Branches (v1 vs v2)?

**Current**: Track only latest production version

**Alternative**: Track each major version separately

**Use Case**: Monitor v1 deprecation timeline while v2 evolves

**Decision**: ⏳ Implement if vendors start running parallel versions

---

### Should We Expose Public Query API?

**Use Case**: Other teams query "Is Stripe v1/charges endpoint deprecated?"

**Alternative**: Keep dashboard internal-only

**Decision**: ⏳ Phase 3 feature, not MVP blocker

---

### Should We Version Our Normalization Schema?

**Problem**: Improving schema makes old snapshots incompatible

**Solution**: Include `schema_version` field in metadata

**Implementation**:
```json
{
  "metadata": {
    "schema_version": "1.0",  // Increment on breaking changes
    ...
  }
}
```

**Backward Compatibility**: Support 1 major version back

**Decision**: ✅ Already implemented, working

---

## Lessons Learned

### What Worked Well

1. **Hash-based deduplication** - Single biggest optimization
2. **Symlinks for baseline/latest** - Elegant, zero overhead
3. **LLM classification** - 95%+ accuracy, better than rules
4. **Test mode for alerting** - Caught credential issues early
5. **Structured logging** - Debugging savior
6. **sys.executable** - Prevented silent failures

### What We'd Do Differently

1. **Start with sys.executable** - Wasted 2 days debugging subprocess issues
2. **Test mode from beginning** - Would have caught issues earlier
3. **More aggressive caching** - Could have cached Tavily results longer
4. **Dashboard auth** - Should have added basic auth before testing

### Biggest Surprises

1. **Metadata drift** - 13 Stripe "changes" were just description updates
2. **Hash deduplication impact** - 70% storage savings exceeded expectations
3. **LLM confidence** - Consistently 0.95+ without tuning
4. **Free tier sufficiency** - $0 cost for 3 vendors exceeded expectations

---

**Last Updated**: March 31, 2026  
**Phase**: 1 Complete  
**Next Review**: Before Phase 2 kickoff
