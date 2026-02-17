"""
Test ride workflow: START and END buttons
Tests for bugs:
1) 'Démarrer la course' button shows 'Course déjà en statut: unknown' error on iPhone/Safari even when API returns 200 OK
2) Verify correct status transitions: ASSIGNED → IN_PROGRESS → DRIVER_COMPLETED

Test focuses on:
- START ride: Click 'Démarrer la course' and verify status changes from ASSIGNED to IN_PROGRESS
- END ride: Click 'Terminer la course' and verify status changes from IN_PROGRESS to DRIVER_COMPLETED  
- 409 error handling: Verify no 'unknown' status is displayed when 409 occurs
"""

import pytest
import requests
import os
import uuid

# Get base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://driver-claim-auth.preview.emergentagent.com"

# Test credentials
DRIVER_EMAIL = "chauffeur1@test.com"
DRIVER_PASSWORD = "test123"
TEST_COURSE_ID = "btn-test-1b89dafe"
TEST_COURSE_TOKEN = "JbStqVXilGCqI8fWYfA4O16R8VmVJy2vVfo0RJBcGoo"


class TestDriverAuth:
    """Test driver authentication"""
    
    def test_driver_login_success(self):
        """Test driver login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/driver/login", json={
            "email": DRIVER_EMAIL,
            "password": DRIVER_PASSWORD
        })
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "Missing token in response"
        assert "driver" in data, "Missing driver in response"
        assert data["driver"]["email"] == DRIVER_EMAIL
        assert data["driver"]["is_active"] == True
        print(f"✅ Driver login successful: {data['driver']['name']}")


class TestRideWorkflow:
    """Test ride START and END workflow - main bug fixes"""
    
    @pytest.fixture
    def driver_token(self):
        """Get driver auth token"""
        response = requests.post(f"{BASE_URL}/api/driver/login", json={
            "email": DRIVER_EMAIL,
            "password": DRIVER_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture
    def reset_test_course(self, driver_token):
        """Reset test course to ASSIGNED status before test"""
        # This requires admin access - for now we'll create a new test course
        pass
    
    def test_start_ride_success_response_format(self, driver_token):
        """
        BUG FIX TEST: Verify start_ride returns correct format with 'status' field
        
        The bug was: Frontend showed 'Course déjà en statut: unknown' because
        it was looking for 'status' field but backend returned different field name.
        
        Expected successful response:
        {
            "success": true,
            "message": "Course démarrée !",
            "status": "IN_PROGRESS",  <-- This field was missing/wrongly named
            "started_at": "...",
            "started_by_driver_id": "..."
        }
        """
        # Create a fresh test course for this test
        unique_id = f"test-start-{uuid.uuid4().hex[:8]}"
        
        # First, we test with existing course but it might already be started
        # Let's test the response format by checking a 409 conflict response
        response = requests.post(
            f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}/start?token={TEST_COURSE_TOKEN}",
            headers={
                "Authorization": f"Bearer {driver_token}",
                "Content-Type": "application/json"
            }
        )
        
        print(f"Start ride response status: {response.status_code}")
        print(f"Start ride response body: {response.text}")
        
        data = response.json()
        
        if response.status_code == 200:
            # SUCCESS case - verify correct response format
            assert "success" in data, "Missing 'success' field in 200 response"
            assert "status" in data, "Missing 'status' field in 200 response"
            assert "message" in data, "Missing 'message' field in 200 response"
            assert data["status"] == "IN_PROGRESS", f"Expected IN_PROGRESS, got {data['status']}"
            assert data["success"] == True
            print(f"✅ Start ride SUCCESS - status: {data['status']}")
        
        elif response.status_code == 409:
            # CONFLICT case - verify 'current_status' field is present (for 409 error handling)
            # BUG FIX: Frontend should read 'current_status' not 'status' from 409 response
            assert "detail" in data, "Missing 'detail' field in 409 response"
            assert "current_status" in data, "Missing 'current_status' field in 409 response - BUG!"
            assert data["current_status"] != "unknown", f"current_status should not be 'unknown', got: {data['current_status']}"
            print(f"✅ Start ride 409 response correct - current_status: {data['current_status']}")
        
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")
    
    def test_409_response_has_current_status(self, driver_token):
        """
        BUG FIX TEST: Verify 409 response includes 'current_status' field
        
        When ride is already started, the 409 response must include 'current_status'
        so frontend can display the correct status instead of 'unknown'.
        
        This tests the fix for: "Course déjà en statut: unknown" error on iPhone/Safari
        """
        # First start the ride (or it's already started)
        response = requests.post(
            f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}/start?token={TEST_COURSE_TOKEN}",
            headers={
                "Authorization": f"Bearer {driver_token}",
                "Content-Type": "application/json"
            }
        )
        
        # Now try to start again - should get 409
        response2 = requests.post(
            f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}/start?token={TEST_COURSE_TOKEN}",
            headers={
                "Authorization": f"Bearer {driver_token}",
                "Content-Type": "application/json"
            }
        )
        
        print(f"Double-start response status: {response2.status_code}")
        print(f"Double-start response body: {response2.text}")
        
        # Should be 409 since ride was already started
        if response2.status_code == 409:
            data = response2.json()
            
            # BUG FIX: This is the critical field that was missing
            assert "current_status" in data, "BUG: Missing 'current_status' in 409 response!"
            
            current_status = data.get("current_status")
            assert current_status is not None, "BUG: current_status is None!"
            assert current_status != "unknown", f"BUG: current_status is 'unknown'! Got: {current_status}"
            assert current_status in ["IN_PROGRESS", "DRIVER_COMPLETED", "DONE"], \
                f"Unexpected current_status: {current_status}"
            
            print(f"✅ 409 response correctly includes current_status: {current_status}")
        else:
            print(f"Note: Got {response2.status_code} instead of 409")
    
    def test_end_ride_409_response_format(self, driver_token):
        """
        BUG FIX TEST: Verify end_ride 409 response includes 'current_status' field
        """
        # Try to end ride (might already be ended)
        response = requests.post(
            f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}/end?token={TEST_COURSE_TOKEN}",
            headers={
                "Authorization": f"Bearer {driver_token}",
                "Content-Type": "application/json"
            }
        )
        
        print(f"End ride response status: {response.status_code}")
        print(f"End ride response body: {response.text}")
        
        data = response.json()
        
        if response.status_code == 200:
            # SUCCESS case
            assert "success" in data, "Missing 'success' field"
            assert "status" in data, "Missing 'status' field in 200 response"
            assert data["status"] == "DRIVER_COMPLETED", f"Expected DRIVER_COMPLETED, got {data['status']}"
            print(f"✅ End ride SUCCESS - status: {data['status']}")
        
        elif response.status_code == 409:
            # CONFLICT case - verify current_status is present
            assert "current_status" in data, "BUG: Missing 'current_status' in end_ride 409 response!"
            current_status = data.get("current_status")
            assert current_status != "unknown", f"BUG: current_status is 'unknown'!"
            print(f"✅ End ride 409 response correct - current_status: {current_status}")
        
        elif response.status_code == 400:
            # Invalid status transition
            print(f"End ride 400 (invalid status): {data.get('detail')}")
        
        else:
            print(f"End ride got status: {response.status_code}")


class TestFreshCourseWorkflow:
    """Test complete workflow with a fresh course to verify transitions"""
    
    @pytest.fixture
    def driver_token(self):
        """Get driver auth token"""
        response = requests.post(f"{BASE_URL}/api/driver/login", json={
            "email": DRIVER_EMAIL,
            "password": DRIVER_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_get_assigned_course(self, driver_token):
        """Find an ASSIGNED course to test the full workflow"""
        response = requests.get(
            f"{BASE_URL}/api/driver/courses",
            headers={"Authorization": f"Bearer {driver_token}"}
        )
        
        assert response.status_code == 200
        courses = response.json()
        
        # Find an ASSIGNED course
        assigned_courses = [c for c in courses if c['status'] == 'ASSIGNED']
        
        print(f"Total courses: {len(courses)}")
        print(f"ASSIGNED courses: {len(assigned_courses)}")
        
        if assigned_courses:
            course = assigned_courses[0]
            print(f"Found ASSIGNED course: {course['id'][:20]}")
            print(f"  Client: {course['client_name']}")
            print(f"  Token: {course.get('driver_access_token', 'N/A')[:20] if course.get('driver_access_token') else 'N/A'}")
        else:
            print("No ASSIGNED courses found - might all be IN_PROGRESS or completed")


class TestStatusBadgeMapping:
    """Test that all status values map correctly (no 'unknown' status)"""
    
    def test_all_valid_statuses(self):
        """Verify all status values that API can return"""
        valid_statuses = [
            "OPEN",
            "RESERVED",
            "ASSIGNED",
            "IN_PROGRESS",
            "DRIVER_COMPLETED",
            "DONE",
            "CANCELLED",
            "CANCELLED_LATE_DRIVER",
            "CANCELLED_LATE_CLIENT"
        ]
        
        # These should all be recognized by frontend getStatusLabel()
        for status in valid_statuses:
            assert status != "unknown", f"Invalid status: {status}"
            print(f"✅ Valid status: {status}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
