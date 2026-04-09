# SpecWatch – Development Progress

## Overview

SpecWatch is a developer tool designed to monitor external API providers (e.g., Stripe, Twilio, OpenAI) and detect changes that may introduce breaking contract changes for dependent services.
The system discovers authoritative API sources (documentation, OpenAPI specs, changelogs) and prepares them for further analysis.


## Architecture
Discovery → Ingestion → Normalization → Diff Engine

---

# STEP 1 – Project Setup

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

# STEP 2 – Discovery Pipeline

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

# STEP 3 – Ingestion Pipeline

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

* When Ingestion re-runs, it computes the hash (SHA256 hashing) of new raw spec file, and compares against the hash of already stored spec file. If it matches, it skips saving the new raw spec file while keeping the old one, to avoid de-duplication. Only when hash is different, the new raw spec file is stored.

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

specwatch/store/spec_store.py

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

# STEP 4 – Normalization Pipeline

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

The hash identification for a normalized snapshot is saved inside its metadata.

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
│   ├── 2026-01-10T09:00:00Z.json
│   ├── 2026-01-12T09:00:00Z.json
│   └── 2026-01-15T09:00:00Z.json
├── baseline.json -> snapshots/2026-01-10T09:00:00Z.json
└── latest.json   -> snapshots/2026-01-15T09:00:00Z.json
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
python -m pipelines.normalization_pipeline --vendors stripe

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
[INFO] found_raw_spec vendor=stripe spec_file=stripe_openapi_2026-01-15.yaml
[DEBUG] step_1_parsing vendor=stripe
[DEBUG] parsing_as_yaml filepath=storage/raw/raw_specs/stripe_openapi_2026-01-15.yaml
[INFO] yaml_parsed_successfully top_level_keys=['openapi', 'info', 'servers', 'paths']
[DEBUG] step_2_hashing vendor=stripe
[DEBUG] step_3_base_url vendor=stripe
[INFO] base_url_extracted base_url=https://api.stripe.com
[DEBUG] step_4_endpoints vendor=stripe
[INFO] endpoints_extraction_complete total_endpoints=450
[INFO] normalization_complete vendor=stripe endpoint_count=450
[INFO] snapshot_stored vendor=stripe snapshot_path=storage/normalized/stripe/snapshots/2026-01-15.json
[INFO] vendor_normalized_success vendor=stripe status=success
```

This structured logging makes debugging and monitoring significantly easier during development and production operations.

## Example Normalized Output

A normalized Stripe specification contains metadata and extracted endpoint details:

```json
{
  "metadata": {
    "vendor": "stripe",
    "normalized_at": "2026-01-15T10:00:00Z",
    "source_file": "stripe_openapi_2026-01-15.yaml",
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
python scripts/update_baseline.py stripe 2026-01-20T09:00:00Z
```

These utilities help validate that normalization is working correctly and provide quick insights into stored snapshots.

## Key Implementation Decisions

Several critical design choices were made during STEP 4 implementation:

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

# STEP 5 – Diff Engine Pipeline

Implemented the **diff engine** responsible for comparing normalized snapshots and detecting API changes.

The diff engine compares baseline and latest normalized snapshots to identify structural changes in API contracts, including endpoint additions/removals, parameter modifications, and metadata changes.

## Diff Engine Workflow

The diff engine performs the following steps:

1. Load baseline and latest normalized snapshots
2. Compare metadata (base URL, OpenAPI version)
3. Build endpoint maps by unique endpoint ID
4. Detect added/removed/modified endpoints using set operations
5. For common endpoints, compare field changes (deprecated, auth_required, responses)
6. Build parameter maps by (location, name) tuple
7. Detect added/removed/modified parameters
8. Compare parameter fields (type, required, location)
9. Build structured diff output with change classifications
10. Store diff results with version timestamps

## Implementation Architecture

### Diff Models

Type-safe Pydantic models define the diff structure:

**File**: `specwatch/diff/diff_models.py`

Models include:
- `ParameterChange` - Represents parameter-level changes (added/removed/type changed/requirement changed)
- `EndpointFieldChange` - Represents endpoint field changes (deprecated, auth_required, responses)
- `EndpointChange` - Represents endpoint-level changes with nested parameter changes
- `MetadataChange` - Represents API metadata changes (base_url)
- `DiffSummary` - Summary statistics (counts of each change type)
- `APIDiff` - Complete diff with metadata, summary, and detailed changes

### Diff Utilities

Helper functions for efficient comparison:

**File**: `specwatch/diff/diff_utils.py`

Functions include:
- `build_endpoint_map()` - Map endpoints by ID for O(1) lookup
- `build_parameter_map()` - Map parameters by (location, name) for O(1) lookup
- `compare_parameter_fields()` - Deep field comparison for parameters
- `compare_endpoint_fields()` - Field comparison for endpoints (excluding parameters)
- `is_breaking_change()` - Heuristic classifier for Phase 1 (Later, will use LLM)

### Diff Engine Core Logic

**File**: `specwatch/diff/diff_engine.py`

Core functions:
- `compute_diff()` - Main entry point that orchestrates full diff computation
- `_diff_metadata()` - Compare metadata fields (base_url changes)
- `_diff_endpoints()` - Compare endpoint arrays using set operations
- `_diff_parameters()` - Compare parameter arrays for common endpoints

**Comparison Strategy**:
- Uses endpoint IDs (`POST:/v1/customers`) for unambiguous matching
- Uses (location, name) tuples for parameter matching
- Applies set operations for efficient added/removed detection
- Deep field comparison for modified items

### Diff Storage

**File**: `specwatch/store/diff_store.py`

Storage abstraction supporting both test and production modes:
- `store_diff()` - Store diff results with timestamped filenames
- `load_diff()` - Load diff results by filename
- `get_latest_diff()` - Retrieve most recent diff for a vendor

**Filename format**: `diff_{baseline_ts}_to_{latest_ts}.json`

## Diff Pipeline Orchestration

**File**: `pipelines/diff_pipeline.py`

The diff pipeline supports two modes:

### Test Mode
```bash
python -m pipelines.diff_pipeline --test-mode
```

**Input**: `test/normalized_output/{vendor}/baseline.json` and `latest.json`  
**Output**: `test/diff_output/{vendor}/diff_*.json`

Uses synthetic snapshots with known changes for testing and validation.

### Production Mode
```bash
python -m pipelines.diff_pipeline
```

**Input**: `storage/normalized/{vendor}/baseline.json` and `latest.json`  
**Output**: `storage/diffs/{vendor}/diff_*.json`

Uses real normalized snapshots from production storage.

**Pipeline features**:
- Auto-discovers vendors from input directory
- Processes each vendor independently
- Logs detailed summary for each diff
- Returns success/failure status for all vendors

## Test Infrastructure

### Synthetic Test Data

**Script**: `scripts/create_normalized_test_snapshots.py`

Generates synthetic baseline and latest snapshots with intentional differences:

**Stripe** (endpoint-level changes):
- 1 endpoint added: `POST:/v1/payment_intents`
- 1 endpoint removed: `POST:/v1/charges`
- 1 endpoint deprecated: `GET:/v1/customers`

**Twilio** (parameter-level changes):
- Parameter type changed: `Body` (string → object) - BREAKING
- Parameter requirement changed: `From` (required: true → false)
- Parameter added: `StatusCallback` (optional)
- Parameter removed: `MediaUrl`

**OpenAI** (metadata + mixed changes):
- Base URL changed: `/v1` → `/v2` - BREAKING
- Endpoint deprecated: `POST:/completions`
- Auth requirement changed: `auth_required` (false → true) - BREAKING
- Response codes changed: Added `429` rate limit status

### Unit Tests

**File**: `scripts/test_diff_engine.py`

Test cases validate:
- Snapshot loading functionality
- Stripe diff detection (endpoint changes)
- Twilio diff detection (parameter changes)
- OpenAI diff detection (metadata changes)
- No-change scenario (baseline == latest)
- JSON serialization/deserialization

## Diff Output Structure

Example diff output for Stripe:

```json
{
  "vendor": "stripe",
  "baseline_version": "2026-01-10T09:00:00Z",
  "latest_version": "2026-01-20T09:00:00Z",
  "compared_at": "2026-03-21T10:00:00Z",
  "has_changes": true,
  "summary": {
    "endpoints_added": 1,
    "endpoints_removed": 1,
    "endpoints_modified": 0,
    "endpoints_deprecated": 1,
    "parameters_added": 0,
    "parameters_removed": 0,
    "parameters_modified": 0,
    "metadata_changes": 0
  },
  "metadata_changes": [],
  "endpoint_changes": [
    {
      "change_type": "endpoint_added",
      "endpoint_id": "POST:/v1/payment_intents",
      "path": "/v1/payment_intents",
      "method": "POST",
      "summary": "Create a payment intent"
    },
    {
      "change_type": "endpoint_removed",
      "endpoint_id": "POST:/v1/charges",
      "path": "/v1/charges",
      "method": "POST",
      "summary": "Create a charge (old API)"
    },
    {
      "change_type": "endpoint_deprecated",
      "endpoint_id": "GET:/v1/customers",
      "path": "/v1/customers",
      "method": "GET",
      "field_changes": [
        {
          "field_name": "deprecated",
          "old_value": false,
          "new_value": true
        }
      ]
    }
  ]
}
```

## Key Implementation Decisions

### Endpoint Matching Strategy

**Problem**: Need reliable way to match endpoints across versions.

**Solution**: Use explicit endpoint IDs generated during normalization (`POST:/v1/customers`). This provides stable identity even when other fields change.

**Benefit**: Unambiguous matching via set operations, O(1) lookup performance.

### Parameter Comparison Strategy

**Problem**: Parameters are arrays without unique identifiers.

**Solution**: Build map using composite key `(location, name)`. For example:
- `("body", "email")` → parameter details
- `("query", "limit")` → parameter details

**Benefit**: Efficient parameter matching and change detection.

### Change Type Granularity

**Decision**: Track specific change types for precise classification.

**Change types tracked**:
- Endpoint level: `endpoint_added`, `endpoint_removed`, `endpoint_deprecated`, `endpoint_modified`
- Parameter level: `parameter_added`, `parameter_removed`, `parameter_type_changed`, `parameter_requirement_changed`
- Metadata level: `base_url` changes

**Benefit**: Later, LLM classifier can make context-aware decisions based on specific change types.

### Test Mode vs Production Mode

**Problem**: Need to test diff engine with controlled data before using real snapshots.

**Solution**: Implement `--test-mode` flag:
- Test mode: Uses `test/normalized_output/` with synthetic data
- Production mode: Uses `storage/normalized/` with real snapshots

**Benefit**: Safe testing with known expected changes, validation before production use.

### Diff Storage Approach

**Decision**: Store every diff result (even when no changes detected).

**Rationale**: 
- Provides audit trail ("we checked on X date, found no changes")
- Distinguishes "never checked" from "checked, no changes"
- Storage cost is negligible (JSON files are small)

**Format**: Timestamped files like `diff_2026-01-10_to_2026-01-20.json`

## Integration with Main Pipeline

Updated `main.py` to include diff pipeline:

```python
from pipelines.diff_pipeline import run_diff

def run_full_pipeline():
    run_discovery()
    run_ingestion()
    run_normalization()
    run_diff()  # ← Added
```

Running full pipeline:
```bash
python main.py
```

Processes all stages: Discovery → Ingestion → Normalization → Diff

## Execution Results

### Test Mode Execution

```bash
python -m pipelines.diff_pipeline --test-mode
```

**Results**:
- Processed 3 vendors (OpenAI, Stripe, Twilio)
- Detected all intentional changes in synthetic data
- Stripe: 1 added, 1 removed, 1 deprecated
- Twilio: 4 parameter changes (type, requirement, added, removed)
- OpenAI: 1 metadata change (base_url), 1 deprecated, 2 modified
- All diffs stored to `test/diff_output/`

### Production Mode Execution

```bash
python -m pipelines.diff_pipeline
```

**Results**:
- Processed 3 vendors (OpenAI, Stripe, Twilio)
- All vendors: `has_changes=false` (baseline == latest)
- Empty diffs stored (audit trail maintained)
- All diffs stored to `storage/diffs/`

**Interpretation**: Production snapshots have same baseline and latest (no API changes detected), which is expected behavior.

---

# STEP 6 – LLM Classification Pipeline

Implemented **LLM-based classification** using Groq's `gpt-oss-120b` model to analyze API changes and classify them by severity and impact.

The classification layer evaluates each detected change from the diff engine and assigns severity levels (breaking, deprecation, additive, minor) with confidence scores and migration recommendations.

## Classification Workflow

The classification pipeline performs the following steps:

1. Load diff results from storage
2. Initialize Groq API client with `gpt-oss-120b` model
3. For each detected change, build classification prompt with full context
4. Call LLM with optimized parameters (temperature=0.3, reasoning_effort=medium)
5. Parse JSON response with structured output format
6. Fall back to heuristic classification if LLM fails
7. Aggregate classification statistics (breaking/deprecation/additive/minor counts)
8. Store classified diff with recommendations
9. Log critical alerts for breaking changes

## Implementation Architecture

### Classification Models

Type-safe Pydantic models for classification results:

**File**: `specwatch/classification/classification_models.py`

Models include:
- `ChangeClassification` - Single change classification with severity, confidence, reasoning, and migration path
- `ClassifiedEndpointChange` - Original change + LLM classification
- `ClassificationSummary` - Aggregate statistics (breaking count, deprecation count, etc.)
- `ClassifiedAPIDiff` - Complete classified diff with all changes analyzed

**Classification Severity Levels**:
- `breaking` - Immediate client failures (endpoint removed, required param added, type changed)
- `deprecation` - Works now but will break in future (deprecated flag set)
- `additive` - Backward compatible additions (new endpoint, optional param)
- `minor` - Cosmetic changes (description updates, non-functional changes)

### Classification Prompts

LLM prompt engineering for context-aware analysis:

**File**: `specwatch/classification/prompts.py`

Functions include:
- `build_classification_prompt()` - Constructs detailed prompt with change context, other changes in diff, and classification schema
- `build_fallback_classification()` - Heuristic rules when LLM unavailable

**Prompt Structure**:
- API context (vendor, versions, all changes)
- Specific change to classify (type, endpoint, parameters)
- Classification guidelines with examples
- Expected JSON response schema
- Confidence scoring instructions

### LLM Classifier

Core classification engine using Groq API:

**File**: `specwatch/classification/classifier.py`

**ChangeClassifier** class provides:
- Groq API client initialization with `openai/gpt-oss-120b` model
- Individual change classification with full diff context
- Batch diff classification processing all changes
- Automatic fallback to heuristics on LLM failure
- Classification summary aggregation

**Groq API Configuration**:
```python
model = "openai/gpt-oss-120b"
temperature = 0.3       # Low for deterministic output
max_completion_tokens = 1024  # Sufficient for JSON
top_p = 0.9             # Focused sampling
reasoning_effort = "medium"   # Balanced speed/accuracy
stream = False          # Easier JSON parsing
```

**Why these parameters?**
- **Low temperature (0.3)**: Classification should be consistent, not creative
- **Top-p 0.9**: Slightly focused while maintaining quality
- **No streaming**: Simplifies JSON response parsing
- **Medium reasoning**: Good balance for API change analysis

### Classification Storage

**File**: `specwatch/store/classification_store.py`

Storage layer for classified diffs:
- `store_classified_diff()` - Store results with timestamped filenames
- `load_classified_diff()` - Load classified diffs by filename
- `get_latest_classified_diff()` - Retrieve most recent classification

**Filename format**: `classified_diff_{baseline_ts}_to_{latest_ts}.json`

## Classification Pipeline Orchestration

**File**: `pipelines/classification_pipeline.py`

The classification pipeline supports two modes:

### Test Mode
```bash
python -m pipelines.classification_pipeline --test-mode
```

**Input**: `test/diff_output/{vendor}/diff_*.json`  
**Output**: `test/classified_output/{vendor}/classified_diff_*.json`

Uses test diffs from synthetic data to validate LLM classification accuracy.

### Production Mode
```bash
python -m pipelines.classification_pipeline
```

**Input**: `storage/diffs/{vendor}/diff_*.json`  
**Output**: `storage/classified_diffs/{vendor}/classified_diff_*.json`

Classifies real API diffs from production pipeline.

**Pipeline features**:
- Auto-discovers vendors from diff directory
- Skips LLM calls for empty diffs (cost optimization)
- Creates empty classified diffs for audit trail
- Logs critical warnings for breaking changes
- Handles LLM failures gracefully with fallback

## Classified Diff Output Structure

Example classified diff for Stripe:

```json
{
  "vendor": "stripe",
  "baseline_version": "2024-01-10T09:00:00Z",
  "latest_version": "2024-01-20T09:00:00Z",
  "classified_at": "2024-03-21T12:00:00Z",
  "has_breaking_changes": true,
  "has_deprecations": true,
  "requires_immediate_action": true,
  "classification_summary": {
    "total_changes": 3,
    "breaking_changes": 1,
    "deprecations": 1,
    "additive_changes": 1,
    "minor_changes": 0,
    "critical_alerts_needed": 1,
    "warning_alerts_needed": 1,
    "info_notifications": 1
  },
  "classified_changes": [
    {
      "change_type": "endpoint_removed",
      "endpoint_id": "POST:/v1/charges",
      "path": "/v1/charges",
      "method": "POST",
      "classification": {
        "severity": "breaking",
        "confidence": 1.00,
        "reasoning": "Endpoint removal causes existing clients to receive 404 errors. However, POST:/v1/payment_intents was added in this diff, suggesting a planned migration path exists.",
        "recommended_action": "alert_critical",
        "migration_path": "Migrate to POST:/v1/payment_intents. See Stripe migration documentation.",
        "estimated_impact": "high"
      }
    }
  ]
}
```

## Key Implementation Decisions

### LLM vs Heuristics

**Problem**: Simple heuristics can't understand context or migration paths.

**Solution**: Use LLM (Groq's `gpt-oss-120b`) for intelligent, context-aware classification with automatic fallback to heuristics on failure.

**Benefits**:
- Understands migration paths (charges → payment_intents)
- Considers deprecation timelines
- Evaluates multiple related changes together
- Provides detailed reasoning and migration guidance

### Individual vs Batch Classification

**Decision**: Classify each change individually (not batched).

**Rationale**:
- Better context per change
- Easier debugging and validation
- Simpler error handling
- Cost negligible (~$2/month for expected usage)

**Future optimization**: Can batch in Phase 2 if cost becomes issue.

### Empty Diff Optimization

**Problem**: No need to call LLM for empty diffs.

**Solution**: Check `has_changes` flag before processing. If false, create empty classified diff without LLM calls.

**Benefits**:
- Cost optimization (no wasteful API calls)
- Faster execution
- Still maintains audit trail

### Fallback Strategy

**Problem**: LLM might fail (API error, invalid JSON, rate limit).

**Solution**: Automatic fallback to heuristic classification on any error.

**Heuristic Rules**:
- `endpoint_removed` → breaking (confidence: 0.95)
- `endpoint_deprecated` → deprecation (confidence: 0.9)
- `endpoint_added` → additive (confidence: 0.95)
- `parameter_type_changed` → breaking (confidence: 0.85)
- `parameter_required` (optional → required) → breaking (confidence: 0.9)

**Benefits**: Pipeline never fails, always produces classification.

### Confidence Scoring

**LLM provides confidence** (0.0 to 1.0):
- **1.0**: Certain (e.g., endpoint removed = definitely breaking)
- **0.9-0.99**: Very confident
- **0.7-0.89**: Confident
- **0.5-0.69**: Moderate confidence
- **<0.5**: Low confidence (rare)

Used for future filtering and manual review thresholds.

## Integration with Main Pipeline

Updated `main.py` to include classification pipeline:

```python
from pipelines.classification_pipeline import run_classification

def run_full_pipeline():
    run_discovery()
    run_ingestion()
    run_normalization()
    run_diff()
    run_classification()  # ← Added
```

Running full pipeline:
```bash
python main.py
```

Processes all stages: Discovery → Ingestion → Normalization → Diff → Classification

## Execution Results

### Test Mode Execution

```bash
python -m pipelines.classification_pipeline --test-mode
```

**Results**:
-  Processed 3 vendors (OpenAI, Stripe, Twilio)
-  Classified 7 changes total (all with LLM, no fallbacks)
-  Average confidence: 0.95-1.00 (excellent)
-  Average classification time: ~1.5 seconds per change
-  All breaking changes correctly identified
-  Deprecations vs breaking vs additive properly distinguished

**Classification Accuracy**:
- **Stripe**: 1 breaking (endpoint removed, conf=1.00), 1 deprecation (conf=0.96), 1 additive (conf=0.95)
- **OpenAI**: 1 breaking (auth changed, conf=0.95), 1 deprecation (conf=0.95), 1 additive (conf=0.96)
- **Twilio**: 1 breaking (param type changed, conf=0.95)

**Performance**: ~11 seconds for 7 LLM calls (~1.5s average per call)

### Production Mode Execution

```bash
python -m pipelines.classification_pipeline
```

**Results**:
-  Processed 3 vendors (OpenAI, Stripe, Twilio)
-  All vendors: No changes detected
-  Skipped LLM calls (cost optimization)
-  Created empty classified diffs for audit trail
-  Total runtime: <1 second

**Smart Optimization**: Pipeline detected empty diffs and avoided wasteful LLM API calls while still maintaining complete audit trail.

## Cost Analysis

**Per change**:
- Input: ~500 tokens (prompt + context)
- Output: ~200 tokens (classification JSON)
- Groq cost: Varies by plan (free tier available)

**Estimated usage**:
- 3 vendors × ~5 changes per vendor per month = ~15 classifications/month
- Total LLM calls: ~15/month
- Cost: Minimal (under free tier limits)

**Current implementation**: Zero cost overruns, all classifications within expected parameters.

---

# STEP 7 – Alerting Pipeline

Implemented complete alerting system with GitHub Issues, Email notifications.

The alerting layer processes classified diffs and sends notifications via multiple channels based on severity.

## Alerting System Architecture

### Alert Routing Strategy

The alerting system routes notifications based on change severity:

| Severity | GitHub Issue | Email | Rationale |
|---|---|---|---|
| Breaking | Yes | Yes | Critical - requires immediate action |
| Deprecation | Yes | No | Warning - plan migration, create tracking issue |
| Additive | No | Yes | Info - new features available |
| Minor | No | No | Logged only - no alerts needed |

This tiered approach ensures stakeholders receive appropriate notifications without alert fatigue.

## Implementation Components

### Alert Data Models

Type-safe Pydantic models for alert structure:

**File**: `specwatch/alerting/alert_models.py`

Models include:
- `AlertPriority` - Enum: CRITICAL, WARNING, INFO
- `AlertChannel` - Enum: GITHUB, EMAIL, SLACK
- `Alert` - Complete alert with vendor, endpoint, severity, reasoning, migration path
- `AlertResult` - Result of sending alert (success/failure with message)

**Alert Object Structure**:
```python
Alert(
    vendor="stripe",
    title="BREAKING: POST /v1/payments",
    severity="breaking",
    priority=AlertPriority.CRITICAL,
    endpoint_id="POST:/v1/payments",
    method="POST",
    path="/v1/payments",
    change_type="parameter_removed",
    reasoning="Required parameter 'source' removed...",
    migration_path="Replace 'source' with 'payment_method'...",
    impact="critical",
    confidence=0.99,
    baseline_version="2026-03-20T22:51:37Z",
    latest_version="2026-03-29T20:27:50Z",
    detected_at="2026-03-31T10:00:00Z"
)
```

### Alert Formatters

**File**: `specwatch/alerting/alert_formatter.py`

Formats alerts for different channels:
- `format_github_issue()` - Markdown-formatted GitHub issue with labels, priority indicators, and code blocks
- `format_email_html()` - HTML email with color-coded severity, tables, and actionable migration steps
- `format_email_text()` - Plain text fallback for email clients
- `format_slack_message()` - Slack blocks with emoji indicators and action buttons

**GitHub Issue Example**:
```markdown
# 🔴 BREAKING CHANGE: POST /v1/payments

**Severity**: Breaking  
**Confidence**: 99%  
**Impact**: Critical  
**Detected**: 2026-03-31

## Change Details
- **Endpoint**: POST /v1/payments
- **Change Type**: parameter_removed
- **Versions**: 2026-03-20 → 2026-03-29

## Analysis
Required parameter 'source' has been removed from POST /v1/payments endpoint...

## Migration Path
Replace 'source' parameter with new 'payment_method' parameter...

---
*Labels*: breaking, stripe, api-change
```

### GitHub Alerter

**File**: `specwatch/alerting/github_alerter.py`

GitHub Issues integration using PyGithub:

Features:
- Creates issues in designated repository
- Applies severity-based labels (breaking, deprecation, vendor name)
- Sets issue title with emoji indicators (🔴 breaking, ⚠️ deprecation)
- Includes full change context and migration guidance
- Returns issue URL in alert result

**Configuration (via .env)**:
```bash
GITHUB_ENABLED=true
GITHUB_TOKEN=ghp_xxxxx
GITHUB_REPO=specwatch-alerts
```

### Email Alerter

**File**: `specwatch/alerting/email_alerter.py`

SMTP-based email notifications:

Features:
- Gmail SMTP integration (requires App Password)
- HTML + plain text multipart messages
- Color-coded severity indicators
- Tabular change summaries
- Individual alerts + daily digest support

**Configuration (via .env)**:
```bash
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=sender_email
SMTP_PASSWORD=16-char-app-password
EMAIL_FROM=sender_email
EMAIL_TO=receiver_email
```

### Alerting Pipeline with Test Mode

**File**: `pipelines/alerting_pipeline.py`

Complete alerting orchestration with dual-mode support:

**Production Mode**:
```bash
python -m pipelines.alerting_pipeline
```
- Reads from: `storage/classified_diffs/`
- Sends alerts only for actual breaking/deprecation changes
- Uses real GitHub/Email credentials

**Test Mode**:
```bash
python -m pipelines.alerting_pipeline --test
```
- Reads from: `test/classified/output/`
- Uses mock data with pre-defined breaking changes
- Sends **real alerts** to validate setup

**Pipeline Workflow**:
1. Auto-discover vendors from classified diffs directory
2. Load latest classified diff for each vendor
3. Extract critical changes (breaking + deprecations)
4. For each critical change:
   - Create Alert object with full context
   - Determine channels based on severity
   - Send via GitHub/Email
   - Log results
5. Return summary statistics

**Optimization**: Skips vendors with no critical changes.

### Test Fixtures

Mock classified diff with realistic breaking changes:
- 2 breaking changes (endpoint removed, parameter removed)
- 1 deprecation (endpoint deprecated)
- Full LLM-style reasoning and migration paths
- Confidence scores and impact assessments

**Purpose**: Test alerting setup without waiting for real API changes.

---


## Testing Infrastructure

### Test Mode for Alerting

**Command**:
```bash
python -m pipelines.alerting_pipeline --test
```

**Purpose**: Test GitHub/Email setup with mock data containing breaking changes.

**Expected Output**:
```
INFO | Alerting pipeline started (TEST MODE)
INFO | GitHub alerter enabled
INFO | Email alerter enabled
INFO | Processing alerts for stripe
INFO | Found 3 critical changes for stripe
INFO | Sending alert via channels: ['github', 'email']
INFO | GitHub alert sent: Issue created #123
INFO | Email alert sent: Email sent to jhaaditya757@gmail.com
INFO | Alerting complete: 3/3 alert(s) sent successfully
```

**Verification**:
- GitHub: Check `https://github.com/Adityajha0808/specwatch-alerts/issues` for 3 new issues
- Email: Check inbox for 2 emails (breaking changes only)

### Test Fixtures Created

**File**: `test/classified_output/stripe/classified_diff_test_stripe.json`

Contains realistic test data:
- `DELETE /v1/customers/{id}` removed (breaking, confidence: 0.98)
- `POST /v1/payments` parameter `source` removed (breaking, confidence: 0.99)
- `GET /v1/charges` deprecated (deprecation, confidence: 0.96)

**Purpose**: Validate complete alerting flow without production changes.

---

# STEP 8 - Dashboard Integration

Implemented interactive Flask dashboard for pipeline control and visualization. 

The dashboard provides real-time pipeline control, vendor management, and alert preview functionality.

### Dashboard Architecture

**Technology Stack**:
- **Backend**: Flask 3.1.0 with Blueprint architecture
- **Frontend**: Bootstrap 5.3 + Vanilla JavaScript
- **Icons**: Bootstrap Icons
- **State Management**: Server-side with JSON file storage

**File Structure**:
```
app/
├── __init__.py                    # Flask factory
├── config.py                      # Configuration loader
├── routes/
│   ├── dashboard.py              # Main dashboard
│   ├── vendors.py                # Vendor CRUD
│   ├── pipelines.py              # Pipeline control
│   └── alerts.py                 # Alert preview/send
├── templates/
│   ├── base.html                 # Base layout with navbar
│   ├── dashboard.html            # Main dashboard
│   ├── vendors_list.html         # Vendor management
│   ├── vendor_detail.html        # Per-vendor details
│   └── components/
│       ├── vendor_card.html      # Reusable vendor card
│       ├── change_card.html      # Change display card
│       └── alert_modal.html      # Alert preview modal
├── static/
│   ├── css/style.css             # Custom styles
│   └── js/main.js                # Dashboard interactions
└── utils/
    ├── data_loader.py            # Storage JSON reader
    └── pipeline_runner.py        # Background pipeline execution
```

### Core Dashboard Features

**File**: `app/routes/dashboard.py`

Main dashboard displaying:
- Vendor status cards with health indicators
- Recent changes timeline (last 30 days)
- Classification summary statistics
- Quick pipeline controls

Data Sources:
- Vendors: `storage/discovery/*.json`
- Changes: `storage/classified_diffs/{vendor}/*.json`
- Stats: Aggregated from classified diffs

### Vendor Management

**File**: `app/routes/vendors.py`

CRUD operations for vendors:
- List vendors: Show all configured vendors with metadata
- Add vendor: Interactive form with validation
- Remove vendor: Two-step confirmation with optional storage cleanup
- Update baseline: Set new baseline version for diff comparison
- View versions: List all normalized snapshots

### Pipeline Control System

**File**: `app/routes/pipelines.py`

API endpoints for pipeline execution:
- `POST /api/pipelines/discovery` - Run discovery only
- `POST /api/pipelines/analysis` - Run ingestion → classification
- `POST /api/pipelines/full` - Run complete pipeline
- `POST /api/pipelines/alerting` - Run alerting only
- `GET /api/pipelines/status` - Real-time progress tracking

**Background Execution**:

**File**: `app/utils/pipeline_runner.py`

Singleton `PipelineRunner` class managing background threads:
- Spawns daemon threads for non-blocking execution
- Tracks progress (0-100%) with stage updates
- Captures stdout/stderr from subprocess
- Handles timeouts (5 min max)
- Provides real-time status via `/api/pipelines/status`

**Critical Implementation Detail**: Uses `sys.executable` instead of `"python"` for subprocess calls to ensure venv compatibility on different devices.

### Alert Preview & Send

**File**: `app/routes/alerts.py`

Alert management endpoints:
- `GET /api/alerts/preview/<vendor>/<index>` - Preview formatted alerts
- `POST /api/alerts/send` - Send alert via selected channels

**Preview Response Structure**:
```json
{
  "github": {
    "title": "🔴 BREAKING: POST /v1/payments",
    "body": "# Breaking Change\n\n...",
    "labels": ["breaking", "stripe", "api-change"]
  },
  "email": {
    "subject": "🔴 BREAKING CHANGE: Stripe API",
    "body_html": "<html>...",
    "body_text": "Breaking change detected..."
  }
}
```

**Alert Modal** (`app/templates/components/alert_modal.html`):
- Tabbed interface (GitHub / Email / Slack)
- Live preview of formatted alerts
- Send buttons with confirmation
- Loading states and error handling
- JavaScript functions: `showAlertModal()`, `sendAlert()`

### UI Components

**Vendor Card** (`app/templates/components/vendor_card.html`):

**Change Card** (`app/templates/components/change_card.html`):

### Navbar with Pipeline Controls

**File**: `app/templates/base.html`


Pipeline Modal (shows real-time progress).

JavaScript polls `/api/pipelines/status` every 1 second during execution and updates progress bar.

---

## Critical Issues Encountered & Resolved

Below issues were encountered while implementing Dashboard:

### Issue 1: Subprocess Execution on Mac

**Problem**: Pipeline buttons in UI returned success immediately (0 seconds) but nothing executed. Discovery should take ~60 seconds but completed instantly.

**Root Cause**: All `subprocess.run()` calls used hardcoded `"python"` instead of venv's Python interpreter. On Mac with virtualenv, `"python"` often resolves to system Python 2.7 or wrong Python 3, causing "module not found" errors that fail silently.

**Logs Observed**:
```
04:11:03 | Working directory: /Users/.../specwatch-platform
04:11:03 | discovery subprocess completed with returncode: 0
04:11:03 | discovery pipeline completed successfully  # ← Same second!
```

**Solution Applied**: Replace all `"python"` with `sys.executable`:
```python
# BEFORE (broken):
subprocess.run(["python", "-m", "pipelines.discovery_pipeline"], ...)

# AFTER (fixed):
subprocess.run([sys.executable, "-m", "pipelines.discovery_pipeline"], ...)
```

**Result**: Pipelines now execute correctly from UI with proper venv isolation.

### Issue 2: Add Vendor Timeout

**Problem**: Add vendor from UI timed out after 30 seconds with 500 error.

**Cause**: Same as Issue 1 - wrong Python interpreter.

**Solution**: Fixed `vendors.py` to use `sys.executable`.

**Test Solution**: Implemented `--test` mode to validate alerting setup without waiting for real breaking changes.

---

### 8. Caching

**Purpose**: Cache costly calls for discovery, classification and ingestion.

**Implementation**:

- Fingerprint map:

Discovery:
Key   = tavily:search:<query>:<max_results>
Value = full Tavily JSON response

Ingestion:
Key   = spec:hash:{vendor}
Value = hash of actual fetched spec content

Classification:
Key   = classification:<diff_hash>
Value = full LLM classified diff JSON

Each stage caches its highest-cost deterministic artifact: Tavily search payloads in discovery, vendor-level spec content hashes in ingestion, and full LLM-classified diff outputs in classification, using content-based fingerprints as Redis keys.

- I/O reduction in ingestion: The optimization is not the new hash generation itself — we still must hash the freshly fetched spec.
The gain comes from replacing historical snapshot reads with a Redis fingerprint lookup, which turns change detection into a constant-time metadata comparison.

**ISSUES**: Initially used URL-based hashing, but corrected it to content-based fingerprinting because spec URLs remain stable while content changes underneath.
Now ingestion always fetches the spec, computes a content SHA hash, compares it against the vendor’s cached fingerprint in Redis, and only triggers downstream normalization, diffing, and LLM classification when the content hash changes.

---

# Execution Results

## Production Run (March 30, 2026)

| Stage | Duration | Notes |
|---|---|---|
| Discovery | ~71 seconds | 3 vendors, all sources resolved |
| Ingestion | ~10 seconds | Hash-based deduplication, all specs unchanged |
| Normalization | <1 second | Hash-based skip |
| Diff | <1 second | Stripe: 13 changes detected, others: no changes |
| Classification | ~107 seconds | 13 Stripe changes classified, all as `minor` |
| Alerting | <1 second | No breaking/deprecation changes, skipped alerts |

**Total pipeline**: ~3 minutes

**Stripe 13 Changes Analysis**:
- All in `/v2/core/accounts/*` endpoints
- All with `field_changes=1, param_changes=0`
- Timespan: 9 days between versions
- Classification: All `minor` (confidence 0.96-0.99)
- Interpretation: Upstream metadata update (descriptions/summaries), correctly classified as non-breaking

## Test Mode Run

**Command**: `python -m pipelines.alerting_pipeline --test`

**Results**:
- Processed 1 vendor (Stripe)
- Found 3 critical changes (2 breaking, 1 deprecation)
- Sent 3 GitHub issues
- Sent 2 emails (breaking changes only)
- 100% success rate

**GitHub Issues Created**:
- `🔴 BREAKING: DELETE /v1/customers/{id}` (#1)
- `🔴 BREAKING: POST /v1/payments` (#2)
- `⚠️ DEPRECATION: GET /v1/charges` (#3)

---

## Performance Metrics

**Pipeline Execution (Full)**:
- Discovery: ~60 seconds (Tavily API calls)
- Ingestion: ~10 seconds (HTTP fetches with deduplication)
- Normalization: <1 second (hash-based skip)
- Diff: <1 second (set operations on 450 endpoints)
- Classification: ~8 seconds per change (~1.5s LLM call + overhead)
- Alerting: <1 second (GitHub API + SMTP)

**UI Responsiveness**:
- Dashboard load: <200ms
- Pipeline status poll: <50ms
- Alert preview: <100ms

---

# Current Status

At the end of STEP 8:

**Discovery pipeline** – Identifies official API sources  
**Ingestion pipeline** – Fetches raw OpenAPI specifications  
**Normalization pipeline** – Converts specs to canonical format  
**Diff engine** – Detects changes between versions  
**Classification pipeline** – LLM-based severity analysis  
**Alerting pipeline** – Multi-channel notifications (GitHub, Email, Slack)  
**Flask dashboard** – Visual interface for pipeline control and monitoring  

The system now maintains a complete end-to-end pipeline from source discovery to intelligent alerting:

```
Discovery → Ingestion → Normalization → Diff → Classification → Alerting
```

---

## Storage State

```
storage/
├── discovery/              # Latest discovery snapshots
├── raw/
│   ├── discovery/          # Versioned discovery history
│   └── raw_specs/          # Raw OpenAPI specifications
├── normalized/             # Normalized API schemas
│   ├── stripe/
│   │   ├── snapshots/      # All versions
│   │   ├── baseline.json   # Stable reference
│   │   └── latest.json     # Current state
│   ├── twilio/
│   └── openai/
├── diffs/                  # Diff results
│   ├── stripe/
│   │   └── diff_2024-01-10_to_2024-01-20.json
│   ├── twilio/
│   └── openai/
├── classified_diffs/       # LLM-classified diffs
│   ├── stripe/
│   │   └── classified_diff_2024-01-10_to_2024-01-20.json
│   ├── twilio/
│   └── openai/
└── alerts/                 # Alert history
    └── stripe/
        └── alert_history_2026-03-30.json
```

---

## Test Infrastructure

```
test/
├── normalized_output/               # Synthetic normalized test data for diff input
│   ├── stripe/
│   ├── twilio/
│   └── openai/
├── diff_output/                 # Test mode diff results and input for LLM classification
│   ├── stripe/
│   ├── twilio/
│   └── openai/
├── classified_output/      # Test mode classified diffs for alerting input
│   ├── stripe/
│       └── classified_diff_test_stripe.json # Test fixtures for alerting
│   ├── twilio/
│   └── openai/


scripts/
├── test_diff_engine.py     # Unit tests for diff pipeline
```

---

## Application Structure

```
app/                        # Flask dashboard
├── __init__.py
├── config.py
├── routes/
│   ├── dashboard.py
│   ├── vendors.py
│   ├── pipelines.py
│   └── alerts.py
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── vendors_list.html
│   ├── vendor_detail.html
│   └── components/
│       ├── vendor_card.html
│       ├── change_card.html
│       └── alert_modal.html
├── static/
│   ├── css/style.css
│   └── js/main.js
└── utils/
    ├── data_loader.py
    └── pipeline_runner.py
```

---

## Next Steps (Phase 2)

**Scheduled Execution**:
- Cron-based pipeline runs (daily/weekly)
- Automatic baseline updates on production deployments
- Slack digest emails (daily summary)

**Enhanced Alerting**:
- Alert acknowledgment system
- Change approval workflow
- Alert history and analytics

**Improved Change Detection**:
- Semantic endpoint matching (detect path migrations like /v1 → /v2)
- Response schema diff (currently skipped)
- Query parameter ordering stability

**Dashboard Enhancements**:
- Real-time WebSocket updates
- Historical trend charts
- Vendor comparison view
- Alert management interface

**Deployment**:
- Railway/Heroku/Render deployment
- CI/CD with GitHub Actions
- Monitoring and logging (Sentry)
