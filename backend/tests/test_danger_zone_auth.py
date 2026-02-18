"""
Tests for Danger Zone authentication fixes
- Auth via sessionStorage.adminPassword
- GET /api/admin/danger/status endpoint
- GET /api/admin/danger/reset-preview endpoint
- Verify ALLOW_DANGER_RESET=true returns enabled:true
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestDangerZoneAuth:
    """Test Danger Zone endpoints with authentication"""
    
    def test_health_check(self):
        """Basic API health check"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        print(f"✅ Health check passed: {response.json()}")
    
    def test_admin_login_success(self):
        """Admin login with correct password"""
        response = requests.post(
            f"{BASE_URL}/api/admin/login",
            json={"password": "admin123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        print(f"✅ Admin login successful")
    
    def test_admin_login_failure(self):
        """Admin login with wrong password"""
        response = requests.post(
            f"{BASE_URL}/api/admin/login",
            json={"password": "wrongpassword"}
        )
        assert response.status_code == 401
        print(f"✅ Admin login failed correctly with wrong password")
    
    def test_danger_status_endpoint(self):
        """GET /api/admin/danger/status returns enabled:true with reason"""
        response = requests.get(
            f"{BASE_URL}/api/admin/danger/status",
            params={"password": "admin123"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "enabled" in data
        assert "reason" in data
        assert "raw_value" in data
        assert "parsed_value" in data
        
        # ALLOW_DANGER_RESET=true should return enabled:true
        print(f"✅ Danger status: enabled={data['enabled']}, reason={data['reason']}")
        assert data["enabled"] == True, f"Expected enabled=True but got {data['enabled']}"
        assert data["parsed_value"] == True
        assert "true" in data["reason"].lower()
    
    def test_danger_status_wrong_password(self):
        """GET /api/admin/danger/status with wrong password returns 401"""
        response = requests.get(
            f"{BASE_URL}/api/admin/danger/status",
            params={"password": "wrongpassword"}
        )
        assert response.status_code == 401
        print(f"✅ Danger status correctly returns 401 with wrong password")
    
    def test_danger_status_missing_password(self):
        """GET /api/admin/danger/status without password returns 422"""
        response = requests.get(
            f"{BASE_URL}/api/admin/danger/status"
        )
        assert response.status_code == 422
        print(f"✅ Danger status correctly returns 422 without password")
    
    def test_reset_preview_endpoint(self):
        """GET /api/admin/danger/reset-preview returns counts correctly"""
        response = requests.get(
            f"{BASE_URL}/api/admin/danger/reset-preview",
            params={"password": "admin123"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "enabled" in data
        assert "to_delete" in data
        assert "total_documents_to_delete" in data
        assert "preserved" in data
        
        # Check to_delete has expected collections
        to_delete = data["to_delete"]
        assert "reservations" in to_delete
        assert "courses" in to_delete
        assert "commission_payments" in to_delete
        assert "claim_tokens" in to_delete
        assert "activity_logs" in to_delete
        
        # All counts should be integers >= 0
        for collection, count in to_delete.items():
            assert isinstance(count, int)
            assert count >= 0
        
        print(f"✅ Reset preview: enabled={data['enabled']}, total_to_delete={data['total_documents_to_delete']}")
        print(f"   to_delete: {to_delete}")
        print(f"   preserved: {data['preserved']}")
    
    def test_reset_preview_wrong_password(self):
        """GET /api/admin/danger/reset-preview with wrong password returns 401"""
        response = requests.get(
            f"{BASE_URL}/api/admin/danger/reset-preview",
            params={"password": "wrongpassword"}
        )
        assert response.status_code == 401
        print(f"✅ Reset preview correctly returns 401 with wrong password")
    
    def test_reset_preview_status_matches_env(self):
        """Verify preview enabled status matches ALLOW_DANGER_RESET env"""
        response = requests.get(
            f"{BASE_URL}/api/admin/danger/reset-preview",
            params={"password": "admin123"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Since ALLOW_DANGER_RESET=true in backend/.env
        assert data["enabled"] == True
        print(f"✅ Reset preview enabled={data['enabled']} matches env ALLOW_DANGER_RESET=true")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
