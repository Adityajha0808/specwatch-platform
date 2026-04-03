# SpecWatch

**Automated API Change Detection & Intelligent Alerting**

SpecWatch monitors external API providers (Stripe, Twilio, OpenAI, etc.) and automatically detects breaking changes, deprecations, and new features. It uses LLM-based classification to assess impact and sends targeted alerts via GitHub Issues and Email.

---

## 🎯 What It Does

- **Discovers** official API sources (docs, OpenAPI specs, changelogs)
- **Fetches** and versions API specifications automatically
- **Normalizes** diverse OpenAPI formats into a canonical schema
- **Detects** changes between API versions with precision
- **Classifies** changes by severity using LLM (breaking/deprecation/additive/minor)
- **Alerts** stakeholders via GitHub Issues, Email, or Slack based on impact
- **Provides** a web dashboard for pipeline control and visualization

---

## 🏗️ Architecture

```
Discovery → Ingestion → Normalization → Diff → Classification → Alerting
```

### Pipeline Stages

| Stage | Purpose | Output |
|-------|---------|--------|
| **Discovery** | Find official API sources via Tavily search | `storage/discovery/{vendor}.json` |
| **Ingestion** | Fetch raw OpenAPI specifications | `storage/raw/raw_specs/{vendor}_openapi_*.yaml` |
| **Normalization** | Convert to canonical format | `storage/normalized/{vendor}/snapshots/*.json` |
| **Diff** | Detect changes between versions | `storage/diffs/{vendor}/diff_*.json` |
| **Classification** | LLM-based severity analysis | `storage/classified_diffs/{vendor}/classified_diff_*.json` |
| **Alerting** | Send notifications based on severity | GitHub Issues + Email |

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Virtual environment** (recommended)
- **API Keys**:
  - Tavily API key (for discovery)
  - Groq API key (for LLM classification)
  - GitHub token (for issue creation)
  - Gmail app password (for email alerts)

### Installation

```bash
# Clone repository
git clone https://github.com/Adityajha0808/specwatch-platform.git
cd specwatch-platform

# Create virtual environment
python3 -m venv specwatchenv
source specwatchenv/bin/activate  # On Mac/Linux
# specwatchenv\Scripts\activate    # On Windows

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```bash
# Tavily API (for discovery)
TAVILY_API_KEY=tvly-xxxxxxxxxxxxx

# Groq API (for LLM classification)
GROQ_API_KEY=gsk_xxxxxxxxxxxxx

# GitHub Integration
GITHUB_ENABLED=true
GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
GITHUB_REPO=YourUsername/specwatch-alerts

# Email Integration (Gmail)
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=sender-email@gmail.com
SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx  # Gmail App Password
EMAIL_FROM=sender-email@gmail.com
EMAIL_TO=receiver-email@gmail.com

# Slack Integration (disabled for now)
SLACK_ENABLED=false
```

**Get API Keys**:
- **Tavily**: https://tavily.com (free tier: 1000 searches/month)
- **Groq**: https://console.groq.com (free tier available)
- **GitHub Token**: https://github.com/settings/tokens (scope: `repo`)
- **Gmail App Password**: https://myaccount.google.com/apppasswords (requires 2FA)

### Add Your First Vendor

```bash
# Add Stripe as a monitored vendor
python3 scripts/add_vendor.py stripe "Stripe"

# Verify configuration
cat specwatch/config/json/vendors.json
```

---

## 📖 Usage

### Run Complete Pipeline

```bash
# Run all stages (Discovery → Alerting)
python3 main.py
```

**Expected runtime**: ~3 minutes for 3 vendors

**What happens**:
1. Discovers official API sources
2. Fetches latest OpenAPI specs
3. Normalizes to canonical format
4. Compares against baseline
5. Classifies changes with LLM
6. Sends alerts for critical changes

### Run Individual Pipelines

```bash
# Discovery only
python3 -m pipelines.discovery_pipeline

# Ingestion only
python3 -m pipelines.ingestion_pipeline

# Normalization only
python3 -m pipelines.normalization_pipeline

# Diff only
python3 -m pipelines.diff_pipeline

# Classification only
python3 -m pipelines.classification_pipeline

# Alerting only
python3 -m pipelines.alerting_pipeline
```

### Test Mode (Alerting)

Validate your GitHub/Email setup without waiting for real changes:

```bash
# Send test alerts using mock data
python3 -m pipelines.alerting_pipeline --test
```

**Expected output**: 3 GitHub issues + 2 emails created using synthetic breaking changes.

---

## 🖥️ Web Dashboard

### Start the Dashboard

```bash
python3 app.py
```

Open browser: **http://localhost:5000**

### Dashboard Features

**Main Dashboard** (`/`)
- Vendor status cards (healthy/warning/critical)
- Recent changes timeline
- Classification statistics
- Pipeline controls in navbar

**Vendor Management** (`/vendors`)
- List all monitored vendors
- Add new vendors
- Remove vendors (with optional storage cleanup)
- Update baseline versions

**Vendor Details** (`/vendors/{vendor}`)
- All detected changes
- Severity breakdown
- LLM reasoning and migration paths
- Version history

**Pipeline Controls** (navbar)
- **Discovery**: Find latest API sources
- **Analysis**: Run ingestion → classification
- **Alerting**: Send alerts for critical changes
- **Full Pipeline**: Run all stages

**Alert Preview**
- Preview GitHub issue format
- Preview email HTML/text
- Send alerts manually
- Test alerting setup

---

## 🔔 Alert Routing

| Severity | GitHub Issue | Email | Why |
|----------|--------------|-------|-----|
| **Breaking** | ✅ | ✅ | Critical - requires immediate action |
| **Deprecation** | ✅ | ❌ | Warning - plan migration |
| **Additive** | ❌ | ✅ | Info - new features available |
| **Minor** | ❌ | ❌ | Logged only |

**Breaking Change Example**:
- Endpoint removed
- Required parameter added
- Parameter type changed
- Response schema changed

**Deprecation Example**:
- Endpoint marked deprecated
- Sunset date announced

**Additive Example**:
- New endpoint added
- Optional parameter added

**Minor Example**:
- Description updated
- Summary changed

---

## 📁 Project Structure

```
specwatch-platform/
├── specwatch/                  # Core library
│   ├── discovery/              # Source discovery
│   ├── ingestion/              # Spec fetching
│   ├── normalization/          # Schema normalization
│   ├── diff/                   # Change detection
│   ├── classification/         # LLM analysis
│   ├── alerting/               # Multi-channel alerts
│   ├── config/                 # Configuration files
│   ├── store/                  # Storage layer
│   └── utils/                  # Shared utilities
├── pipelines/                  # Pipeline orchestration
│   ├── discovery_pipeline.py
│   ├── ingestion_pipeline.py
│   ├── normalization_pipeline.py
│   ├── diff_pipeline.py
│   ├── classification_pipeline.py
│   └── alerting_pipeline.py
├── app/                        # Flask dashboard
│   ├── routes/                 # API endpoints
│   ├── templates/              # HTML templates
│   ├── static/                 # CSS/JS
│   └── utils/                  # Dashboard utilities
├── storage/                    # Runtime data (gitignored)
│   ├── discovery/              # Latest sources
│   ├── raw/                    # Raw specs
│   ├── normalized/             # Canonical schemas
│   ├── diffs/                  # Change detection
│   ├── classified_diffs/       # LLM classifications
│   └── alerts/                 # Alert history
├── scripts/                    # Management scripts
│   ├── add_vendor.py           # Add new vendor
│   ├── remove_vendor.py        # Remove vendor
│   └── update_baseline.py      # Set baseline version
├── main.py                     # Pipeline entry point
├── app.py                      # Dashboard entry point
├── requirements.txt            # Dependencies
├── .env                        # Configuration (create this)
└── README.md                   # This file
```

---

## 🛠️ Configuration Files

All configuration is in `specwatch/config/json/`:

**vendors.json** - Monitored vendors
```json
{
  "vendors": [
    {
      "name": "stripe",
      "display_name": "Stripe",
      "enabled": true
    }
  ]
}
```

**vendor_registry.json** - Trusted domains
```json
{
  "vendors": {
    "stripe": {
      "trusted_domains": [
        "stripe.com",
        "github.com/stripe"
      ]
    }
  }
}
```

**vendor_specs.json** - OpenAPI spec URLs
```json
{
  "stripe": {
    "openapi_url": "https://raw.githubusercontent.com/stripe/openapi/master/latest/openapi.spec3.sdk.yaml"
  }
}
```

**discovery_queries.json** - Search templates
```json
{
  "docs": "{vendor} API documentation",
  "openapi": "{vendor} OpenAPI specification GitHub",
  "changelog": "{vendor} API changelog"
}
```

---

## 🧪 Testing

### Test Alerting Setup

```bash
# Send test alerts (uses mock data)
python3 -m pipelines.alerting_pipeline --test
```

**Verifies**:
- GitHub token works
- Email SMTP credentials valid
- Alert formatting correct
- Multi-channel routing

### Run Unit Tests

```
Run: python3 -m scripts.test_diff_engine
```

---

## 🔧 Management Scripts

### Add Vendor

```bash
python3 scripts/add_vendor.py twilio "Twilio"
```

**What it does**:
- Updates `vendors.json`
- Updates `vendor_registry.json`
- Updates `vendor_specs.json`
- Creates initial discovery entry

### Remove Vendor

```bash
python3 scripts/remove_vendor.py stripe
```

**Interactive prompts**:
1. Confirm removal from config
2. Optionally clean storage (discovery, specs, diffs, etc.)

### Update Baseline

```bash
# Set specific version as baseline
python3 scripts/update_baseline.py stripe 2026-03-29T20-27-50

# List available versions
python3 scripts/list_versions.py stripe
```

**Why update baseline?**
- You deployed a new API version to production
- You want to track changes from a specific point
- You need to reset after major API migration

---

## 💡 How It Works

### 1. Discovery

Uses **Tavily search API** to find official sources:
- Searches for "{vendor} API documentation"
- Searches for "{vendor} OpenAPI specification GitHub"
- Resolves best URL from trusted domains
- Validates URLs are reachable

### 2. Ingestion

Fetches OpenAPI specifications:
- Resolves GitHub repos to raw spec URLs
- Downloads YAML/JSON specs
- Computes SHA-256 hash for deduplication
- Stores versioned snapshots

### 3. Normalization

Converts to canonical format:
- Parses YAML/JSON
- Extracts endpoints (method + path)
- Extracts parameters (location + name + type)
- Sorts deterministically to prevent false positives
- Stores with `baseline.json` and `latest.json` symlinks

### 4. Diff

Detects changes:
- Compares `baseline.json` vs `latest.json`
- Uses set operations for efficiency
- Tracks: added/removed/modified endpoints
- Tracks: added/removed/modified parameters
- Stores structured diff results

### 5. Classification

LLM-based severity analysis:
- Uses Groq's `gpt-oss-120b` model
- Evaluates each change with full context
- Assigns severity: breaking/deprecation/additive/minor
- Provides reasoning and migration path
- Confidence score (0.0 - 1.0)

### 6. Alerting

Multi-channel notifications:
- **Breaking**: GitHub issue + Email
- **Deprecation**: GitHub issue only
- **Additive**: Email only
- **Minor**: No alerts (logged)

---

## 🎛️ Environment Variables

```bash
# Required
TAVILY_API_KEY=tvly-xxxxx           # Tavily search
GROQ_API_KEY=gsk_xxxxx              # LLM classification

# GitHub (optional but recommended)
GITHUB_ENABLED=true
GITHUB_TOKEN=ghp_xxxxx
GITHUB_REPO=username/repo-name

# Email (optional but recommended)
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=sender@gmail.com
SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx  # App password
EMAIL_FROM=sender@gmail.com
EMAIL_TO=receiver@gmail.com

# Slack (optional)
SLACK_ENABLED=false
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx
```

---

## 📈 Performance

**Typical run (3 vendors)**:
- Discovery: ~60 seconds
- Ingestion: ~10 seconds (with hash deduplication)
- Normalization: <1 second (hash-based skip)
- Diff: <1 second
- Classification: ~1.5 seconds per change
- Alerting: <1 second

**Total**: ~2-3 minutes for full pipeline

**Optimizations**:
- Hash-based deduplication (ingestion + normalization)
- Skips LLM calls for unchanged specs
- Skips alerts for no critical changes
- Background execution in dashboard

---

## 💰 Cost Estimate

**Free Tier Usage**:
- Tavily: 1000 searches/month (3 vendors × daily = 90/month)
- Groq: Free tier covers expected usage
- GitHub API: Free (5000 requests/hour)
- Gmail SMTP: Free

**Paid Usage** (if scaling):
- Tavily: $0.001 per search
- Groq: Pay-per-token (very low cost)

**Estimated monthly cost**: $0 (within free tiers)

---

## 🐛 Troubleshooting

### Pipelines Don't Run from UI

**Symptom**: Buttons click but nothing happens

**Fix**: Make sure you're using `python3 app.py` (not `python`)

**Verification**:
```bash
# Check which Python Flask is using
import sys
print(sys.executable)
# Should show: /path/to/specwatchenv/bin/python3
```

### GitHub Alerts Fail

**Error**: `401 Bad credentials`

**Fix**:
1. Generate new token: https://github.com/settings/tokens
2. Scope must include `repo`
3. Update `.env` with new token

### Email Alerts Fail

**Error**: `535 Username and Password not accepted`

**Fix**:
1. Enable 2FA on Google Account
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Use 16-character app password (NOT regular password)
4. Update `.env`

### No Alerts Sent

**Symptom**: `Alerting complete: 0/0 alert(s) sent`

**Reason**: No breaking/deprecation changes detected (this is normal!)

**Verify**: Run test mode to check setup:
```bash
python3 -m pipelines.alerting_pipeline --test
```

### Module Not Found

**Error**: `ModuleNotFoundError: No module named 'specwatch'`

**Fix**:
```bash
# Make sure venv is activated
source specwatchenv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python3 -c "import specwatch; print('OK')"
```

---

## 🤝 Contributing

Contributions welcome! Areas for improvement:

**Features**:
- Scheduled pipeline runs (cron)
- Response schema diffing
- Semantic endpoint matching
- Alert acknowledgment system
- Historical trend charts

**Integrations**:
- Jira integration
- PagerDuty integration
- Datadog metrics

**Testing**:
- More comprehensive unit tests
- Integration tests
- Performance benchmarks

---

## 📞 Support

- **Issues**: https://github.com/Adityajha0808/specwatch-platform/issues
- **Docs**: See `PROGRESS.md` for detailed implementation notes
- **Email**: jhaaditya757@gmail.com

---

**Built with ❤️ by developers, for developers.**

Monitor your APIs. Sleep better. 😴
