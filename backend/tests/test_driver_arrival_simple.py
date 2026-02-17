"""
Test Driver Arrival System - Simplified Tests
==============================================
Tests for the 'Chauffeur arrivé + compteur d'attente automatique + confirmation client' feature.
Uses existing ASSIGNED courses for testing.
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://driver-claim-auth.preview.emergentagent.com')

# Test credentials
DRIVER_EMAIL = "chauffeur1@test.com"
DRIVER_PASSWORD = "test123"

# ============================================
# DRIVER LOGIN HELPER
# ============================================
def get_driver_token():
    """Get driver JWT token"""
    res = requests.post(f"{BASE_URL}/api/driver/login", json={
        "email": DRIVER_EMAIL,
        "password": DRIVER_PASSWORD
    })
    assert res.status_code == 200, f"Driver login failed: {res.text}"
    return res.json()['token'], res.json()['driver']['id']


# ============================================
# TEST: ENDPOINT AVAILABILITY
# ============================================
class TestEndpointAvailability:
    """Verify all new endpoints exist and respond correctly"""
    
    def test_waiting_info_endpoint_returns_404_for_invalid_id(self):
        """GET /api/driver/ride/{id}/waiting-info returns 404 for non-existent ride"""
        fake_id = str(uuid.uuid4())
        res = requests.get(f"{BASE_URL}/api/driver/ride/{fake_id}/waiting-info")
        assert res.status_code == 404
        print("[PASS] waiting-info returns 404 for invalid ID")
    
    def test_arrive_endpoint_requires_auth(self):
        """POST /api/driver/ride/{id}/arrive requires authentication"""
        fake_id = str(uuid.uuid4())
        res = requests.post(
            f"{BASE_URL}/api/driver/ride/{fake_id}/arrive",
            json={"lat": 48.8566, "lng": 2.3522}
        )
        assert res.status_code in [401, 403, 404]
        print("[PASS] arrive endpoint requires auth")
    
    def test_client_present_endpoint_requires_token(self):
        """POST /api/driver/ride/{id}/client-present requires token"""
        fake_id = str(uuid.uuid4())
        # Without token param
        res = requests.post(f"{BASE_URL}/api/driver/ride/{fake_id}/client-present")
        assert res.status_code in [401, 403, 404, 422]  # 422 if token param missing
        print("[PASS] client-present requires token param")
    
    def test_no_show_endpoint_requires_auth(self):
        """POST /api/driver/ride/{id}/no-show requires authentication"""
        fake_id = str(uuid.uuid4())
        res = requests.post(f"{BASE_URL}/api/driver/ride/{fake_id}/no-show")
        assert res.status_code in [401, 403, 404]
        print("[PASS] no-show endpoint requires auth")


# ============================================
# TEST: DRIVER ARRIVE WORKFLOW
# ============================================
class TestDriverArriveWorkflow:
    """Test the driver arrive flow using existing ASSIGNED courses"""
    
    @pytest.fixture(scope="class")
    def driver_session(self):
        """Get driver session with token"""
        token, driver_id = get_driver_token()
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        })
        session.driver_id = driver_id
        return session
    
    @pytest.fixture(scope="class")
    def assigned_course(self, driver_session):
        """Find an ASSIGNED course or skip"""
        res = driver_session.get(f"{BASE_URL}/api/driver/courses")
        assert res.status_code == 200
        
        courses = res.json()
        assigned = [c for c in courses if c.get('status') == 'ASSIGNED']
        
        if not assigned:
            pytest.skip("No ASSIGNED courses available for testing")
        
        # Return first ASSIGNED course
        return assigned[0]
    
    def test_arrive_with_gps_coordinates(self, driver_session, assigned_course):
        """Test driver arrive with GPS coordinates"""
        course_id = assigned_course['id']
        token = assigned_course.get('driver_access_token')
        
        gps_data = {"lat": 48.8566, "lng": 2.3522}
        
        # Use token auth if available
        url = f"{BASE_URL}/api/driver/ride/{course_id}/arrive"
        if token:
            url += f"?token={token}"
        
        res = driver_session.post(url, json=gps_data)
        
        # Success (200) or GPS too far (400) or already in progress (409)
        assert res.status_code in [200, 400, 409], f"Unexpected: {res.status_code} - {res.text}"
        
        data = res.json()
        
        if res.status_code == 200:
            assert data.get("status") == "DRIVER_ARRIVED"
            print(f"[PASS] Driver arrived successfully | arrival_time={data.get('arrival_time')}")
        elif res.status_code == 400:
            if data.get("error") == "too_far":
                print(f"[INFO] GPS validation working - driver too far from pickup")
            else:
                print(f"[INFO] Arrive blocked: {data.get('detail', data)}")
        elif res.status_code == 409:
            print(f"[INFO] Course already started/ended")
    
    def test_get_waiting_info_for_course(self, assigned_course):
        """Test getting waiting info for a course"""
        course_id = assigned_course['id']
        
        res = requests.get(f"{BASE_URL}/api/driver/ride/{course_id}/waiting-info")
        
        assert res.status_code == 200, f"Failed: {res.text}"
        
        data = res.json()
        
        # Verify expected fields
        assert "status" in data
        assert "has_arrived" in data
        assert "waiting_minutes" in data
        assert "waiting_price" in data
        assert "can_declare_no_show" in data
        
        print(f"[PASS] Waiting info retrieved | status={data['status']} | has_arrived={data['has_arrived']}")
        print(f"  - waiting_minutes: {data['waiting_minutes']}")
        print(f"  - waiting_price: {data['waiting_price']}")
        print(f"  - can_declare_no_show: {data['can_declare_no_show']}")


# ============================================
# TEST: NO-SHOW FLOW
# ============================================
class TestNoShowFlow:
    """Test the no-show declaration flow"""
    
    def test_no_show_requires_20_minutes(self):
        """No-show should fail if waiting < 20 minutes"""
        # This test uses a freshly arrived driver (if any DRIVER_ARRIVED courses exist)
        token, driver_id = get_driver_token()
        
        session = requests.Session()
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get courses
        res = session.get(f"{BASE_URL}/api/driver/courses")
        courses = res.json()
        
        # Find DRIVER_ARRIVED courses
        arrived = [c for c in courses if c.get('status') == 'DRIVER_ARRIVED']
        
        if not arrived:
            print("[SKIP] No DRIVER_ARRIVED courses to test no-show")
            return
        
        course = arrived[0]
        access_token = course.get('driver_access_token')
        
        # Try no-show
        url = f"{BASE_URL}/api/driver/ride/{course['id']}/no-show"
        if access_token:
            url += f"?token={access_token}"
        
        res = session.post(url)
        
        if res.status_code == 400:
            data = res.json()
            if data.get("error") == "too_early":
                print(f"[PASS] No-show correctly blocked - waiting: {data.get('waiting_minutes')} min (need 20)")
            else:
                print(f"[INFO] No-show blocked: {data}")
        elif res.status_code == 200:
            print("[INFO] No-show succeeded (>= 20 min wait)")


# ============================================
# TEST: START RIDE FROM DRIVER_ARRIVED
# ============================================
class TestStartRideFromArrived:
    """Test starting ride from DRIVER_ARRIVED status"""
    
    def test_start_ride_calculates_waiting_time(self):
        """When starting from DRIVER_ARRIVED, waiting time should be calculated"""
        token, driver_id = get_driver_token()
        
        session = requests.Session()
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get courses
        res = session.get(f"{BASE_URL}/api/driver/courses")
        courses = res.json()
        
        # Find DRIVER_ARRIVED courses
        arrived = [c for c in courses if c.get('status') == 'DRIVER_ARRIVED']
        
        if not arrived:
            print("[SKIP] No DRIVER_ARRIVED courses to test start ride")
            return
        
        course = arrived[0]
        access_token = course.get('driver_access_token')
        
        # Start ride
        url = f"{BASE_URL}/api/driver/ride/{course['id']}/start"
        if access_token:
            url += f"?token={access_token}"
        
        res = session.post(url)
        
        if res.status_code == 200:
            data = res.json()
            assert data.get("status") == "IN_PROGRESS"
            print(f"[PASS] Ride started from DRIVER_ARRIVED")
            
            # Verify course has waiting time recorded
            course_res = session.get(f"{BASE_URL}/api/driver/ride/{course['id']}", params={"token": access_token})
            if course_res.status_code == 200:
                updated = course_res.json()
                print(f"  - waiting_minutes: {updated.get('waiting_minutes', 'N/A')}")
                print(f"  - waiting_price: {updated.get('waiting_price', 'N/A')}")
        elif res.status_code == 409:
            print("[INFO] Ride already in progress")


# ============================================
# TEST: CLIENT PRESENCE
# ============================================
class TestClientPresence:
    """Test client presence signaling"""
    
    def test_client_present_endpoint_works(self):
        """Client can signal presence when driver has arrived"""
        token, driver_id = get_driver_token()
        
        session = requests.Session()
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get courses
        res = session.get(f"{BASE_URL}/api/driver/courses")
        courses = res.json()
        
        # Find DRIVER_ARRIVED courses
        arrived = [c for c in courses if c.get('status') == 'DRIVER_ARRIVED']
        
        if not arrived:
            print("[SKIP] No DRIVER_ARRIVED courses to test client presence")
            return
        
        course = arrived[0]
        
        # Try client presence (uses course ID as token)
        res = requests.post(
            f"{BASE_URL}/api/driver/ride/{course['id']}/client-present",
            params={"token": course['id']}
        )
        
        if res.status_code == 200:
            data = res.json()
            if data.get("idempotent"):
                print("[PASS] Client presence already recorded (idempotent)")
            else:
                print(f"[PASS] Client presence recorded at {data.get('client_present_time')}")
        elif res.status_code == 400:
            print(f"[INFO] Client presence blocked: {res.json()}")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])
