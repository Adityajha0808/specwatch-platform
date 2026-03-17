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
| Twilio | stripe/openapi | `openapi/spec3.yaml` |
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
- Recursive depth search to reolve missing specs inside nested folders.

Downloaded specifications are now stored in the versioned storage layer:

storage/raw/raw_specs/

These files represent the **raw API contract snapshots** that will be used for further schema parsing and change detection in subsequent stages of the system.


# Current Status

At the end of Day 3:

- Source discovery is fully operational

- Vendor sources are resolved and validated

- OpenAPI specifications are fetched automatically

- Versioned API contracts are stored locally

- The system can now collect API contract data from external vendors automatically.

- This dataset will be used in the next stage to parse and normalize API schemas for change detection.
