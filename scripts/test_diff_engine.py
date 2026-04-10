"""
Unit tests for diff engine.
Tests diff engine against synthetic snapshots with known changes.

Run: python3 -m scripts.test_diff_engine
"""

import json
import pytest
from pathlib import Path

from specwatch.diff.diff_engine import compute_diff, load_snapshot
from specwatch.diff.diff_models import APIDiff


# Test fixtures directory
FIXTURES_DIR = Path("test/normalized_output")


# Test cases for diff engine core functionality
class TestDiffEngine:

    # Test loading snapshots from fixtures
    def test_load_snapshot(self):

        # Stripe baseline should exist
        stripe_baseline = FIXTURES_DIR / "stripe" / "baseline.json"
        assert stripe_baseline.exists(), "Stripe baseline fixture not found"
        
        # Load and verify structure
        snapshot = load_snapshot(str(stripe_baseline))
        assert "metadata" in snapshot
        assert "endpoints" in snapshot
        assert snapshot["metadata"]["vendor"] == "stripe"
    
    # Test Stripe diff detection (endpoint changes)
    def test_stripe_diff(self):

        baseline = str(FIXTURES_DIR / "stripe" / "baseline.json")
        latest = str(FIXTURES_DIR / "stripe" / "latest.json")
        
        diff = compute_diff(baseline, latest, vendor="stripe")
        
        # Verify basic structure
        assert isinstance(diff, APIDiff)
        assert diff.vendor == "stripe"
        assert diff.has_changes is True
        
        # Verify summary counts
        assert diff.summary.endpoints_added == 1, "Should detect 1 added endpoint (payment_intents)"
        assert diff.summary.endpoints_removed == 1, "Should detect 1 removed endpoint (charges)"
        assert diff.summary.endpoints_deprecated == 1, "Should detect 1 deprecated endpoint (GET /customers)"
        
        # Verify specific changes
        endpoint_ids = [change.endpoint_id for change in diff.endpoint_changes]
        assert "POST:/v1/payment_intents" in endpoint_ids, "Should detect payment_intents added"
        assert "POST:/v1/charges" in endpoint_ids, "Should detect charges removed"
        
        print(f"\n Stripe diff test passed:")
        print(f"   Added: {diff.summary.endpoints_added}")
        print(f"   Removed: {diff.summary.endpoints_removed}")
        print(f"   Deprecated: {diff.summary.endpoints_deprecated}")
    
    # Test Twilio diff detection (parameter changes)
    def test_twilio_diff(self):

        baseline = str(FIXTURES_DIR / "twilio" / "baseline.json")
        latest = str(FIXTURES_DIR / "twilio" / "latest.json")
        
        diff = compute_diff(baseline, latest, vendor="twilio")
        
        # Verify basic structure
        assert diff.vendor == "twilio"
        assert diff.has_changes is True
        
        # Verify parameter changes detected
        assert diff.summary.endpoints_modified == 1, "Should detect 1 modified endpoint"
        assert diff.summary.parameters_added >= 1, "Should detect added parameter (StatusCallback)"
        assert diff.summary.parameters_removed >= 1, "Should detect removed parameter (MediaUrl)"
        assert diff.summary.parameters_modified >= 1, "Should detect modified parameter (Body type/From required)"
        
        # Find the modified endpoint
        modified_endpoints = [
            change for change in diff.endpoint_changes
            if change.change_type == "endpoint_modified"
        ]
        assert len(modified_endpoints) > 0
        
        # Verify parameter changes exist
        param_changes = modified_endpoints[0].parameter_changes
        assert len(param_changes) > 0, "Should have parameter changes"
        
        # Check for type change (Body: string → object)
        type_changes = [
            pc for pc in param_changes
            if pc.change_type == "parameter_type_changed" and pc.parameter_name == "Body"
        ]
        assert len(type_changes) == 1, "Should detect Body type change"
        assert type_changes[0].old_field_value == "string"
        assert type_changes[0].new_field_value == "object"
        
        print(f"\n Twilio diff test passed:")
        print(f"   Modified endpoints: {diff.summary.endpoints_modified}")
        print(f"   Params added: {diff.summary.parameters_added}")
        print(f"   Params removed: {diff.summary.parameters_removed}")
        print(f"   Params modified: {diff.summary.parameters_modified}")
    
    # Test OpenAI diff detection (metadata + mixed changes)
    def test_openai_diff(self):

        baseline = str(FIXTURES_DIR / "openai" / "baseline.json")
        latest = str(FIXTURES_DIR / "openai" / "latest.json")
        
        diff = compute_diff(baseline, latest, vendor="openai")
        
        # Verify basic structure
        assert diff.vendor == "openai"
        assert diff.has_changes is True
        
        # Verify metadata changes (base_url)
        assert diff.summary.metadata_changes == 1, "Should detect base_url change"
        assert len(diff.metadata_changes) == 1
        assert diff.metadata_changes[0].field_name == "base_url"
        assert diff.metadata_changes[0].old_value == "https://api.openai.com/v1"
        assert diff.metadata_changes[0].new_value == "https://api.openai.com/v2"
        
        # Verify endpoint deprecation
        assert diff.summary.endpoints_deprecated == 1, "Should detect /completions deprecated"
        
        # Verify endpoint modifications (auth, responses changes)
        assert diff.summary.endpoints_modified >= 1
        
        print(f"\n OpenAI diff test passed:")
        print(f"   Metadata changes: {diff.summary.metadata_changes}")
        print(f"   Deprecated endpoints: {diff.summary.endpoints_deprecated}")
        print(f"   Modified endpoints: {diff.summary.endpoints_modified}")
    
    # Test diff when baseline == latest (no changes)
    def test_no_changes(self):

        # Use same file for both baseline and latest
        baseline = str(FIXTURES_DIR / "stripe" / "baseline.json")
        latest = str(FIXTURES_DIR / "stripe" / "baseline.json")  # Same file
        
        diff = compute_diff(baseline, latest, vendor="stripe")
        
        # Should have no changes
        assert diff.has_changes is False
        assert diff.summary.endpoints_added == 0
        assert diff.summary.endpoints_removed == 0
        assert diff.summary.endpoints_modified == 0
        assert len(diff.endpoint_changes) == 0
        
        print(f"\n No changes test passed")
    
    # Test that diff can be serialized to JSON
    def test_diff_json_serialization(self):

        baseline = str(FIXTURES_DIR / "stripe" / "baseline.json")
        latest = str(FIXTURES_DIR / "stripe" / "latest.json")
        
        diff = compute_diff(baseline, latest, vendor="stripe")
        
        # Convert to JSON
        json_str = diff.to_json()
        assert isinstance(json_str, str)
        
        # Parse back
        data = json.loads(json_str)
        assert data["vendor"] == "stripe"
        assert "summary" in data
        assert "endpoint_changes" in data
        
        print(f"\n JSON serialization test passed")


# Run tests manually
if __name__ == "__main__":

    print("\n" + "="*60)
    print("Running Diff Engine Tests")
    print("="*60)
    
    test = TestDiffEngine()
    
    try:
        test.test_load_snapshot()
        print(" test_load_snapshot passed")
    except AssertionError as e:
        print(f" test_load_snapshot failed: {e}")
    
    try:
        test.test_stripe_diff()
    except AssertionError as e:
        print(f" test_stripe_diff failed: {e}")
    
    try:
        test.test_twilio_diff()
    except AssertionError as e:
        print(f" test_twilio_diff failed: {e}")
    
    try:
        test.test_openai_diff()
    except AssertionError as e:
        print(f" test_openai_diff failed: {e}")
    
    try:
        test.test_no_changes()
    except AssertionError as e:
        print(f" test_no_changes failed: {e}")
    
    try:
        test.test_diff_json_serialization()
    except AssertionError as e:
        print(f" test_diff_json_serialization failed: {e}")
    
    print("\n" + "="*60)
    print("Tests Complete")
    print("="*60 + "\n")
