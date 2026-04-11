# SpecWatch - Failure Modes & Mitigations

## Overview

This document catalogs failure scenarios across all pipeline stages, their impact, detection mechanisms, and mitigation strategies.

---

## Failure Classification

| Severity | Impact | Response Time | Examples |
|----------|--------|---------------|----------|
| **Critical** | Pipeline stops, no data produced | Immediate (page ops) | Database corruption, auth failure |
| **High** | Single vendor fails, others continue | <1 hour | Source URL 404, LLM timeout |
| **Medium** | Degraded data quality | <24 hours | Missing fields, low confidence |
| **Low** | Cosmetic issues | Next release | Formatting errors, log spam |

---

## Discovery Layer Failures

### F1: Tavily API Unavailable

**Scenario**: Tavily service is down or rate-limited

**Detection**:
```python
try:
    results = tavily_search(query)
except requests.exceptions.Timeout:
    # Detected
```

**Impact**: Cannot discover new sources, pipeline blocked

**Current Mitigation** (Phase 1):
```python
# Fail loud - raise exception
raise DiscoveryError("Tavily API unavailable")
```

**Planned Mitigation** (Phase 2):
```python
# Fallback to cached discovery
if tavily_fails:
    cached = load_cached_discovery(vendor, max_age=7_days)
    if cached:
        logger.warning("Using cached discovery (Tavily unavailable)")
        return cached
    else:
        # Fallback to manual config
        return load_manual_config(vendor)
```

**Monitoring**:
- Alert if Tavily errors > 3 in 10 minutes
- Track success rate (target: >99%)

**Cost**: $0 (free tier has built-in retry)

---

### F2: No Sources Found for Vendor

**Scenario**: Tavily returns 0 results for all queries

**Detection**:
```python
if len(results) == 0:
    logger.error("No sources found for vendor")
```

**Impact**: Cannot proceed with ingestion

**Root Causes**:
- New vendor with uncommon name
- Vendor changed domain/branding
- Tavily index outdated

**Current Mitigation**:
```python
# Require manual vendor_specs.json entry
raise DiscoveryError("No sources found, add to vendor_specs.json")
```

**Planned Mitigation**:
```python
# Prompt user to provide manual URLs via dashboard
if no_sources_found:
    notify_user("Please provide OpenAPI URL for {vendor}")
    # Dashboard shows form to input URL
```

**Workaround**: Add to `vendor_specs.json` manually

---

### F3: URL Validation Fails

**Scenario**: Discovered URL returns 404/403/500

**Detection**:
```python
response = http_client.get(url, timeout=10)
if response.status_code != 200:
    logger.warning(f"URL validation failed: {url}")
```

**Impact**: Ingestion will fail downstream

**Current Mitigation**:
```python
# Try alternative URLs from Tavily results
for result in tavily_results:
    if validate_url(result.url):
        return result.url  # First valid URL wins
```

**Planned Mitigation**:
```python
# Store all candidate URLs, try each in order
for url in candidate_urls:
    try:
        content = fetch(url)
        return content
    except:
        continue  # Try next
raise IngestionError("All URLs failed")
```

**Recovery Time**: 0 (automatic fallback)

---

## Ingestion Layer Failures

### F4: GitHub Rate Limiting

**Scenario**: Hit GitHub API rate limit (5000 req/hour)

**Detection**:
```python
if response.status_code == 429:
    retry_after = response.headers.get('Retry-After')
```

**Impact**: Cannot fetch specs from GitHub repos

**Current Mitigation**:
```python
# Exponential backoff with jitter
@retry(wait=wait_exponential(min=1, max=60), stop=stop_after_attempt(3))
def fetch_github_url(url):
    # Retry logic built-in
```

**Planned Mitigation**:
```python
# Respect Retry-After header
if rate_limited:
    sleep_seconds = int(response.headers['Retry-After'])
    logger.info(f"Rate limited, sleeping {sleep_seconds}s")
    time.sleep(sleep_seconds)
    retry()
```

**Prevention**:
- Use authenticated GitHub requests (5000/hour → 5000/hour per token)
- Cache successful fetches for 24 hours

**Monitoring**: Track GitHub API quota usage

---

### F5: Malformed OpenAPI Spec

**Scenario**: Fetched spec is not valid YAML/JSON

**Detection**:
```python
try:
    spec = yaml.safe_load(content)
except yaml.YAMLError as e:
    logger.error(f"Invalid YAML: {e}")
```

**Impact**: Normalization will fail

**Current Mitigation**:
```python
# Fail loud - raise exception
raise IngestionError(f"Invalid spec format: {e}")
```

**Planned Mitigation**:
```python
# Try alternative parsers
try:
    spec = yaml.safe_load(content)
except:
    try:
        spec = json.loads(content)
    except:
        # Fuzzy YAML parser (tolerates minor errors)
        spec = ruamel.yaml.load(content, Loader=ruamel.yaml.RoundTripLoader)
```

**Recovery**: Manual fix required, notify ops team

**Frequency**: Rare (seen 0 times in production)

---

### F6: Network Timeout

**Scenario**: HTTP request times out (>30s)

**Detection**:
```python
try:
    response = requests.get(url, timeout=30)
except requests.exceptions.Timeout:
    # Detected
```

**Impact**: Missing spec for current run

**Current Mitigation**:
```python
# Retry with exponential backoff (3 attempts)
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
def fetch_spec(url):
    return requests.get(url, timeout=30)
```

**Planned Mitigation**:
```python
# Use cached spec from previous run
if fetch_fails:
    cached_spec = load_latest_cached_spec(vendor)
    logger.warning("Using cached spec (network timeout)")
    return cached_spec
```

**Frequency**: <1% of requests

---

### F7: Spec Size Exceeds Limit

**Scenario**: OpenAPI spec is >10MB (memory issue)

**Detection**:
```python
content_length = int(response.headers.get('Content-Length', 0))
if content_length > 10_000_000:
    raise IngestionError("Spec too large")
```

**Impact**: Out of memory, process crash

**Current Mitigation**:
```python
# Hard limit at 10MB
if size > 10MB:
    raise IngestionError("Spec exceeds size limit")
```

**Planned Mitigation**:
```python
# Stream large files to disk
with open(temp_file, 'wb') as f:
    for chunk in response.iter_content(chunk_size=8192):
        f.write(chunk)
```

**Recovery**: Contact vendor to split spec or use subset

---

## Normalization Layer Failures

### F8: Missing Required Fields

**Scenario**: OpenAPI spec missing `paths` or `servers` field

**Detection**:
```python
if 'paths' not in spec:
    logger.error("Missing 'paths' field in OpenAPI spec")
```

**Impact**: Cannot extract endpoints

**Current Mitigation**:
```python
# Use defaults
base_url = spec.get('servers', [{}])[0].get('url', 'https://api.example.com')
endpoints = spec.get('paths', {})
```

**Planned Mitigation**:
```python
# Flag as incomplete, notify user
if 'paths' not in spec:
    mark_vendor_incomplete(vendor)
    notify_user(f"{vendor} spec incomplete, manual review needed")
    # Still create partial snapshot
```

**Frequency**: Rare (well-formed specs from major vendors)

---

### F9: Unsupported OpenAPI Version

**Scenario**: Spec is OpenAPI 2.0 (Swagger), not 3.x

**Detection**:
```python
openapi_version = spec.get('openapi', spec.get('swagger', ''))
if not openapi_version.startswith('3.'):
    logger.warning(f"Unsupported OpenAPI version: {openapi_version}")
```

**Impact**: Parser expects 3.x structure

**Current Mitigation**:
```python
# Skip normalization
raise NormalizationError(f"Unsupported version: {openapi_version}")
```

**Planned Mitigation**:
```python
# Auto-convert Swagger 2.0 → OpenAPI 3.0
if is_swagger_2(spec):
    spec = convert_swagger_to_openapi(spec)  # Use swagger2openapi library
```

**Recovery**: Use conversion tool manually

---

### F10: Circular References in Schema

**Scenario**: Spec has `$ref` loops (infinite recursion)

**Detection**:
```python
# Python's default recursion limit triggers
RecursionError: maximum recursion depth exceeded
```

**Impact**: Parser crashes

**Current Mitigation**:
```python
# Set recursion limit
sys.setrecursionlimit(1000)  # Default: 1000
# If hit, fails with clear error
```

**Planned Mitigation**:
```python
# Track visited refs
def resolve_ref(ref, visited=None):
    if visited is None:
        visited = set()
    if ref in visited:
        return {"type": "object", "description": "Circular reference"}
    visited.add(ref)
    # Continue resolution
```

**Frequency**: Extremely rare (spec validation tools catch this)

---

## Diff Engine Failures

### F11: Corrupted Snapshot Files

**Scenario**: `baseline.json` or `latest.json` is corrupted/unreadable

**Detection**:
```python
try:
    with open('baseline.json') as f:
        baseline = json.load(f)
except json.JSONDecodeError:
    logger.error("Corrupted baseline snapshot")
```

**Impact**: Cannot compute diff

**Current Mitigation**:
```python
# Fail loud
raise DiffError("Corrupted snapshot file")
```

**Planned Mitigation**:
```python
# Rebuild from snapshots directory
if corrupted:
    logger.warning("Rebuilding symlink from latest snapshot")
    latest_snapshot = find_latest_snapshot(vendor)
    update_symlink('latest.json', latest_snapshot)
    retry_diff()
```

**Prevention**: Use checksums, atomic writes

---

### F12: Endpoint ID Collision

**Scenario**: Two endpoints generate same ID (e.g., `POST:/v1/users`)

**Detection**:
```python
endpoint_ids = [e['id'] for e in endpoints]
duplicates = [id for id in endpoint_ids if endpoint_ids.count(id) > 1]
if duplicates:
    logger.error(f"Duplicate endpoint IDs: {duplicates}")
```

**Impact**: Diff matching fails (ambiguous)

**Current Mitigation**:
```python
# Should not happen with proper normalization
# Endpoints sorted, IDs are unique by definition
```

**Planned Mitigation**:
```python
# Add disambiguation suffix
if id_exists(endpoint_id):
    endpoint_id = f"{endpoint_id}__{index}"
```

**Frequency**: Never seen (proper ID generation prevents this)

---

## Classification Layer Failures

### F13: LLM API Timeout

**Scenario**: Groq API call exceeds 30s timeout

**Detection**:
```python
try:
    response = groq_client.chat.completions.create(...)
except asyncio.TimeoutError:
    logger.error("LLM API timeout")
```

**Impact**: Change not classified

**Current Mitigation**:
```python
# Fallback to heuristic classification
if llm_fails:
    classification = heuristic_classify(change)
    classification['confidence'] = 0.7  # Lower confidence
    logger.warning("Used heuristic fallback (LLM timeout)")
```

**Heuristic Rules**:
```python
def heuristic_classify(change):
    if change.type == "endpoint_removed":
        return {"severity": "breaking", "confidence": 0.95}
    elif change.type == "endpoint_deprecated":
        return {"severity": "deprecation", "confidence": 0.9}
    elif change.type == "parameter_type_changed":
        return {"severity": "breaking", "confidence": 0.85}
    else:
        return {"severity": "minor", "confidence": 0.5}
```

**Recovery Time**: 0 (automatic fallback)

---

### F14: LLM Returns Invalid JSON

**Scenario**: LLM response is not parseable JSON

**Detection**:
```python
try:
    classification = json.loads(llm_response)
except json.JSONDecodeError:
    logger.error("LLM returned invalid JSON")
```

**Impact**: Classification fails

**Current Mitigation**:
```python
# Strip markdown fences and retry parse
cleaned = llm_response.strip('```json\n').strip('```\n')
try:
    classification = json.loads(cleaned)
except:
    # Fallback to heuristic
    classification = heuristic_classify(change)
```

**Planned Mitigation**:
```python
# Use structured output mode (JSON schema validation)
response = groq_client.chat.completions.create(
    response_format={"type": "json_object"},
    # Guarantees valid JSON
)
```

**Frequency**: Rare (<1% with temperature=0.3)

---

### F15: LLM Rate Limiting

**Scenario**: Exceeded Groq API quota (free tier limits)

**Detection**:
```python
if response.status_code == 429:
    logger.error("LLM API rate limited")
```

**Impact**: Cannot classify remaining changes

**Current Mitigation**:
```python
# Fail for current run, retry next run
raise ClassificationError("Rate limited, retry later")
```

**Planned Mitigation**:
```python
# Queue changes for later processing
if rate_limited:
    queue_for_retry(pending_changes)
    # Classify what we can, mark rest as pending
    # Retry in 1 hour
```

**Prevention**: Monitor quota usage, upgrade to paid tier if needed

---

### F16: Low Confidence Classifications

**Scenario**: LLM returns confidence <0.5

**Detection**:
```python
if classification['confidence'] < 0.5:
    logger.warning("Low confidence classification")
```

**Impact**: Potentially incorrect severity

**Current Mitigation**:
```python
# Accept but flag for manual review
classification['needs_review'] = True
# Still use the classification
```

**Planned Mitigation**:
```python
# Escalate to human review
if confidence < 0.5:
    create_review_task(change, classification)
    # Send notification to ops team
    # Wait for human approval before alerting
```

**Frequency**: Rare (5% of classifications)

---

## Alerting Layer Failures

### F17: GitHub Authentication Failure

**Scenario**: Invalid/expired GitHub token

**Detection**:
```python
try:
    repo = github.get_repo(repo_name)
except github.GithubException as e:
    if e.status == 401:
        logger.error("GitHub auth failed")
```

**Impact**: Cannot create issues

**Current Mitigation**:
```python
# Fail alert, log error
raise AlertingError("GitHub authentication failed")
# Email alert still sent (fallback channel)
```

**Planned Mitigation**:
```python
# Rotate to backup token
if auth_fails:
    try:
        github = Github(backup_token)
        retry_issue_creation()
    except:
        # Send alert via email only
        send_email_alert(alert)
```

**Recovery**: Regenerate GitHub token, update `.env`

---

### F18: SMTP Connection Failure

**Scenario**: Gmail SMTP server unreachable

**Detection**:
```python
try:
    smtp.connect('smtp.gmail.com', 587)
except smtplib.SMTPException:
    logger.error("SMTP connection failed")
```

**Impact**: Cannot send email alerts

**Current Mitigation**:
```python
# Retry 3 times with exponential backoff
@retry(stop=stop_after_attempt(3))
def send_email(alert):
    # SMTP connection + send
```

**Planned Mitigation**:
```python
# Fallback to alternative email service
if gmail_fails:
    try:
        send_via_sendgrid(alert)  # Alternative provider
    except:
        # Dead letter queue
        store_failed_alert(alert)
        # Ops team reviews manually
```

**Recovery Time**: <1 hour (Gmail reliability >99.9%)

---

### F19: Slack Webhook Fails

**Scenario**: Slack webhook URL returns 404/403

**Detection**:
```python
response = requests.post(webhook_url, json=payload)
if response.status_code != 200:
    logger.error(f"Slack webhook failed: {response.status_code}")
```

**Impact**: No Slack notification

**Current Mitigation**:
```python
# Log error, continue (GitHub + Email still sent)
logger.error("Slack alert failed, but GitHub/Email sent")
```

**Planned Mitigation**:
```python
# Retry with alternative webhook
if primary_webhook_fails:
    try:
        requests.post(backup_webhook_url, json=payload)
    except:
        # Give up, log to dead letter queue
```

**Recovery**: Update webhook URL in `.env`

---

## Storage Layer Failures

### F20: Disk Full

**Scenario**: Storage partition full, cannot write

**Detection**:
```python
try:
    with open(filepath, 'w') as f:
        json.dump(data, f)
except OSError as e:
    if e.errno == errno.ENOSPC:
        logger.critical("Disk full!")
```

**Impact**: Pipeline stops, data loss

**Current Mitigation**:
```python
# Fail loud
raise StorageError("Disk full")
```

**Planned Mitigation**:
```python
# Check available space before write
available = shutil.disk_usage('/').free
if available < 100_000_000:  # 100MB
    logger.critical("Low disk space, cleaning old snapshots")
    cleanup_old_snapshots(keep_last=30)
    # Retry write
```

**Prevention**: Monitor disk usage (alert at 80%)

---

### F21: File Permission Denied

**Scenario**: Cannot write to storage directory

**Detection**:
```python
try:
    with open(filepath, 'w') as f:
        json.dump(data, f)
except PermissionError:
    logger.error("Permission denied")
```

**Impact**: Cannot store results

**Current Mitigation**:
```python
# Fail loud
raise StorageError("Permission denied on storage directory")
```

**Recovery**: Fix permissions with `chmod 755 storage/`

---

### F22: Symlink Creation Fails

**Scenario**: OS doesn't support symlinks (Windows without admin)

**Detection**:
```python
try:
    os.symlink(target, link)
except OSError:
    logger.error("Symlink creation failed")
```

**Impact**: Cannot use baseline/latest pattern

**Current Mitigation**:
```python
# Not implemented (assumes Unix-like OS)
```

**Planned Mitigation**:
```python
# Fallback to file copy
if symlink_fails:
    shutil.copy(target, link)  # Copy instead of link
    # Works on Windows, wastes space but functional
```

**Frequency**: N/A (Mac/Linux deployment assumed)

---

## Dashboard Failures

### F23: Pipeline Runner Stuck

**Scenario**: Background thread hangs, never completes

**Detection**:
```python
# Monitor thread status
if runner.status['running'] and time_since_start > 600:  # 10 minutes
    logger.error("Pipeline stuck")
```

**Impact**: UI shows "Running..." forever

**Current Mitigation**:
```python
# Subprocess timeout enforced
subprocess.run(..., timeout=300)  # 5 minutes max
# After timeout, thread exits
```

**Planned Mitigation**:
```python
# Add kill switch
@app.route('/api/pipelines/kill', methods=['POST'])
def kill_pipeline():
    runner.kill()  # Terminate thread forcefully
    return {"success": true}
```

**Recovery**: Restart Flask app

---

### F24: Progress Not Updating

**Scenario**: JavaScript polling stops (network error)

**Detection**: User reports "stuck at 45%"

**Impact**: Poor UX, user doesn't know pipeline status

**Current Mitigation**:
```python
# JavaScript retry on fetch error
.catch(err => {
    console.error("Status poll failed:", err);
    setTimeout(pollStatus, 5000);  // Retry in 5s
})
```

**Planned Mitigation**:
```python
# WebSocket for real-time updates (no polling)
# More reliable, instant updates
```

**Frequency**: Rare (network glitches)

---

## Systemic Failures

### F25: Out of Memory

**Scenario**: Large spec (10MB+) crashes Python process

**Detection**: Process killed by OS (OOMKilled)

**Impact**: Pipeline stops, no logs

**Current Mitigation**:
```python
# Size limit check before processing
if file_size > 10_000_000:
    raise IngestionError("File too large")
```

**Planned Mitigation**:
```python
# Stream large files
# Increase process memory limit
# Use pagination for large diffs
```

**Prevention**: Monitor memory usage

---

### F26: Multiple Concurrent Runs

**Scenario**: User clicks "Discovery" twice in parallel

**Detection**:
```python
if runner.is_running():
    raise RuntimeError("Pipeline already running")
```

**Impact**: Race conditions, corrupted state

**Current Mitigation**:
```python
# Singleton pattern enforced
# Second click returns error
return jsonify({"error": "Pipeline already running"}), 409
```

**Prevention**: Disable button when running (frontend)

---

## Monitoring & Alerting

### Critical Alerts (Page Ops)

- [ ] Pipeline fails >3 times in 1 hour
- [ ] Disk usage >90%
- [ ] Memory usage >90%
- [ ] All vendors failing (systemic issue)

### Warning Alerts (Review in <1 hour)

- [ ] Single vendor fails >2 times
- [ ] LLM timeout rate >10%
- [ ] Alert delivery failure
- [ ] Low confidence classification >20%

### Info Alerts (Daily digest)

- [ ] Discovery found 0 sources
- [ ] Heuristic fallback used
- [ ] Network timeout (retried successfully)

---

## Recovery Procedures

### Procedure 1: Reset Stuck Pipeline

```bash
# Kill Flask app
pkill -f "python run_dashboard.py"

# Clear stuck state
rm -f /tmp/pipeline.lock

# Restart
python3 run_dashboard.py
```

### Procedure 2: Rebuild Corrupted Symlinks

```bash
# Navigate to vendor dir
cd storage/normalized/stripe

# Find latest snapshot
latest=$(ls snapshots/ | tail -1)

# Recreate symlinks
ln -sf "snapshots/$latest" latest.json
ln -sf "snapshots/$baseline" baseline.json  # Replace $baseline
```

### Procedure 3: Manual Classification Run

```bash
# If classification failed, re-run manually
python3 -m pipelines.classification_pipeline

# Check results
cat storage/classified_diffs/stripe/classified_diff_*.json | jq .
```

### Procedure 4: Disk Space Cleanup

```bash
# Remove old snapshots (keep last 30 days)
find storage/normalized/*/snapshots -mtime +30 -delete

# Remove old diffs
find storage/diffs -mtime +90 -delete

# Compress old files
find storage -name "*.json" -mtime +180 -exec gzip {} \;
```

---

## Failure Rate Targets

| Component | Target Availability | Max Acceptable Failures |
|-----------|---------------------|-------------------------|
| Discovery | 99% | 3/month |
| Ingestion | 99.5% | 1/month |
| Normalization | 99.9% | <1/month |
| Diff | 99.99% | Never (no external deps) |
| Classification | 95% | LLM fallback acceptable |
| Alerting | 99% | 3/month |
| Dashboard | 99.9% | <1/month |

---

**Last Updated**: March 31, 2026  
**Incident Count (Last 30 Days)**: 0 critical, 2 warnings
