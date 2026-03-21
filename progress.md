# SpecWatch – Development Progress

## Overview

SpecWatch is a developer tool designed to monitor external API providers (e.g., Stripe, Twilio, OpenAI) and detect changes that may introduce breaking contract changes for dependent services.
The system discovers authoritative API sources (documentation, OpenAPI specs, changelogs) and prepares them for further analysis.


## Architecture
Discovery → Ingestion → Normalization → Diff Engine

---

# Day 1 – Project Setup

### Repository Structure

Created the initial project structure separating core modules and pipelines.

Key directories:

* `specwatch/` – core library modules
* `pipelines/` – workflow execution logic
* `storage/` – runtime data storage

### Core Modules Created

**Discovery**

* `tavily_client.py` – wrapper for Tavily search API
* `source_resolver.py` – resolves best source from search results

**Configuration**

* `config_loader.py` – loads vendor and query configuration
* `config_validator.py` – validates configuration integrity

**Storage**

* `raw_discovery_store.py` – stores versioned discovery outputs
* `discovery_store.py` – stores latest discovery snapshot

**Utilities**

* `logger.py` – centralized logging
* `url_validator.py` – validates reachable URLs

### Entry Point

`main.py` added as the system entrypoint:

```python
from pipelines.discovery_pipeline import run_discovery

if __name__ == "__main__":
    run_discovery()
```

---

# Day 2 – Discovery Pipeline

Implemented the **source discovery pipeline** responsible for identifying official API sources.

### Discovery Workflow

The pipeline performs the following steps:

1. Load vendor configurations
2. Validate configuration files
3. Generate discovery queries
4. Run Tavily search queries
5. Resolve trusted sources
6. Validate URLs
7. Store discovery results

### Config Driven Design

Discovery behavior is controlled through configuration files:

* `vendors.json`
* `vendor_registry.json`
* `discovery_queries.json`

This allows vendors to be added without modifying core code.

### Vendor Onboarding

Implemented a vendor onboarding script allowing new vendors to be registered dynamically by updating configuration files.

* `scripts/add_vendor.py`

### Source Trust Filtering

Search results are filtered using trusted vendor domains defined in the registry configuration to avoid unreliable sources.

### URL Validation

Candidate URLs are validated to ensure they return valid HTTP responses before being accepted as official sources.

### Logging

Structured logging was implemented across modules to trace pipeline execution and discovery results.

---

## Discovery Output

Discovery results are stored in two locations:

**Versioned Raw Storage**

```
storage/raw/discovery
```

Stores timestamped discovery results for historical tracking.

Example:

```
stripe_20260310_193512.json
```

---

**Latest Snapshot Storage**

```
storage/discovery/
```

Maintains the most recent discovery state per vendor.

Example:

```
openai.json
```

---

### Example Discovery Output

```json
{
  "vendor": "openai",
  "api": "OpenAI",
  "discovered_at": "2026-03-10T20:10:21Z",
  "sources": {
    "docs": "https://developers.openai.com/api/docs/concepts/",
    "openapi": "https://github.com/openai/openai-openapi",
    "changelog": "https://developers.openai.com/api/docs/changelog/"
  }
}
```

---

# Day 3 – Ingestion Pipeline

* Implemented the ingestion layer responsible for retrieving actual API specifications from the sources discovered during the discovery stage.

* While the discovery pipeline identifies official vendor sources, the ingestion pipeline retrieves the actual OpenAPI specifications that describe the API contract.

* These specifications form the foundation for later analysis and change detection.

## Ingestion Workflow

- The ingestion pipeline performs the following steps:

* Load discovery results from storage

* Extract OpenAPI source URLs

* Resolve the actual specification location

* Fetch the OpenAPI specification

* Store the specification for future analysis

* The pipeline reads previously discovered vendor sources and retrieves the API specification files directly from those locations.

### HTTP Client Utility

- A reusable HTTP client utility was implemented to standardize external requests across the system.

* File:

specwatch/utils/http_client.py

* Responsibilities:

Perform HTTP GET requests

* Handle timeouts

* Handle connection errors

* Return response content safely

This utility will be reused across future modules that require external data retrieval.

### OpenAPI Source Resolver

- Some vendors publish OpenAPI specifications through indirect sources such as GitHub repositories or documentation pages.

- A resolver module was implemented to determine the actual specification file location from a discovered source.

* File:

specwatch/ingestion/openapi_resolver.py

* Responsibilities:

- Resolve GitHub repository sources via different strategies

- Resolve raw specification file URLs

- Validate reachable specification locations

- Specification Fetcher

The specification fetcher retrieves the OpenAPI specification content from the resolved source URL.

* File:

specwatch/ingestion/spec_fetcher.py

* Responsibilities:

- Download OpenAPI specification files

- Handle both JSON and YAML formats

- Validate response content

- Return raw specification data

* Specification Storage

- Downloaded OpenAPI specifications are stored in the storage layer for later processing.

* File:

specwatch/storage/spec_store.py

- Specifications are stored using timestamped filenames to preserve version history.

- Storage location:

storage/raw/raw_specs/

- Example files:

openai_openapi_2026-03-14T20-21-12.yaml
twilio_openapi_2026-03-14T20-21-12.yaml
stripe_openapi_2026-03-14T20-21-15.yaml

This versioned storage allows SpecWatch to track API contract changes over time.

## Ingestion Pipeline

- The ingestion pipeline orchestrates the ingestion process.

- File:

pipelines/ingestion_pipeline.py

* Responsibilities:

- Load discovery output files

- Resolve OpenAPI specification sources

- Fetch specification files

- Store versioned specifications

The ingestion pipeline processes each vendor independently and logs execution progress for traceability.

- Updated System Entry Point

The system entry point was updated to run both discovery and ingestion pipelines.

main.py

from pipelines.discovery_pipeline import run_discovery
from pipelines.ingestion_pipeline import run_ingestion

if __name__ == "__main__":

    run_discovery()
    run_ingestion()

Running the system now performs both stages sequentially.

python main.py
Storage State After Ingestion

- The system now maintains three key storage layers:

Discovery Snapshot
storage/discovery/

* Stores the latest discovered sources per vendor.

Raw Discovery History
storage/raw/discovery/

* Stores versioned discovery results for historical reference.

Raw API Specifications
storage/raw/specs/

* Stores timestamped OpenAPI specifications fetched from vendor sources.


## Ingestion Issue Encountered – OpenAPI Resolution

During initial execution of the ingestion pipeline, the system failed to download OpenAPI specifications for some vendors.

Example logs indicated repeated `HTTP 404` responses when attempting to fetch specification files:


Failed to fetch URL:
https://raw.githubusercontent.com/stripe/openapi/master/openapi.yaml


The ingestion resolver initially assumed a fixed OpenAPI file structure when converting GitHub repository URLs into raw specification URLs.

For example:

github.com/vendor/repo → raw.githubusercontent.com/vendor/repo/master/openapi.yaml

However, in practice API vendors structure their repositories differently.

Example cases:

| Vendor | Repository | Actual Spec Location |
|------|------|------|
| Stripe | stripe/openapi | `openapi/spec3.yaml` |
| Twilio | twilio/openapi | `openapi/spec3.yaml` |
| OpenAI | openai/openai-openapi | `openapi.yaml` on `main` branch |

Because the resolver assumed a single filename and branch (`master`), it generated invalid URLs which resulted in failed downloads.

---

## Resolution

The OpenAPI resolver was redesigned to support **dynamic specification discovery within GitHub repositories**.

The resolver now attempts multiple common OpenAPI file paths and repository branches before resolving a valid specification.

Example paths checked:

openapi.yaml
openapi.yml
swagger.yaml
swagger.yml
openapi/spec3.yaml
spec/openapi.yaml

Example branches checked:

main
master

The resolver iterates through these combinations and validates the first reachable specification file using the HTTP client utility.

This approach significantly improves compatibility with different repository layouts used by API providers.

---

## Result

After implementing the enhanced resolver logic:

- OpenAPI specifications are successfully resolved for vendors hosted on GitHub
- The ingestion pipeline can reliably fetch and store specification files
- The system becomes resilient to variations in repository structure
- Recursive depth search to resolve missing specs inside nested folders.

Downloaded specifications are now stored in the versioned storage layer:

storage/raw/raw_specs/

These files represent the **raw API contract snapshots** that will be used for further schema parsing and change detection in subsequent stages of the system.

---

# Day 4 – Normalization Pipeline

Implemented the **normalization layer** responsible for converting raw OpenAPI specifications into a unified canonical format.

Raw OpenAPI specifications vary significantly across vendors in terms of structure, format (YAML vs JSON), and OpenAPI version. The normalization layer standardizes these heterogeneous inputs into a consistent schema that enables reliable change detection.

## Normalization Workflow

The normalization pipeline performs the following steps:

1. Load raw OpenAPI specifications
2. Parse YAML or JSON format
3. Validate OpenAPI version
4. Extract base URL from servers field
5. Extract all API endpoints with unique identifiers
6. Extract parameters from each operation
7. Apply deterministic sorting (endpoints by path+method, parameters by location+name)
8. Compute SHA-256 hash for deduplication
9. Check if normalization needed (compare hash with latest snapshot)
10. Build canonical schema representation
11. Store normalized snapshot with versioning
12. Update symlinks (baseline and latest)

### Canonical Schema Design

A simplified canonical schema was defined to capture essential API contract elements needed for change detection.

File:

```
schemas/api_schema.json
```

The schema includes:

**Metadata**
- Vendor name
- Normalization timestamp
- Source file hash
- Schema version

**Endpoints**
- Unique endpoint identifier (e.g., `POST:/v1/customers`)
- HTTP method (GET, POST, PUT, DELETE, PATCH)
- Path (e.g., `/v1/customers`)
- Summary/description
- Deprecation status
- Authentication requirement
- Request body requirement
- Response status codes (e.g., `["200", "400", "401"]`)

**Parameters**
- Parameter name
- Location (path, query, header, body)
- Type (string, integer, boolean)
- Required flag
- Description

This schema excludes deep response schemas and complex nested structures to keep Phase 1 simple and focused on detecting structural changes.

### OpenAPI Parser

The parser module handles loading and validating OpenAPI specifications from YAML or JSON files.

File:

```
specwatch/normalization/parser.py
```

Responsibilities:
- Detect file format (YAML vs JSON)
- Parse specification content
- Validate OpenAPI version (supports 3.x)
- Extract base URL from servers array
- Handle parsing errors gracefully

The parser supports both YAML and JSON formats, making it compatible with different vendor publishing practices.

### Endpoint Extractor

The extractor module traverses the OpenAPI `paths` object and extracts endpoint details.

File:

```
specwatch/normalization/extractor.py
```

Responsibilities:
- Iterate through all paths and operations
- Generate unique endpoint identifiers (`{METHOD}:{path}`)
- Extract parameters from multiple locations (path, query, header, body)
- Detect deprecated endpoints
- Determine authentication requirements
- Handle request body schema extraction
- Apply deterministic sorting (endpoints by path+method, parameters by location+name)

The extractor focuses on top-level parameter extraction, avoiding deep nested object traversal to maintain simplicity in Phase 1.

**Critical implementation detail**: Endpoints and parameters are sorted deterministically to prevent false positives in the diff engine. Without sorting, the same API structure could appear as "changed" simply because items were ordered differently.

### Normalizer Orchestrator

The normalizer orchestrates the parsing and extraction process and builds the final canonical format.

File:

```
specwatch/normalization/normalize.py
```

Responsibilities:
- Coordinate parser and extractor modules
- Compute SHA-256 hash of source file for change detection
- Compare hash with latest snapshot to skip redundant normalization
- Build canonical JSON structure with sorted keys
- Store normalized snapshots with timestamps in snapshots directory
- Maintain symlinks for baseline and latest versions
- Track schema version for normalization logic upgrades

The normalizer generates a SHA-256 hash (truncated to 16 characters) of the raw specification file. This hash serves dual purposes:

1. **Deduplication**: If the hash matches the latest snapshot's source hash, normalization is skipped entirely
2. **Integrity verification**: The hash is stored in snapshot metadata for auditing and debugging

**Two-layer deduplication strategy**:
- **Layer 1 (Ingestion)**: Prevents duplicate raw spec files when API content is unchanged
- **Layer 2 (Normalization)**: Prevents duplicate normalized snapshots even when normalization is run manually or retried

## Normalized Storage Strategy

Normalized specifications are stored using a versioned snapshot approach with symlink references.

Storage location:

```
storage/normalized/{vendor}/
```

Directory structure per vendor:

```
storage/normalized/stripe/
├── snapshots/
│   ├── 2024-01-10T09:00:00Z.json
│   ├── 2024-01-12T09:00:00Z.json
│   └── 2024-01-15T09:00:00Z.json
├── baseline.json -> snapshots/2024-01-10T09:00:00Z.json
└── latest.json   -> snapshots/2024-01-15T09:00:00Z.json
```

**Snapshots directory**

Contains all historical normalized versions with ISO timestamp filenames. This preserves full version history for auditing and comparison. Each snapshot is immutable and represents the complete API state at that moment.

**baseline.json symlink**

Points to the established stable version used as the comparison baseline. This represents the API version currently deployed in production systems. The baseline is:
- Set automatically during first normalization
- Updated manually using `update_baseline.py` when production upgrades to a newer API version
- Used by the diff engine to detect changes relative to what's currently in use

**latest.json symlink**

Points to the most recently normalized snapshot, representing the current state of the vendor's API. This symlink is:
- Updated automatically on every normalization run
- Used by the diff engine to compare against baseline
- Provides O(1) access without directory scanning or sorting logic

**Why symlinks?**

Symlinks provide storage efficiency and clean abstraction:
- **No data duplication**: Snapshots stored once, referenced via lightweight pointers (4 bytes vs 500KB)
- **Fast access**: Direct file reference without directory listing or sorting
- **Atomic updates**: Changing a symlink is instant and atomic
- **Clean code**: Diff engine reads `baseline.json` and `latest.json` without knowing which specific snapshots they point to

## Version Selection Logic

The normalization pipeline intelligently selects the latest raw specification when multiple versions exist.

Selection criteria:
- Finds all raw specs matching vendor pattern (`{vendor}_openapi_*.yaml` or `.json`)
- Sorts by file modification time (newest first)
- Selects the most recently modified file

This ensures the pipeline always normalizes the freshest data without manual intervention.

## Normalization Pipeline

The normalization pipeline orchestrates the full normalization workflow.

File:

```
pipelines/normalization_pipeline.py
```

Responsibilities:
- Auto-discover vendors from raw specs directory
- Normalize latest specification for each vendor
- Update symlinks (baseline and latest)
- Log detailed progress and debug information
- Handle normalization failures gracefully

The pipeline can process all vendors automatically or accept specific vendor names as arguments:

```bash
# Normalize all vendors
python -m pipelines.normalization_pipeline

# Normalize specific vendors
python -m pipelines.normalization_pipeline --vendors stripe twilio

# Enable debug logging
python -m pipelines.normalization_pipeline --debug
```

### Updated System Entry Point

The system entry point was updated to include the normalization stage.

```python
from pipelines.discovery_pipeline import run_discovery
from pipelines.ingestion_pipeline import run_ingestion
from pipelines.normalization_pipeline import run_normalization

if __name__ == "__main__":
    run_discovery()
    run_ingestion()
    run_normalization()
```

Running the system now executes all three stages sequentially:

```bash
python main.py
```

## Structured Logging

Comprehensive debug logging was added across all normalization modules to enable detailed pipeline tracing.

Log levels used:
- `DEBUG` – Step-by-step execution details
- `INFO` – Major milestones and success events
- `WARNING` – Non-critical issues (e.g., missing fields)
- `ERROR` – Critical failures requiring attention

Example log output:

```
[INFO] normalization_pipeline_started vendors=['stripe', 'twilio', 'openai']
[DEBUG] normalize_vendor_started vendor=stripe
[DEBUG] searching_raw_specs vendor=stripe raw_dir=storage/raw/raw_specs
[INFO] found_raw_spec vendor=stripe spec_file=stripe_openapi_2024-01-15.yaml
[DEBUG] step_1_parsing vendor=stripe
[DEBUG] parsing_as_yaml filepath=storage/raw/raw_specs/stripe_openapi_2024-01-15.yaml
[INFO] yaml_parsed_successfully top_level_keys=['openapi', 'info', 'servers', 'paths']
[DEBUG] step_2_hashing vendor=stripe
[DEBUG] step_3_base_url vendor=stripe
[INFO] base_url_extracted base_url=https://api.stripe.com
[DEBUG] step_4_endpoints vendor=stripe
[INFO] endpoints_extraction_complete total_endpoints=450
[INFO] normalization_complete vendor=stripe endpoint_count=450
[INFO] snapshot_stored vendor=stripe snapshot_path=storage/normalized/stripe/snapshots/2024-01-15.json
[INFO] vendor_normalized_success vendor=stripe status=success
```

This structured logging makes debugging and monitoring significantly easier during development and production operations.

## Example Normalized Output

A normalized Stripe specification contains metadata and extracted endpoint details:

```json
{
  "metadata": {
    "vendor": "stripe",
    "normalized_at": "2024-01-15T10:00:00Z",
    "source_file": "stripe_openapi_2024-01-15.yaml",
    "source_hash": "a1b2c3d4e5f6g7h8",
    "schema_version": "1.0",
    "openapi_version": "3.0.0"
  },
  "base_url": "https://api.stripe.com",
  "endpoints": [
    {
      "id": "POST:/v1/customers",
      "path": "/v1/customers",
      "method": "POST",
      "summary": "Create a customer",
      "deprecated": false,
      "parameters": [
        {
          "name": "email",
          "location": "body",
          "required": false,
          "type": "string",
          "description": "Customer's email address"
        }
      ],
      "request_body_required": false,
      "auth_required": true,
      "responses": ["200", "400", "401"]
    }
  ]
}
```

This format is significantly smaller than the raw OpenAPI spec (typically 60-70% reduction) while preserving all information needed for change detection.

## Verification Utilities

Helper scripts were created to inspect and verify normalized outputs.

**List all versions for a vendor:**

```bash
python scripts/list_versions.py stripe
```

**Update baseline to specific snapshot:**

```bash
python scripts/update_baseline.py stripe 2024-01-20T09:00:00Z
```

These utilities help validate that normalization is working correctly and provide quick insights into stored snapshots.

## Key Implementation Decisions

Several critical design choices were made during Day 4 implementation:

### Deterministic Output

**Problem**: Non-deterministic JSON output would cause false positives in diff detection.

**Solution**: Applied consistent sorting at two levels:
- Endpoints sorted by `(path, method)`
- Parameters sorted by `(location, name)`
- JSON keys sorted with `sort_keys=True`

This ensures identical API structures produce byte-for-byte identical normalized outputs.

### Endpoint Identity

**Problem**: Diff engine needs unambiguous way to match endpoints across versions.

**Solution**: Generate explicit `id` field using format `{METHOD}:{path}` (e.g., `POST:/v1/customers`). This provides stable identity even if other fields change.

### Two-Layer Deduplication

**Problem**: Running normalization multiple times on unchanged specs creates duplicate snapshots.

**Solution**: Implemented defense-in-depth approach:
- **Layer 1 (Ingestion)**: Skip fetching if raw spec content unchanged (SHA-256 hash comparison)
- **Layer 2 (Normalization)**: Skip normalizing if source hash matches latest snapshot

This prevents duplicates even when pipeline phases run independently or are manually retried.

### Symlink Strategy

**Problem**: Code needs fast access to "baseline" and "latest" snapshots without knowing specific timestamps.

**Solution**: Use symlinks as pointers:
- `baseline.json` → production-approved snapshot
- `latest.json` → most recent snapshot

Benefits:
- No data duplication (4 bytes vs 500KB per file)
- O(1) access without directory scanning
- Clean abstraction (diff engine doesn't need to know snapshot naming)

### Schema Versioning

**Problem**: Improving normalization logic would require re-processing all historical specs.

**Solution**: Track `schema_version` in metadata. When normalization logic improves, increment version and re-normalize even if source hash unchanged. This allows controlled schema evolution.

---

# Current Status

At the end of Day 4:

**Discovery pipeline** – Identifies official API sources  -- Implemented
**Ingestion pipeline** – Fetches raw OpenAPI specifications  -- Implemented
**Normalization pipeline** – Converts specs to canonical format  -- Implemented
**Diff engine** – Next: Detect changes between versions  
**Classification** – Next: Use LLM to classify change severity  
**Alerting** – Next: Send notifications for breaking changes  

The system now maintains a complete pipeline from source discovery to normalized schema storage:

```
Discovery → Ingestion → Normalization → [Diff] → [Classification] → [Alerting]
```

**Storage state:**

```
storage/
├── discovery/              # Latest discovery snapshots
├── raw/
│   ├── discovery/          # Versioned discovery history
│   └── raw_specs/          # Raw OpenAPI specifications
└── normalized/             # Normalized API schemas
    ├── stripe/
    │   ├── snapshots/      # All versions
    │   ├── baseline.json   # Stable reference
    │   └── latest.json     # Current state
    ├── twilio/
    └── openai/
```

The next stage will implement the **diff engine** to compare normalized snapshots and detect structural changes in API contracts. This will enable the system to identify when vendors introduce breaking changes, deprecations, or new features.
