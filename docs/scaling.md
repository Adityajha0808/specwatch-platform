# SpecWatch - Scaling Strategy

## Current Capacity (Phase 1)

**Hardware**: Single EC2 t3.small instance (2 vCPU, 2GB RAM)  
**Vendors**: 3 (Stripe, OpenAI, Twilio)  
**Pipeline Duration**: ~3 minutes  
**Daily Runs**: 1-2  
**Cost**: $0/month (free tiers)  

**Bottlenecks**:
- Discovery: Tavily API latency (2-3s × 3 queries per vendor)
- Classification: LLM API latency (1.5s per change)
- Storage: Local filesystem (single point of failure)

---

## Scaling Dimensions

```
┌─────────────────────────────────────────────────────────────┐
│                    Scaling Vectors                          │
│                                                             │
│  X-Axis: Number of Vendors (horizontal scaling)            │
│  Y-Axis: Pipeline Frequency (temporal scaling)             │
│  Z-Axis: Data Volume per Vendor (vertical scaling)         │
└─────────────────────────────────────────────────────────────┘
```

### Dimension 1: Vendor Count (X-Axis)

| Vendors | Pipeline Duration | Architecture | Cost/Month |
|---------|-------------------|--------------|------------|
| **3** (current) | 3 min | Single process | $0 |
| **10** | 10 min | Parallel discovery | $10 |
| **20** | 15 min | Worker pool | $25 |
| **50** | 20 min | Kubernetes + Redis | $75 |
| **100** | 25 min | Distributed Beam | $200 |
| **500** | 30 min | Multi-region cluster | $1000 |

### Dimension 2: Run Frequency (Y-Axis)

| Frequency | Use Case | Infrastructure | Cost Impact |
|-----------|----------|----------------|-------------|
| **Daily** (current) | Routine monitoring | Cron job | 1x |
| **Hourly** | Fast detection | Scheduler service | 24x |
| **15 minutes** | Critical APIs | Queue-based | 96x |
| **Real-time** | Live monitoring | Event-driven | 200x+ |

### Dimension 3: Data Volume (Z-Axis)

| Spec Size | Vendors Affected | Storage Strategy | Cost Impact |
|-----------|------------------|------------------|-------------|
| **<5MB** (current) | Most | Local FS | 1x |
| **5-20MB** | Large APIs (AWS) | S3 Standard | 2x |
| **20-100MB** | Monolithic specs | S3 + compression | 5x |
| **>100MB** | Legacy systems | Streaming parser | 10x |

---

## Scaling Milestones

### Milestone 1: 10 Vendors (Near-term)

**Changes Required**: Minimal

**Architecture**:
```
Single EC2 instance (t3.medium: 2 vCPU, 4GB RAM)
    ├─ Parallel discovery (ThreadPoolExecutor)
    ├─ Sequential normalization
    └─ Sequential classification
```

**Performance**:
- Discovery: 3 vendors × 3 queries = 9 sequential → 20s
- With parallelism: 3 queries (all vendors) → 6s (3x speedup)
- Total pipeline: 10 minutes (vs 3 min current)

**Code Changes**:
```python
# discovery_pipeline.py
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(discover_vendor, v) for v in vendors]
    results = [f.result() for f in futures]
```

**Cost**: $10/month (Tavily paid tier, compute stays free tier)

**Effort**: 1 day

---

### Milestone 2: 20 Vendors (3-6 months)

**Changes Required**: Moderate

**Architecture**:
```
EC2 t3.large (2 vCPU, 8GB RAM) + Redis (t3.micro)
    ├─ Async discovery with rate limiting
    ├─ Parallel normalization (process pool)
    ├─ Batch LLM classification
    └─ Redis cache (discovery + diffs)
```

**Performance**:
- Discovery: Parallel with respect to Tavily rate limits
- Normalization: 4 workers (multiprocessing.Pool)
- Classification: Batch 10 changes per LLM call (10x speedup)
- Total pipeline: 15 minutes

**Code Changes**:
```python
# classification_pipeline.py
def batch_classify(changes: List[Change]) -> List[Classification]:
    """Classify up to 10 changes in single LLM call"""
    prompt = build_batch_prompt(changes)
    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4096  # Larger for batch
    )
    return parse_batch_response(response)
```

**Cost**: $25/month
- Compute: $15 (t3.large spot)
- Redis: $5 (t3.micro)
- APIs: $5 (Tavily + Groq paid tiers)

**Effort**: 1 week

---

### Milestone 3: 50 Vendors (6-12 months)

**Changes Required**: Significant

**Architecture**:
```
Kubernetes Cluster (3 nodes: t3.medium)
    ├─ Discovery Workers (3 pods, parallel)
    ├─ Normalization Workers (5 pods, parallel)
    ├─ Classification Workers (2 pods, batch processing)
    ├─ Redis Cluster (caching + queueing)
    ├─ S3 for storage (versioned buckets)
    └─ RDS Postgres (metadata index)
```

**Data Flow**:
```
Scheduler (CronJob)
    ↓
Pub/Sub: Discovery Queue
    ↓
Discovery Workers (parallel) → Redis cache
    ↓
Pub/Sub: Ingestion Queue
    ↓
Ingestion Workers (parallel) → S3 raw storage
    ↓
... (continue pattern)
```

**Performance**:
- All stages parallelized
- Total pipeline: 20 minutes (50 vendors)
- Average per vendor: 24 seconds

**Infrastructure as Code**:
```yaml
# k8s/discovery-worker.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: discovery-worker
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: worker
        image: specwatch:discovery
        env:
        - name: REDIS_URL
          value: redis://redis-cluster:6379
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
```

**Cost**: $75/month
- Kubernetes: $45 (3 × t3.medium spot)
- Redis: $10 (elasticache.t3.small)
- S3: $5 (500GB with lifecycle policies)
- RDS: $10 (db.t3.micro)
- APIs: $5

**Effort**: 1 month

---

### Milestone 4: 100 Vendors (1-2 years)

**Changes Required**: Major

**Architecture**:
```
Multi-Region Kubernetes
    ├─ US-East: Primary cluster (50 vendors)
    ├─ US-West: Secondary cluster (50 vendors)
    ├─ Global Redis (cluster mode)
    ├─ S3 with cross-region replication
    ├─ RDS Multi-AZ with read replicas
    └─ CloudFront CDN (dashboard)
```

**Advanced Optimizations**:

1. **Differential Snapshots** (storage optimization):
```python
# Only store changed endpoints, not full snapshot
diff_snapshot = {
    "base_version": "2026-03-20",
    "changes_only": True,
    "added_endpoints": [...],
    "modified_endpoints": [...],
    # Full snapshot reconstructed on-demand
}
# Storage: 500KB → 50KB (10x reduction)
```

2. **Smart Scheduling** (cost optimization):
```python
# Schedule based on API change frequency
vendors_by_frequency = {
    "stripe": "hourly",      # Changes often
    "twilio": "daily",       # Stable
    "legacy_api": "weekly"   # Rarely changes
}
# Cost savings: 70% (avoid unnecessary runs)
```

3. **Predictive Deduplication** (performance):
```python
# ML model predicts if spec will differ
if predict_no_change(vendor, last_fetch_time):
    skip_ingestion()  # Save 5s per vendor
```

**Performance**:
- Total pipeline: 25 minutes (100 vendors)
- Parallelism: 10x (10 workers per stage)

**Cost**: $200/month

**Effort**: 3 months

---

### Milestone 5: 500+ Vendors (2-3 years)

**Changes Required**: Complete redesign

**Architecture**: Apache Beam on Dataflow

```python
import apache_beam as beam

with beam.Pipeline() as pipeline:
    (pipeline
     | 'Read Vendors' >> beam.Create(vendors)
     | 'Discover' >> beam.ParDo(DiscoveryFn())
     | 'Ingest' >> beam.ParDo(IngestionFn())
     | 'Normalize' >> beam.ParDo(NormalizationFn())
     | 'Group by Vendor' >> beam.GroupByKey()
     | 'Diff' >> beam.ParDo(DiffFn())
     | 'Classify' >> beam.ParDo(ClassificationFn())
     | 'Alert' >> beam.ParDo(AlertingFn())
     | 'Write Results' >> beam.io.WriteToParquet('s3://results/')
    )
```

**Features**:
- Auto-scaling (0-100 workers dynamically)
- Fault tolerance (automatic retries)
- Exactly-once processing
- Streaming mode (real-time monitoring)

**Cost**: $1000/month

**Effort**: 6 months

---

## Specific Bottleneck Solutions

### Bottleneck 1: Discovery (Tavily Latency)

**Current**: 3 queries × 2s = 6s per vendor × 3 vendors = 18s total

**Solution Matrix**:

| Vendors | Strategy | Latency | Cost |
|---------|----------|---------|------|
| **3** | Sequential | 18s | $0 |
| **10** | Parallel (ThreadPoolExecutor) | 6s | $10 |
| **20** | Cached (7-day TTL) + parallel | 2s* | $20 |
| **50** | Tavily batch API + cache | 1s* | $50 |

\* Assumes 80% cache hit rate

**Implementation**:
```python
# Parallel + caching
@lru_cache(maxsize=100)
def cached_discovery(vendor: str) -> Discovery:
    # Cache for 7 days (604800s)
    return discover_sources(vendor)

with ThreadPoolExecutor(max_workers=10) as executor:
    discoveries = executor.map(cached_discovery, vendors)
```

---

### Bottleneck 2: Classification (LLM Latency)

**Current**: 1.5s per change (serial)

**Solution Matrix**:

| Changes | Strategy | Latency | Accuracy | Cost |
|---------|----------|---------|----------|------|
| **1-5** | Serial calls | 1.5s × n | 95% | $0.01 |
| **5-20** | Batch prompt | 3s total | 93% | $0.003 |
| **20-50** | Parallel batch | 3s total | 93% | $0.01 |
| **50+** | Map-reduce | 5s total | 92% | $0.02 |

**Batch Implementation**:
```python
def batch_classify(changes: List[Change]) -> List[Classification]:
    """Classify up to 10 changes in single call"""
    prompt = f"""
    Classify these {len(changes)} API changes:
    
    {json.dumps([c.to_dict() for c in changes], indent=2)}
    
    Return JSON array of classifications.
    """
    response = llm_call(prompt, max_tokens=4096)
    return parse_json_array(response)

# Usage
for batch in chunks(all_changes, size=10):
    results = batch_classify(batch)
```

**Speedup**: 10x (10 changes in 3s vs 15s)

---

### Bottleneck 3: Storage I/O

**Current**: Local filesystem (500KB writes)

**Solution Matrix**:

| Vendors | Strategy | Latency | Durability | Cost |
|---------|----------|---------|------------|------|
| **3** | Local FS | <100ms | Low | $0 |
| **10** | S3 Standard | 200ms | High | $2 |
| **20** | S3 + CDN | 50ms* | High | $10 |
| **50** | S3 + Redis | 10ms* | High | $25 |

\* Assumes cache hit

**Implementation**:
```python
class HybridStorage:
    def __init__(self):
        self.redis = Redis()  # L1 cache
        self.s3 = S3Client()  # L2 persistent
    
    def store(self, key: str, data: dict):
        # Write-through cache
        self.redis.setex(key, 3600, json.dumps(data))  # 1 hour TTL
        self.s3.put_object(Key=key, Body=json.dumps(data))
    
    def retrieve(self, key: str) -> dict:
        # Try cache first
        cached = self.redis.get(key)
        if cached:
            return json.loads(cached)
        # Fallback to S3
        obj = self.s3.get_object(Key=key)
        data = json.loads(obj['Body'].read())
        # Populate cache
        self.redis.setex(key, 3600, json.dumps(data))
        return data
```

---

## Cost Optimization Strategies

### Strategy 1: Spot Instances

**Savings**: 70% on compute

```yaml
# k8s node pool with spot instances
nodeSelector:
  node.kubernetes.io/instance-type: t3.medium
  karpenter.sh/capacity-type: spot
tolerations:
  - key: "spot"
    operator: "Exists"
```

**Risk**: Nodes can be terminated (handled by Kubernetes rescheduling)

---

### Strategy 2: Reserved Instances

**Commitment**: 1-year reservation for predictable workload

**Savings**: 40% on RDS, ElastiCache

**When**: 50+ vendors (predictable baseline capacity)

---

### Strategy 3: Intelligent Caching

**Cache Layers**:

1. **Discovery Cache** (Redis, 7-day TTL)
   - Savings: 90% Tavily API calls
   - Impact: $50 → $5/month

2. **Diff Cache** (Redis, 90-day TTL)
   - Key: `diff:{hash(baseline)}:{hash(latest)}`
   - Savings: Recompute avoidance
   - Impact: 30% CPU reduction

3. **Classification Cache** (Redis, 7-day TTL)
   - Key: `classification:{hash(diff)}`
   - Savings: 80% LLM calls (identical diffs)
   - Impact: $20 → $4/month

**Total Savings**: ~$60/month at 50 vendors

---

### Strategy 4: Lifecycle Policies

**S3 Tiering**:
```
0-30 days:  S3 Standard (hot)
30-90 days: S3 Standard-IA (warm)
90-365 days: S3 Glacier Instant Retrieval (cold)
>365 days: S3 Glacier Deep Archive (archive)
```

**Savings**: 80% on storage costs

---

## Monitoring at Scale

### Metrics to Track

**Per-Vendor Metrics**:
- Discovery success rate
- Ingestion latency (p50, p95, p99)
- Normalization errors
- Classification confidence distribution
- Alert delivery success rate

**System Metrics**:
- Pipeline throughput (vendors/hour)
- Queue depth (discovery, ingestion, classification)
- CPU/Memory utilization
- Disk I/O
- Network bandwidth

**Cost Metrics**:
- API spend per vendor (Tavily, Groq)
- Storage growth rate (GB/month)
- Compute cost per pipeline run

### Alerting Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Pipeline duration | >10 min | >20 min |
| Discovery failure rate | >5% | >10% |
| Classification fallback | >20% | >50% |
| Queue depth | >100 | >500 |
| CPU usage | >70% | >90% |
| Memory usage | >80% | >95% |

---

## Scalability Testing Plan

### Load Test 1: 10 Vendors

**Goal**: Verify parallelism works

**Procedure**:
1. Add 7 test vendors (mock APIs)
2. Run full pipeline
3. Measure: total duration, CPU usage, memory usage
4. Expected: <10 minutes, <50% CPU

### Load Test 2: 50 Vendors (Simulated)

**Goal**: Identify bottlenecks before production

**Procedure**:
1. Generate 50 synthetic OpenAPI specs
2. Run ingestion → classification
3. Measure: queue depths, worker saturation
4. Expected: <20 minutes with Kubernetes

### Load Test 3: Sustained Load

**Goal**: Verify no memory leaks

**Procedure**:
1. Run pipeline every hour for 24 hours
2. Monitor: memory growth, file handle leaks
3. Expected: Stable memory usage, no crashes

---

## Migration Checklist

### Phase 1 → Phase 2 (10-20 Vendors)

- [ ] Add Redis for caching
- [ ] Implement parallel discovery
- [ ] Implement batch classification
- [ ] Migrate to S3 (optional)
- [ ] Set up monitoring dashboards
- [ ] Load test with 20 vendors

### Phase 2 → Phase 3 (50 Vendors)

- [ ] Deploy Kubernetes cluster
- [ ] Convert pipelines to workers
- [ ] Add message queue (SQS/Pub/Sub)
- [ ] Migrate to RDS for metadata
- [ ] Implement auto-scaling
- [ ] Set up multi-region backups

---

## Scaling Decision Tree

```
How many vendors?
│
├─ <10 vendors
│  └─ Single EC2 instance
│     └─ Parallel discovery (ThreadPoolExecutor)
│
├─ 10-20 vendors
│  └─ EC2 + Redis
│     └─ Batch classification
│
├─ 20-50 vendors
│  └─ Kubernetes (3 nodes)
│     └─ Worker pools + queues
│
├─ 50-100 vendors
│  └─ Multi-region Kubernetes
│     └─ Advanced caching + differential snapshots
│
└─ >100 vendors
   └─ Apache Beam / Dataflow
      └─ Auto-scaling + streaming mode
```

---

**Recommended Path**: Start with Phase 1, migrate to Phase 2 when vendor count >10

**Last Updated**: March 31, 2026  
**Next Review**: When vendor count reaches 8
