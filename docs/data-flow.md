# SpecWatch - Data Flow Documentation

## Overview

This document traces how data moves through SpecWatch from initial discovery to final alert delivery, showing transformations, storage points, and data formats at each stage.

---

## Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ INPUT: Vendor Configuration                                     │
│ - vendors.json: ["stripe", "openai", "twilio"]                  │
│ - vendor_registry.json: {trusted_domains}                       │
│ - discovery_queries.json: {search_templates}                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 1: DISCOVERY (Tavily Search)                              │
│                                                                  │
│ INPUT:  vendor_name="stripe"                                    │
│ QUERY:  "Stripe API documentation"                              │
│         "Stripe OpenAPI specification GitHub"                   │
│         "Stripe API changelog"                                  │
│                                                                  │
│ PROCESS: Tavily API → JSON results → URL validation             │
│                                                                  │
│ OUTPUT: {                                                        │
│   "vendor": "stripe",                                            │
│   "sources": {                                                   │
│     "docs": "https://docs.stripe.com/apis",                     │
│     "openapi": "https://github.com/stripe/openapi",             │
│     "changelog": "https://docs.stripe.com/changelog"            │
│   },                                                             │
│   "discovered_at": "2026-03-29T20:27:50Z"                       │
│ }                                                                │
│                                                                  │
│ STORAGE:                                                         │
│ ├─ storage/raw/raw_discovery/stripe_20260329_221607.json       │
│ └─ storage/discovery/stripe.json (latest)                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 2: INGESTION (Spec Fetching)                              │
│                                                                  │
│ INPUT:  openapi_url="https://github.com/stripe/openapi"        │
│                                                                  │
│ PROCESS:                                                         │
│ 1. Resolve GitHub URL → raw spec URL                            │
│    Try: /openapi.yaml, /openapi/spec3.yaml, etc.               │
│ 2. HTTP GET with retry logic                                    │
│ 3. Compute SHA-256 hash: hash(content)[:16]                     │
│ 4. Compare with latest stored spec hash                         │
│ 5. If hash matches → SKIP STORAGE (deduplication)               │
│    If hash differs → STORE NEW VERSION                          │
│                                                                  │
│ HASH EXAMPLE:                                                    │
│ Content: 2.5MB YAML file                                        │
│ Hash:    26ec724b943e9c39                                       │
│                                                                  │
│ OUTPUT: Raw OpenAPI spec (YAML/JSON)                             │
│                                                                  │
│ STORAGE:                                                         │
│ └─ storage/raw/raw_specs/stripe_openapi_2026-03-29T20-27-40.yaml│
│                                                                  │
│ DEDUPLICATION LOG:                                               │
│ "Spec unchanged for stripe, skipping storage" (if hash matches) │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 3: NORMALIZATION (Schema Standardization)                 │
│                                                                  │
│ INPUT:  Raw OpenAPI spec (YAML/JSON, 2.5MB)                     │
│                                                                  │
│ PROCESS:                                                         │
│ 1. Compute source file hash: hash(raw_spec)[:16]                │
│ 2. Load latest snapshot's source_hash from metadata             │
│ 3. If source_hash matches → SKIP NORMALIZATION                  │
│ 4. If source_hash differs → NORMALIZE:                          │
│    a. Parse YAML/JSON (detect format)                           │
│    b. Extract base_url from servers[0].url                      │
│    c. For each path+method in spec.paths:                       │
│       - Generate endpoint_id: "{METHOD}:{path}"                 │
│       - Extract parameters (path/query/header/body)             │
│       - Extract response codes                                  │
│       - Detect deprecated flag                                  │
│    d. Sort endpoints by (path, method)                          │
│    e. Sort parameters by (location, name)                       │
│    f. Build canonical JSON structure                            │
│                                                                  │
│ TRANSFORMATION:                                                  │
│ 2.5MB OpenAPI YAML → 500KB canonical JSON (~80% reduction)      │
│                                                                  │
│ OUTPUT: {                                                        │
│   "metadata": {                                                  │
│     "vendor": "stripe",                                          │
│     "normalized_at": "2026-03-29T20:27:50Z",                    │
│     "source_hash": "26ec724b943e9c39",                          │
│     "schema_version": "1.0"                                     │
│   },                                                             │
│   "base_url": "https://api.stripe.com",                         │
│   "endpoints": [                                                 │
│     {                                                            │
│       "id": "POST:/v1/customers",                               │
│       "path": "/v1/customers",                                  │
│       "method": "POST",                                          │
│       "deprecated": false,                                       │
│       "auth_required": true,                                     │
│       "parameters": [...]                                        │
│     }                                                            │
│   ]                                                              │
│ }                                                                │
│                                                                  │
│ STORAGE:                                                         │
│ ├─ storage/normalized/stripe/snapshots/2026-03-29T20-27-50.json│
│ ├─ storage/normalized/stripe/baseline.json → snapshots/...      │
│ └─ storage/normalized/stripe/latest.json → snapshots/...        │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 4: DIFF COMPUTATION (Change Detection)                    │
│                                                                  │
│ INPUT:                                                           │
│ - baseline.json (Production version: 2026-03-20)                │
│ - latest.json   (New version: 2026-03-29)                       │
│                                                                  │
│ PROCESS:                                                         │
│ 1. Load both snapshots                                          │
│ 2. Build endpoint maps:                                         │
│    baseline_endpoints = {id: endpoint_data}                     │
│    latest_endpoints = {id: endpoint_data}                       │
│ 3. Set operations:                                              │
│    added = latest_ids - baseline_ids                            │
│    removed = baseline_ids - latest_ids                          │
│    common = baseline_ids ∩ latest_ids                           │
│ 4. For common endpoints:                                        │
│    - Compare deprecated flag                                    │
│    - Compare auth_required                                      │
│    - Compare responses array                                    │
│    - Build parameter maps: {(location,name): param}             │
│    - Detect parameter changes (added/removed/type/required)     │
│                                                                  │
│ ALGORITHM EXAMPLE:                                               │
│ Stripe: 450 endpoints                                           │
│ - Added: 0                                                       │
│ - Removed: 0                                                     │
│ - Common: 450 → deep compare                                    │
│   - 13 endpoints with field_changes=1                           │
│   - All in /v2/core/accounts/* path                             │
│                                                                  │
│ OUTPUT: {                                                        │
│   "vendor": "stripe",                                            │
│   "baseline_version": "2026-03-20T22:51:37Z",                   │
│   "latest_version": "2026-03-29T20:27:50Z",                     │
│   "has_changes": true,                                           │
│   "summary": {                                                   │
│     "endpoints_modified": 13,                                   │
│     "field_changes": 13,                                         │
│     "param_changes": 0                                           │
│   },                                                             │
│   "endpoint_changes": [                                          │
│     {                                                            │
│       "change_type": "endpoint_modified",                       │
│       "endpoint_id": "GET:/v2/core/accounts",                   │
│       "field_changes": [                                         │
│         {"field": "summary", "old": "...", "new": "..."}        │
│       ]                                                          │
│     }                                                            │
│   ]                                                              │
│ }                                                                │
│                                                                  │
│ STORAGE:                                                         │
│ └─ storage/diffs/stripe/diff_2026-03-20_to_2026-03-29.json     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 5: CLASSIFICATION (LLM Analysis)                          │
│                                                                  │
│ INPUT:  Diff result (13 changes)                                │
│                                                                  │
│ PROCESS:                                                         │
│ 1. Check if has_changes == false                                │
│    → If true: skip LLM, create empty classification             │
│ 2. For each change in endpoint_changes:                         │
│    a. Build prompt with context:                                │
│       - Vendor name                                              │
│       - Endpoint details (method, path)                         │
│       - Change type (modified/added/removed)                    │
│       - Specific field changes                                  │
│       - Related changes in same diff                            │
│    b. Call Groq API (gpt-oss-120b):                             │
│       - Temperature: 0.3                                         │
│       - Max tokens: 1024                                         │
│       - Reasoning effort: medium                                │
│    c. Parse JSON response:                                      │
│       {                                                          │
│         "severity": "minor|additive|deprecation|breaking",      │
│         "confidence": 0.98,                                      │
│         "reasoning": "Summary updated for clarity...",          │
│         "migration_path": null,                                 │
│         "impact": "low"                                          │
│       }                                                          │
│ 3. Aggregate statistics                                         │
│                                                                  │
│ TIMING:                                                          │
│ - Per change: ~1.5 seconds (LLM latency)                        │
│ - 13 changes: ~20 seconds total                                 │
│                                                                  │
│ FALLBACK: If LLM fails → heuristic classification:              │
│ - endpoint_removed → breaking (conf=0.95)                       │
│ - parameter_type_changed → breaking (conf=0.85)                 │
│ - endpoint_deprecated → deprecation (conf=0.9)                  │
│                                                                  │
│ OUTPUT: {                                                        │
│   "vendor": "stripe",                                            │
│   "has_breaking_changes": false,                                │
│   "has_deprecations": false,                                    │
│   "classification_summary": {                                    │
│     "total_changes": 13,                                         │
│     "breaking_changes": 0,                                       │
│     "deprecations": 0,                                           │
│     "minor_changes": 13                                          │
│   },                                                             │
│   "classified_changes": [                                        │
│     {                                                            │
│       "endpoint_id": "GET:/v2/core/accounts",                   │
│       "severity": "minor",                                       │
│       "confidence": 0.98,                                        │
│       "reasoning": "Summary text updated..."                    │
│     }                                                            │
│   ]                                                              │
│ }                                                                │
│                                                                  │
│ STORAGE:                                                         │
│ └─ storage/classified_diffs/stripe/classified_diff_*.json      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 6: ALERTING (Notification Delivery)                       │
│                                                                  │
│ INPUT:  Classified diff (13 minor changes)                      │
│                                                                  │
│ PROCESS:                                                         │
│ 1. Extract critical changes:                                    │
│    critical = [c for c in changes if c.severity in             │
│                 ["breaking", "deprecation"]]                    │
│ 2. If len(critical) == 0:                                       │
│    → Log "No critical changes, skipping alerts"                │
│    → STOP (optimization)                                        │
│ 3. For each critical change:                                    │
│    a. Create Alert object with full context                     │
│    b. Determine channels based on severity:                     │
│       - breaking → [GitHub, Email, Slack]                       │
│       - deprecation → [GitHub]                                  │
│    c. Format alert for each channel:                            │
│       - GitHub: Markdown with labels                            │
│       - Email: HTML + plain text                                │
│       - Slack: Blocks with emojis                               │
│    d. Send via APIs:                                            │
│       - GitHub: PyGithub create_issue()                         │
│       - Email: smtplib.SMTP.send_message()                      │
│       - Slack: requests.post(webhook_url)                       │
│    e. Log result and update alert history                       │
│                                                                  │
│ EXAMPLE FLOW (if breaking change existed):                      │
│                                                                  │
│ Alert Object:                                                    │
│ {                                                                │
│   "vendor": "stripe",                                            │
│   "title": "BREAKING: POST /v1/payments",                       │
│   "severity": "breaking",                                        │
│   "endpoint_id": "POST:/v1/payments",                           │
│   "reasoning": "Required parameter 'source' removed",           │
│   "migration_path": "Use 'payment_method' instead",             │
│   "confidence": 0.99                                             │
│ }                                                                │
│                                                                  │
│ GitHub Issue:                                                    │
│ Title: 🔴 BREAKING: POST /v1/payments                            │
│ Body: [Markdown formatted]                                      │
│ Labels: ["breaking", "stripe", "api-change"]                   │
│                                                                  │
│ Email:                                                           │
│ Subject: 🔴 BREAKING CHANGE: Stripe API                          │
│ Body: [HTML with tables, styling]                               │
│                                                                  │
│ OUTPUT:                                                          │
│ - GitHub issue created: #42                                     │
│ - Email sent to: jhaaditya757@gmail.com                         │
│ - Slack message posted (if configured)                          │
│                                                                  │
│ STORAGE:                                                         │
│ └─ storage/alerts/stripe/alert_history_2026-03-30.json         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Transformation Summary

| Stage | Input Format | Output Format | Size Change | Duration |
|-------|-------------|---------------|-------------|----------|
| Discovery | Vendor name (string) | JSON with URLs | N/A → 2KB | ~20s |
| Ingestion | GitHub URL | Raw OpenAPI (YAML/JSON) | N/A → 2.5MB | ~5s |
| Normalization | Raw spec (2.5MB) | Canonical JSON | 2.5MB → 500KB | <1s* |
| Diff | 2 snapshots (500KB each) | Diff JSON | 1MB → 50KB | <1s |
| Classification | Diff (50KB) | Classified diff | 50KB → 80KB | ~20s** |
| Alerting | Classified diff (80KB) | GitHub/Email/Slack | N/A | <1s |

\* With hash-based skip  
\** 13 changes × 1.5s each

---

## Critical Data Paths

### Path 1: Happy Path (No Changes)

```
vendors.json
    ↓
Discovery (20s) → discovery/stripe.json
    ↓
Ingestion (5s) → Compute hash → MATCH → Skip storage
    ↓
Normalization → Load source hash → MATCH → Skip normalization
    ↓
Diff → baseline == latest → has_changes: false
    ↓
Classification → Skip LLM (optimization)
    ↓
Alerting → No critical changes → Skip alerts
    ↓
Total: ~25 seconds (mostly discovery)
```

### Path 2: Breaking Change Path

```
Discovery → New source found
    ↓
Ingestion → Hash mismatch → Store new spec (2.5MB)
    ↓
Normalization → Hash mismatch → Parse + extract → Store snapshot (500KB)
    ↓
Diff → Detect: parameter_removed on POST:/v1/payments
    ↓
Classification → LLM analysis → severity="breaking", confidence=0.99
    ↓
Alerting → Route to [GitHub, Email, Slack]
    ├─ GitHub: Create issue #42
    ├─ Email: Send HTML email
    └─ Slack: Post message
    ↓
Total: ~3 minutes (includes LLM call)
```

### Path 3: Metadata Drift Path (Real Production Example)

```
Discovery → Same sources
    ↓
Ingestion → Fetch spec → Hash DIFFERENT (upstream update)
    ↓
Normalization → Parse → 13 endpoints have description changes
    ↓
Diff → 13 endpoint_modified events (field_changes=1 each)
    ↓
Classification → LLM analyzes 13 changes × 1.5s = 20s
              → All classified as "minor" (conf 0.96-0.99)
    ↓
Alerting → No breaking/deprecation → Skip alerts
    ↓
Total: ~3 minutes (LLM processing dominates)
```

---

## Hash-Based Deduplication Flow

### Layer 1: Ingestion

```
fetch_spec(url)
    ↓
spec_content = HTTP response body (2.5MB YAML)
    ↓
new_hash = sha256(spec_content).hexdigest()[:16]
# Example: "26ec724b943e9c39"
    ↓
latest_hash = read_metadata("stripe", "latest_hash")
# From: storage/raw/raw_specs/stripe_latest_hash.txt
    ↓
if new_hash == latest_hash:
    logger.info("Spec unchanged, skipping storage")
    return  # EXIT EARLY (saves 5s write + 500KB storage)
else:
    write_spec(spec_content, f"stripe_openapi_{timestamp}.yaml")
    write_metadata("stripe", "latest_hash", new_hash)
```

### Layer 2: Normalization

```
raw_spec_path = "storage/raw/raw_specs/stripe_openapi_2026-03-29.yaml"
    ↓
source_hash = sha256(read_file(raw_spec_path)).hexdigest()[:16]
# Same as Layer 1: "26ec724b943e9c39"
    ↓
latest_snapshot = load_json("storage/normalized/stripe/latest.json")
latest_source_hash = latest_snapshot["metadata"]["source_hash"]
    ↓
if source_hash == latest_source_hash:
    logger.info("Source unchanged, skipping normalization")
    return  # EXIT EARLY (saves parsing + extraction)
else:
    normalized = normalize_spec(raw_spec_path)
    normalized["metadata"]["source_hash"] = source_hash
    store_snapshot(normalized)
```

**Why Two Layers?**

- **Layer 1**: Prevents downloading unchanged specs (saves bandwidth, storage)
- **Layer 2**: Prevents re-normalizing unchanged specs (saves CPU, time)
- **Independence**: Layers can run at different times without issues

---

## Symlink Update Flow

```
New snapshot created:
storage/normalized/stripe/snapshots/2026-03-29T20-27-50.json
    ↓
Update latest.json symlink:
    ↓
os.remove("storage/normalized/stripe/latest.json")  # Delete old symlink
os.symlink(
    "snapshots/2026-03-29T20-27-50.json",  # Target
    "storage/normalized/stripe/latest.json"  # Link path
)
    ↓
Atomic operation (instant, no race condition)
    ↓
Diff engine always reads:
- baseline.json → snapshots/2026-03-20T22-51-37.json
- latest.json → snapshots/2026-03-29T20-27-50.json
    ↓
No need to know specific timestamps!
```

**Manual Baseline Update**:

```bash
python scripts/update_baseline.py stripe 2026-03-29T20-27-50
```

```python
# Script updates symlink:
target = f"snapshots/{timestamp}.json"
link = "storage/normalized/stripe/baseline.json"
os.remove(link)
os.symlink(target, link)
```

---

## Alert Routing Decision Tree

```
Classified Change
    ↓
severity == "breaking"?
    ├─ YES → channels = [GitHub, Email, Slack]
    │   ↓
    │   Priority: CRITICAL
    │   GitHub: Create issue with "breaking" label
    │   Email: HTML with red header "🔴 BREAKING"
    │   Slack: @channel mention, urgent emoji
    │
    └─ NO → severity == "deprecation"?
        ├─ YES → channels = [GitHub]
        │   ↓
        │   Priority: WARNING
        │   GitHub: Create issue with "deprecation" label
        │   (No email/Slack to avoid noise)
        │
        └─ NO → severity == "additive"?
            ├─ YES → channels = [Email]
            │   ↓
            │   Priority: INFO
            │   Email: HTML with green header "✅ NEW FEATURE"
            │   (No GitHub issue needed)
            │
            └─ NO (severity == "minor")
                ↓
                channels = []
                Log only, no alerts
                (Prevents alert fatigue)
```

---

## Configuration Data Flow

```
User adds vendor via UI:
    ↓
POST /vendors/api/add
    ↓
subprocess.run([sys.executable, "scripts/add_vendor.py", "twilio", "Twilio"])
    ↓
Script updates 3 config files:
    ├─ vendors.json: Add {"name": "twilio", "display_name": "Twilio"}
    ├─ vendor_registry.json: Add {"twilio": {"trusted_domains": [...]}}
    └─ vendor_specs.json: Add {"twilio": {"openapi_url": "..."}}
    ↓
All pipelines read these configs on next run
    ↓
Discovery finds "twilio" in vendors.json → triggers search
```

---

## Error Data Flow

```
Pipeline stage fails (e.g., LLM timeout)
    ↓
Exception raised in pipeline code
    ↓
try/except block catches exception
    ↓
logger.error("classification_failed", error=str(e))
    ↓
Structured log written to stdout:
{
  "event": "classification_failed",
  "vendor": "stripe",
  "error": "Timeout after 30s",
  "timestamp": "2026-03-30T10:00:00Z",
  "level": "error"
}
    ↓
Phase 1: Pipeline stops (fail loud)
Phase 2: Fallback to heuristic classification (graceful degradation)
```

---

## Dashboard Real-Time Data Flow

```
User clicks "Discovery" button
    ↓
JavaScript: fetch('/api/pipelines/discovery', {method: 'POST'})
    ↓
Flask route: /api/pipelines/discovery
    ↓
PipelineRunner.run_discovery()
    ├─ Spawns daemon thread
    ├─ Updates status: {"running": true, "progress": 0, "stage": "Starting"}
    └─ Returns immediately: {"success": true, "message": "Started"}
    ↓
JavaScript receives response → shows modal
    ↓
JavaScript polls every 1 second:
    fetch('/api/pipelines/status')
    ↓
Flask returns:
    {"running": true, "progress": 45, "stage": "Fetching specs"}
    ↓
JavaScript updates progress bar: 45%
    ↓
... (continues polling) ...
    ↓
Pipeline completes → status updates:
    {"running": false, "progress": 100, "stage": "Complete"}
    ↓
JavaScript detects completion → location.reload()
    ↓
Page refreshes → shows new data from storage files
```

---

## Storage File Lifecycle

```
Day 1: First run
    ↓
storage/normalized/stripe/snapshots/2026-03-20T10-00-00.json created
    ↓
baseline.json → 2026-03-20T10-00-00.json (auto-set on first run)
latest.json → 2026-03-20T10-00-00.json
    ↓
Day 2-9: No API changes (hash matches)
    ↓
No new snapshots created (deduplication working)
baseline.json → 2026-03-20T10-00-00.json (unchanged)
latest.json → 2026-03-20T10-00-00.json (unchanged)
    ↓
Day 10: API change detected (hash differs)
    ↓
storage/normalized/stripe/snapshots/2026-03-29T10-00-00.json created
    ↓
baseline.json → 2026-03-20T10-00-00.json (still old version)
latest.json → 2026-03-29T10-00-00.json (updated automatically)
    ↓
Diff engine compares:
    baseline (Day 1) vs latest (Day 10)
    ↓
13 changes detected → classified → alerts sent
    ↓
Human reviews changes → approves new version
    ↓
Manual baseline update:
    python scripts/update_baseline.py stripe 2026-03-29T10-00-00
    ↓
baseline.json → 2026-03-29T10-00-00.json (updated manually)
latest.json → 2026-03-29T10-00-00.json (already pointing here)
    ↓
Next diff will show: baseline == latest (no changes)
```

---

## Data Size Metrics (Real Production)

**Stripe Example** (March 29, 2026):

| Stage | File | Size |
|-------|------|------|
| Raw Discovery | `stripe_20260329.json` | 2KB |
| Raw OpenAPI | `stripe_openapi_2026-03-29.yaml` | 2.5MB |
| Normalized | `2026-03-29T20-27-50.json` | 500KB |
| Diff | `diff_2026-03-20_to_2026-03-29.json` | 50KB |
| Classified | `classified_diff_*.json` | 80KB |

**Compression Ratio**: 2.5MB → 80KB = **96% reduction** (raw to final)

**Storage Growth** (3 vendors, daily snapshots):
- Per day: 3 × 500KB = 1.5MB normalized snapshots
- Per month: 1.5MB × 30 = 45MB
- Per year: 45MB × 12 = **540MB** (well within free tier limits)

---

## Concurrent Data Access

**Read Paths** (no conflicts):
- Dashboard reads latest.json while diff engine also reads it
- Classification reads diff.json while alerting reads classified_diff.json
- Multiple users view dashboard simultaneously

**Write Paths** (sequential):
- Only one pipeline run at a time (enforced by PipelineRunner singleton)
- Symlink updates are atomic (no race conditions)
- File writes use temp file + rename pattern for atomicity

---

## Data Retention Strategy

**Current** (Phase 1):
- Keep all snapshots indefinitely
- Total storage: ~540MB/year for 3 vendors

**Planned** (Phase 2):
- Daily snapshots: 90 days
- Weekly snapshots: 1 year
- Monthly snapshots: indefinitely
- Gzip old snapshots: 70% size reduction

**Lifecycle Policy**:
```python
if age > 90_days and not is_week_boundary(snapshot):
    delete(snapshot)
elif age > 365_days and not is_month_boundary(snapshot):
    delete(snapshot)
elif age > 365_days:
    compress(snapshot)  # gzip
```

---

## Data Flow Performance

**Bottlenecks Identified**:

1. **Discovery**: Tavily API latency (2-3s per query)
   - Can't parallelize (rate limits)
   - Mitigation: Cache results (7-day TTL)

2. **Classification**: LLM API latency (1.5s per change)
   - Can parallelize (async batch)
   - Mitigation: Empty diff optimization

3. **Storage I/O**: Negligible (<100ms for 500KB writes)

**Optimization Opportunities**:

1. **Parallel Discovery** (if rate limits allow):
   ```python
   with ThreadPoolExecutor() as executor:
       futures = [executor.submit(discover, v) for v in vendors]
   ```

2. **Batch Classification**:
   ```python
   # Instead of 13 × 1.5s = 19.5s
   # Do: 1 × 3s = 3s (batch all changes in one prompt)
   ```

3. **Redis Caching**:
   - Cache diff results by snapshot hash
   - Cache classification by diff hash
   - 90% cache hit rate possible

---

**Last Updated**: March 31, 2026  
**Data Flow Version**: 1.0
