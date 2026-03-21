# ROADMAP

Here’s a brutally practical 7-day execution plan, plus how to move from MVP → interview-grade system.

No fluff. No “learn AI” nonsense. Just work.


#### DAY ZERO ####

7-Day Execution Plan

Project: API Change Detection & Compatibility Intelligence System
Goal after 7 days:
A working system that:

discovers API sources

stores versions

diffs changes

classifies breaking changes

sends alerts

That’s already interview-grade.


#### DAY 1 ####

Day 1 — Repo + Architecture Lock

Goal: No coding without structure.

Tasks

Create repo

Create folder structure:

services/
pipelines/
schemas/
storage/
orchestration/
docs/
config/

Write docs/architecture.md:

problem statement

system diagram

component responsibilities

data flow

failure points

scaling path

Write docs/decisions.md:

why Tavily

why versioned storage

why diffing

why LLM classification

why async pipeline

If this isn’t done, coding = wasted effort.



#### DAY 2 ####

Day 2 — Data Discovery (Tavily Layer)

Goal: Live source discovery working.

Tasks

Implement services/discovery/

Tavily queries:

"Stripe API changelog"

"Twilio API changelog/docs/OpenAPI-spec"

"OpenAI API docs"

"Stripe OpenAPI spec"

"OpenAI OpenAPI"

Output schema:
{
  "api": "Stripe",
  "sources": {
    "docs": "...",
    "openapi": "...",
    "changelog": "..."
  }
}

Save to local JSON.

No ingestion yet — just discovery.


#### DAY 3 ####

Day 3 — Ingestion + Raw Storage

Goal: Pull real data and store versions.

Tasks

services/ingestion/

Fetch:

OpenAPI spec

docs HTML/markdown

Store raw versions:

storage/raw/stripe/v1.json
storage/raw/stripe/v2.json

Add timestamps.

No processing yet.


#### DAY 4 ####

Day 4 — Normalization + Canonical Schema

Goal: Unified format.

Tasks

Define schema in schemas/api_schema.json:

{
  "endpoint": "",
  "method": "",
  "params": [],
  "response": {},
  "auth": ""
}

Build:
services/normalization/normalize.py

Convert OpenAPI → canonical format.

Store:

storage/normalized/stripe/v1.json
storage/normalized/stripe/v2.json


#### DAY 5 ####

Day 5 — Diff Engine

Goal: Detect real changes.

Tasks

services/diff_engine/diff.py

Detect:

removed endpoints

new endpoints

param changes

type changes

required → optional

auth changes

Output:

{
  "endpoint": "/v1/customers",
  "change": "param_removed",
  "param": "email"
}


#### DAY 6 ####

Day 6 — LLM Change Classification

Goal: Semantic understanding.

Tasks

services/classifier/classify.py

Input: diff JSON
Output:

{
  "severity": "breaking",
  "confidence": 0.94,
  "reason": "required param removed"
}

Now you have:
raw → normalized → diff → classified

That’s a real pipeline.


#### DAY 7 ####

Day 7 — Alerting + Pipeline Wiring

Goal: End-to-end system.

Tasks

services/alerting/slack.py

Webhook integration

pipelines/main_pipeline.py:

discovery

ingestion

normalization

diff

classification

alert

Run end-to-end for Stripe/Twilio/OpenAI.


#### MOVING FORWARD ####

After 7 Days You Have:

Live data ingestion
Versioned storage
Change detection
Semantic classification
Automated alerts
Real pipeline
Real architecture

This is already interview-grade.

How to Move After Day 7 (Completion Strategy)
Phase 1 Completion (Week 2)

Stabilization

error handling

retries

caching

deduplication

version indexing

source trust scoring

fallback logic (Tavily down)

Phase 2 (Week 3)

Intelligence Layer

impact scoring

dependency mapping

repo scanning

confidence thresholds

false-positive filtering

Phase 3 (Optional)

Platformization

API service

dashboard

webhook triggers

CI integration

multi-API support

multi-tenant model

How NOT to Work (Important)

UI first
chatbot interface
prompt engineering
dashboards early
“AI demo”
agent loops
overengineering infra

How to Think While Building

Always ask:

What fails?

What’s stale?

What’s noisy?

What’s expensive?

What’s unreliable?

What’s trustable?

What’s cached?

What’s versioned?

That’s engineering mindset.

Completion Definition (Realistic)

Project is “done” when:

pipeline runs automatically

detects real API change

classifies it correctly

sends alert

stores version history

recovers from failure

has architecture docs

Not when UI looks good.
