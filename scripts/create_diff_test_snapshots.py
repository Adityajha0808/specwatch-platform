#!/usr/bin/env python
"""Generates synthetic normalized snapshots for diff engine testing.

Creates baseline.json and latest.json for each vendor with intentional differences:
- Stripe: Endpoint-level changes (added/removed/deprecated)
- Twilio: Parameter-level changes (type/required/added/removed)
- OpenAI: Metadata + mixed changes (base_url/auth/responses)
"""

import json
from pathlib import Path
from datetime import datetime, timedelta


# Base directory for test fixtures
FIXTURES_DIR = Path("tests_diff/fixtures")


# Create Stripe baseline and latest snapshots with endpoint changes
def create_stripe_snapshots():
    
    vendor_dir = FIXTURES_DIR / "stripe"
    vendor_dir.mkdir(parents=True, exist_ok=True)
    
    # Baseline (V1) - Jan 10
    baseline = {
        "metadata": {
            "vendor": "stripe",
            "normalized_at": "2026-01-10T09:00:00Z",
            "source_file": "stripe_openapi_2026-01-10.yaml",
            "source_hash": "aaaa1111bbbb2222",
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
                "deprecated": False,
                "parameters": [
                    {
                        "name": "email",
                        "location": "body",
                        "required": True,
                        "type": "string",
                        "description": "Customer email address"
                    },
                    {
                        "name": "name",
                        "location": "body",
                        "required": False,
                        "type": "string",
                        "description": "Customer name"
                    }
                ],
                "request_body_required": False,
                "auth_required": True,
                "responses": ["200", "400", "401"]
            },
            {
                "id": "GET:/v1/customers",
                "path": "/v1/customers",
                "method": "GET",
                "summary": "List all customers",
                "deprecated": False,
                "parameters": [
                    {
                        "name": "limit",
                        "location": "query",
                        "required": False,
                        "type": "integer",
                        "description": "Limit number of results"
                    }
                ],
                "request_body_required": False,
                "auth_required": True,
                "responses": ["200", "401"]
            },
            {
                "id": "POST:/v1/charges",
                "path": "/v1/charges",
                "method": "POST",
                "summary": "Create a charge (old API)",
                "deprecated": False,
                "parameters": [
                    {
                        "name": "amount",
                        "location": "body",
                        "required": True,
                        "type": "integer",
                        "description": "Amount in cents"
                    },
                    {
                        "name": "currency",
                        "location": "body",
                        "required": True,
                        "type": "string",
                        "description": "Three-letter ISO currency code"
                    }
                ],
                "request_body_required": True,
                "auth_required": True,
                "responses": ["200", "400", "401"]
            }
        ]
    }
    
    # Latest (V2) - Jan 20 (10 days later)
    # Changes:
    # 1. POST:/v1/charges removed (endpoint removed)
    # 2. POST:/v1/payment_intents added (endpoint added)
    # 3. GET:/v1/customers deprecated (endpoint deprecated)
    latest = {
        "metadata": {
            "vendor": "stripe",
            "normalized_at": "2026-01-20T09:00:00Z",
            "source_file": "stripe_openapi_2026-01-20.yaml",
            "source_hash": "cccc3333dddd4444",
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
                "deprecated": False,
                "parameters": [
                    {
                        "name": "email",
                        "location": "body",
                        "required": True,
                        "type": "string",
                        "description": "Customer email address"
                    },
                    {
                        "name": "name",
                        "location": "body",
                        "required": False,
                        "type": "string",
                        "description": "Customer name"
                    }
                ],
                "request_body_required": False,
                "auth_required": True,
                "responses": ["200", "400", "401"]
            },
            {
                "id": "GET:/v1/customers",
                "path": "/v1/customers",
                "method": "GET",
                "summary": "List all customers",
                "deprecated": True,  # CHANGED: deprecated
                "parameters": [
                    {
                        "name": "limit",
                        "location": "query",
                        "required": False,
                        "type": "integer",
                        "description": "Limit number of results"
                    }
                ],
                "request_body_required": False,
                "auth_required": True,
                "responses": ["200", "401"]
            },
            # POST:/v1/charges REMOVED
            # NEW ENDPOINT ADDED:
            {
                "id": "POST:/v1/payment_intents",
                "path": "/v1/payment_intents",
                "method": "POST",
                "summary": "Create a payment intent",
                "deprecated": False,
                "parameters": [
                    {
                        "name": "amount",
                        "location": "body",
                        "required": True,
                        "type": "integer",
                        "description": "Amount in cents"
                    },
                    {
                        "name": "currency",
                        "location": "body",
                        "required": True,
                        "type": "string",
                        "description": "Three-letter ISO currency code"
                    },
                    {
                        "name": "payment_method",
                        "location": "body",
                        "required": False,
                        "type": "string",
                        "description": "Payment method ID"
                    }
                ],
                "request_body_required": True,
                "auth_required": True,
                "responses": ["200", "400", "401"]
            }
        ]
    }
    
    # Save files
    with open(vendor_dir / "baseline.json", "w") as f:
        json.dump(baseline, f, indent=2)
    
    with open(vendor_dir / "latest.json", "w") as f:
        json.dump(latest, f, indent=2)
    
    print(f"   Created Stripe snapshots in {vendor_dir}/")
    print(f"   Changes: 1 endpoint added, 1 removed, 1 deprecated")


# Create Twilio baseline and latest snapshots with parameter changes
def create_twilio_snapshots():
    
    vendor_dir = FIXTURES_DIR / "twilio"
    vendor_dir.mkdir(parents=True, exist_ok=True)
    
    # Baseline (V1) - Jan 15
    baseline = {
        "metadata": {
            "vendor": "twilio",
            "normalized_at": "2026-01-15T10:00:00Z",
            "source_file": "twilio_openapi_2026-01-15.json",
            "source_hash": "eeee5555ffff6666",
            "schema_version": "1.0",
            "openapi_version": "3.0.0"
        },
        "base_url": "https://api.twilio.com",
        "endpoints": [
            {
                "id": "POST:/2010-04-01/Accounts/{AccountSid}/Messages.json",
                "path": "/2010-04-01/Accounts/{AccountSid}/Messages.json",
                "method": "POST",
                "summary": "Send an SMS message",
                "deprecated": False,
                "parameters": [
                    {
                        "name": "AccountSid",
                        "location": "path",
                        "required": True,
                        "type": "string",
                        "description": "Account SID"
                    },
                    {
                        "name": "To",
                        "location": "body",
                        "required": True,
                        "type": "string",
                        "description": "Destination phone number"
                    },
                    {
                        "name": "From",
                        "location": "body",
                        "required": True,
                        "type": "string",
                        "description": "Source phone number"
                    },
                    {
                        "name": "Body",
                        "location": "body",
                        "required": True,
                        "type": "string",
                        "description": "Message body"
                    },
                    {
                        "name": "MediaUrl",
                        "location": "body",
                        "required": False,
                        "type": "string",
                        "description": "Media URL for MMS"
                    }
                ],
                "request_body_required": True,
                "auth_required": True,
                "responses": ["200", "400", "401"]
            }
        ]
    }
    
    # Latest (V2) - Jan 25 (10 days later)
    # Changes:
    # 1. Body parameter type changed: string → object (BREAKING!)
    # 2. From parameter required changed: true → false
    # 3. MediaUrl parameter removed
    # 4. StatusCallback parameter added (new optional)
    latest = {
        "metadata": {
            "vendor": "twilio",
            "normalized_at": "2026-01-25T10:00:00Z",
            "source_file": "twilio_openapi_2026-01-25.json",
            "source_hash": "gggg7777hhhh8888",
            "schema_version": "1.0",
            "openapi_version": "3.0.0"
        },
        "base_url": "https://api.twilio.com",
        "endpoints": [
            {
                "id": "POST:/2010-04-01/Accounts/{AccountSid}/Messages.json",
                "path": "/2010-04-01/Accounts/{AccountSid}/Messages.json",
                "method": "POST",
                "summary": "Send an SMS message",
                "deprecated": False,
                "parameters": [
                    {
                        "name": "AccountSid",
                        "location": "path",
                        "required": True,
                        "type": "string",
                        "description": "Account SID"
                    },
                    {
                        "name": "To",
                        "location": "body",
                        "required": True,
                        "type": "string",
                        "description": "Destination phone number"
                    },
                    {
                        "name": "From",
                        "location": "body",
                        "required": False,  # CHANGED: required true → false
                        "type": "string",
                        "description": "Source phone number"
                    },
                    {
                        "name": "Body",
                        "location": "body",
                        "required": True,
                        "type": "object",  # CHANGED: type string → object (BREAKING!)
                        "description": "Message body with rich content"
                    },
                    # MediaUrl REMOVED
                    # NEW PARAMETER:
                    {
                        "name": "StatusCallback",
                        "location": "body",
                        "required": False,
                        "type": "string",
                        "description": "Status callback URL"
                    }
                ],
                "request_body_required": True,
                "auth_required": True,
                "responses": ["200", "400", "401"]
            }
        ]
    }
    
    # Save files
    with open(vendor_dir / "baseline.json", "w") as f:
        json.dump(baseline, f, indent=2)
    
    with open(vendor_dir / "latest.json", "w") as f:
        json.dump(latest, f, indent=2)
    
    print(f"   Created Twilio snapshots in {vendor_dir}/")
    print(f"   Changes: 1 param type changed, 1 required changed, 1 added, 1 removed")


# Create OpenAI baseline and latest snapshots with metadata + mixed changes
def create_openai_snapshots():
    
    vendor_dir = FIXTURES_DIR / "openai"
    vendor_dir.mkdir(parents=True, exist_ok=True)
    
    # Baseline (V1) - Jan 12
    baseline = {
        "metadata": {
            "vendor": "openai",
            "normalized_at": "2026-01-12T11:00:00Z",
            "source_file": "openai_openapi_2026-01-12.yaml",
            "source_hash": "iiii9999jjjj0000",
            "schema_version": "1.0",
            "openapi_version": "3.0.0"
        },
        "base_url": "https://api.openai.com/v1",
        "endpoints": [
            {
                "id": "POST:/chat/completions",
                "path": "/chat/completions",
                "method": "POST",
                "summary": "Create chat completion",
                "deprecated": False,
                "parameters": [
                    {
                        "name": "model",
                        "location": "body",
                        "required": True,
                        "type": "string",
                        "description": "Model ID"
                    },
                    {
                        "name": "messages",
                        "location": "body",
                        "required": True,
                        "type": "array",
                        "description": "Array of messages"
                    },
                    {
                        "name": "temperature",
                        "location": "body",
                        "required": False,
                        "type": "number",
                        "description": "Sampling temperature"
                    }
                ],
                "request_body_required": True,
                "auth_required": True,
                "responses": ["200", "400", "401"]
            },
            {
                "id": "POST:/completions",
                "path": "/completions",
                "method": "POST",
                "summary": "Create text completion (legacy)",
                "deprecated": False,
                "parameters": [
                    {
                        "name": "model",
                        "location": "body",
                        "required": True,
                        "type": "string",
                        "description": "Model ID"
                    },
                    {
                        "name": "prompt",
                        "location": "body",
                        "required": True,
                        "type": "string",
                        "description": "Text prompt"
                    }
                ],
                "request_body_required": True,
                "auth_required": False,  # No auth required (for testing)
                "responses": ["200", "400"]
            }
        ]
    }
    
    # Latest (V2) - Jan 22 (10 days later)
    # Changes:
    # 1. Base URL changed: /v1 → /v2 (BREAKING!)
    # 2. POST:/completions deprecated
    # 3. POST:/chat/completions auth_required changed: true → true (no change, but testing)
    # 4. POST:/chat/completions responses changed: added 429 rate limit
    # 5. POST:/completions auth_required changed: false → true (BREAKING!)
    latest = {
        "metadata": {
            "vendor": "openai",
            "normalized_at": "2026-01-22T11:00:00Z",
            "source_file": "openai_openapi_2026-01-22.yaml",
            "source_hash": "kkkk1111llll2222",
            "schema_version": "1.0",
            "openapi_version": "3.0.0"
        },
        "base_url": "https://api.openai.com/v2",  # CHANGED: base URL (BREAKING!)
        "endpoints": [
            {
                "id": "POST:/chat/completions",
                "path": "/chat/completions",
                "method": "POST",
                "summary": "Create chat completion",
                "deprecated": False,
                "parameters": [
                    {
                        "name": "model",
                        "location": "body",
                        "required": True,
                        "type": "string",
                        "description": "Model ID"
                    },
                    {
                        "name": "messages",
                        "location": "body",
                        "required": True,
                        "type": "array",
                        "description": "Array of messages"
                    },
                    {
                        "name": "temperature",
                        "location": "body",
                        "required": False,
                        "type": "number",
                        "description": "Sampling temperature"
                    }
                ],
                "request_body_required": True,
                "auth_required": True,
                "responses": ["200", "400", "401", "429"]  # CHANGED: added 429
            },
            {
                "id": "POST:/completions",
                "path": "/completions",
                "method": "POST",
                "summary": "Create text completion (legacy)",
                "deprecated": True,  # CHANGED: deprecated
                "parameters": [
                    {
                        "name": "model",
                        "location": "body",
                        "required": True,
                        "type": "string",
                        "description": "Model ID"
                    },
                    {
                        "name": "prompt",
                        "location": "body",
                        "required": True,
                        "type": "string",
                        "description": "Text prompt"
                    }
                ],
                "request_body_required": True,
                "auth_required": True,  # CHANGED: false → true (BREAKING!)
                "responses": ["200", "400"]
            }
        ]
    }
    
    # Save files
    with open(vendor_dir / "baseline.json", "w") as f:
        json.dump(baseline, f, indent=2)
    
    with open(vendor_dir / "latest.json", "w") as f:
        json.dump(latest, f, indent=2)
    
    print(f"✅ Created OpenAI snapshots in {vendor_dir}/")
    print(f"   Changes: base_url changed, 1 deprecated, 1 auth changed, 1 responses changed")


# Generate all synthetic test snapshots
def main():

    print("\n" + "="*60)
    print("Creating Synthetic Diff Test Snapshots")
    print("="*60 + "\n")
    
    # Create fixtures directory
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create snapshots for each vendor
    create_stripe_snapshots()
    create_twilio_snapshots()
    create_openai_snapshots()
    
    print("\n" + "="*60)
    print(" All synthetic snapshots created successfully!")
    print("="*60)
    print(f"\n Location: {FIXTURES_DIR.absolute()}")
    print("\n Next steps:")
    print("1. Verify fixtures: ls -R tests_diff/fixtures/")
    print("2. Run diff pipeline: python -m pipelines.diff_pipeline --test-mode")
    print("3. Check results: cat tests_diff/output/stripe/diff_*.json")
    print()


if __name__ == "__main__":
    main()
