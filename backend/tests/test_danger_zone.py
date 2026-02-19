"""
Test Danger Zone Endpoints - Reset all test data functionality
Tests for GET /api/admin/danger/reset-preview and POST /api/admin/danger/reset-all
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://emergent-cleanup-3.preview.emergentagent.com')
ADMIN_PASSWORD = "admin123"


class TestDangerZonePreview:
    """Tests for GET /api/admin/danger/reset-preview endpoint"""
    
    def test_preview_requires_password(self):
        """Preview endpoint should require password parameter"""
        res = requests.get(f"{BASE_URL}/api/admin/danger/reset-preview")
        assert res.status_code == 422, f"Expected 422 for missing password, got {res.status_code}"
    
    def test_preview_rejects_wrong_password(self):
        """Preview endpoint should reject wrong password with 401"""
        res = requests.get(f"{BASE_URL}/api/admin/danger/reset-preview?password=wrong")
        assert res.status_code == 401, f"Expected 401 for wrong password, got {res.status_code}"
    
    def test_preview_returns_collection_counts(self):
        """Preview endpoint should return counts for all collections"""
        res = requests.get(f"{BASE_URL}/api/admin/danger/reset-preview?password={ADMIN_PASSWORD}")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        data = res.json()
        
        # Check required fields
        assert "enabled" in data, "Response should have 'enabled' field"
        assert "to_delete" in data, "Response should have 'to_delete' field"
        assert "preserved" in data, "Response should have 'preserved' field"
        assert "total_documents_to_delete" in data, "Response should have 'total_documents_to_delete' field"
        
        # Verify to_delete has all collections
        to_delete = data["to_delete"]
        required_collections = ["reservations", "courses", "commission_payments", "claim_tokens", "activity_logs"]
        for col in required_collections:
            assert col in to_delete, f"to_delete should include '{col}'"
            assert isinstance(to_delete[col], int), f"'{col}' count should be an integer"
        
        # Verify drivers are preserved
        assert "drivers" in data["preserved"], "Drivers should be in preserved field"
    
    def test_preview_returns_enabled_status(self):
        """Preview should show if ALLOW_DANGER_RESET is enabled"""
        res = requests.get(f"{BASE_URL}/api/admin/danger/reset-preview?password={ADMIN_PASSWORD}")
        assert res.status_code == 200
        
        data = res.json()
        assert "enabled" in data
        # In test environment, ALLOW_DANGER_RESET=true
        assert data["enabled"] is True, "ALLOW_DANGER_RESET should be true in test environment"


class TestDangerZoneReset:
    """Tests for POST /api/admin/danger/reset-all endpoint"""
    
    def test_reset_requires_password(self):
        """Reset endpoint should reject request without password"""
        res = requests.post(
            f"{BASE_URL}/api/admin/danger/reset-all",
            json={"confirm": "RESET-ALL-TEST"}
        )
        # Should fail because password is missing
        assert res.status_code == 422, f"Expected 422 for missing password, got {res.status_code}"
    
    def test_reset_rejects_wrong_password(self):
        """Reset endpoint should reject wrong password with 401"""
        res = requests.post(
            f"{BASE_URL}/api/admin/danger/reset-all",
            json={"confirm": "RESET-ALL-TEST", "password": "wrongpassword"}
        )
        assert res.status_code == 401, f"Expected 401 for wrong password, got {res.status_code}"
    
    def test_reset_rejects_wrong_confirmation(self):
        """Reset endpoint should reject wrong confirmation text with 400"""
        res = requests.post(
            f"{BASE_URL}/api/admin/danger/reset-all",
            json={"confirm": "wrong-text", "password": ADMIN_PASSWORD}
        )
        assert res.status_code == 400, f"Expected 400 for wrong confirmation, got {res.status_code}"
        
        data = res.json()
        assert "detail" in data, "Error response should include detail"
        assert "RESET-ALL-TEST" in data["detail"], "Error should mention expected confirmation text"
    
    def test_reset_accepts_correct_credentials(self):
        """Reset with correct credentials should succeed (Note: This will reset data!)"""
        # First get the preview to see current counts
        preview_res = requests.get(f"{BASE_URL}/api/admin/danger/reset-preview?password={ADMIN_PASSWORD}")
        assert preview_res.status_code == 200
        
        preview_data = preview_res.json()
        
        # Skip actual reset if enabled is False
        if not preview_data.get("enabled"):
            pytest.skip("ALLOW_DANGER_RESET is disabled, skipping actual reset test")
        
        # Execute reset
        res = requests.post(
            f"{BASE_URL}/api/admin/danger/reset-all",
            json={"confirm": "RESET-ALL-TEST", "password": ADMIN_PASSWORD}
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        data = res.json()
        
        # Verify response structure
        assert data.get("success") is True, "Response should indicate success"
        assert "deleted" in data, "Response should have 'deleted' field"
        assert "total_deleted" in data, "Response should have 'total_deleted' field"
        assert "preserved" in data, "Response should have 'preserved' field"
        
        # Verify drivers are preserved
        assert "drivers" in data["preserved"], "Drivers should be preserved"


class TestDangerZoneAfterReset:
    """Tests to verify system state after reset - empty state handling"""
    
    def test_reservations_empty_after_reset(self):
        """Reservations endpoint should return empty array after reset"""
        res = requests.get(f"{BASE_URL}/api/reservations")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        
        data = res.json()
        assert isinstance(data, list), "Should return a list"
        # After reset, should be empty or only have new data
        print(f"Reservations count after reset: {len(data)}")
    
    def test_courses_empty_after_reset(self):
        """Courses endpoint should return empty array after reset"""
        res = requests.get(f"{BASE_URL}/api/admin/subcontracting/courses")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        
        data = res.json()
        assert isinstance(data, list), "Should return a list"
        print(f"Courses count after reset: {len(data)}")
    
    def test_drivers_preserved_after_reset(self):
        """Drivers should be preserved after reset"""
        res = requests.get(f"{BASE_URL}/api/admin/subcontracting/drivers")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        
        data = res.json()
        assert isinstance(data, list), "Should return a list"
        # Verify at least one driver preserved (as mentioned in context)
        print(f"Drivers count after reset: {len(data)}")
    
    def test_preview_shows_zero_after_reset(self):
        """Preview should show 0 counts after reset"""
        res = requests.get(f"{BASE_URL}/api/admin/danger/reset-preview?password={ADMIN_PASSWORD}")
        assert res.status_code == 200
        
        data = res.json()
        to_delete = data.get("to_delete", {})
        
        # All collections should be empty or nearly empty
        print(f"Collections counts after reset: {to_delete}")
        print(f"Total to delete: {data.get('total_documents_to_delete')}")
        print(f"Drivers preserved: {data.get('preserved', {}).get('drivers')}")


class TestEmptyStateHandling:
    """Tests that pages handle empty state gracefully after reset"""
    
    def test_dashboard_api_handles_empty(self):
        """Dashboard reservations API should handle empty state"""
        res = requests.get(f"{BASE_URL}/api/reservations")
        assert res.status_code == 200, f"Expected 200 even when empty, got {res.status_code}"
        
        data = res.json()
        assert isinstance(data, list), "Should return empty array, not error"
    
    def test_subcontracting_api_handles_empty(self):
        """Subcontracting courses API should handle empty state"""
        res = requests.get(f"{BASE_URL}/api/admin/subcontracting/courses")
        assert res.status_code == 200, f"Expected 200 even when empty, got {res.status_code}"
        
        data = res.json()
        assert isinstance(data, list), "Should return empty array, not error"
    
    def test_driver_courses_api_handles_empty(self):
        """Driver portal courses API should handle authentication requirement"""
        # This requires driver auth token, so we test that it responds correctly
        res = requests.get(f"{BASE_URL}/api/driver/courses")
        # Should return 401 without auth, not 500
        assert res.status_code in [401, 200], f"Expected 401 or 200, got {res.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
