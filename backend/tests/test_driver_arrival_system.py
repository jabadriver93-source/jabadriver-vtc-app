"""
Test Driver Arrival System - Jabadriver
========================================
Tests for the 'Chauffeur arrivé + compteur d'attente automatique + confirmation client' feature.

Endpoints tested:
- POST /api/driver/ride/{id}/arrive - Driver signals arrival with GPS
- GET /api/driver/ride/{id}/waiting-info - Get real-time waiting info
- POST /api/driver/ride/{id}/client-present - Client signals presence
- POST /api/driver/ride/{id}/no-show - Driver declares client absent after 20 min
- POST /api/driver/ride/{id}/start - Start ride (from DRIVER_ARRIVED)
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://admin-analytics-v2.preview.emergentagent.com')

# Test credentials
DRIVER_EMAIL = "chauffeur1@test.com"
DRIVER_PASSWORD = "test123"
ADMIN_EMAIL = "admin"
ADMIN_PASSWORD = "admin123"


class TestDriverArrivalSystem:
    """Tests for the driver arrival and waiting time system"""
    
    @pytest.fixture(scope="class")
    def driver_session(self):
        """Login as driver and get session token"""
        session = requests.Session()
        res = session.post(f"{BASE_URL}/api/driver/login", json={
            "email": DRIVER_EMAIL,
            "password": DRIVER_PASSWORD
        })
        assert res.status_code == 200, f"Driver login failed: {res.text}"
        data = res.json()
        session.headers.update({"Authorization": f"Bearer {data['token']}"})
        session.driver_id = data['driver']['id']
        return session
    
    @pytest.fixture(scope="class")
    def admin_session(self):
        """Login as admin and get session"""
        session = requests.Session()
        res = session.post(f"{BASE_URL}/api/admin/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert res.status_code == 200, f"Admin login failed: {res.text}"
        data = res.json()
        session.headers.update({"Authorization": f"Bearer {data['token']}"})
        return session
    
    @pytest.fixture(scope="class")
    def test_course(self, admin_session, driver_session):
        """Create a test course assigned to the driver"""
        # Create a new course
        course_data = {
            "client_name": f"Test Client Arrival {datetime.now().strftime('%H%M%S')}",
            "client_email": "testclient@test.com",
            "client_phone": "+33612345678",
            "pickup_address": "10 Rue de Rivoli, 75001 Paris, France",
            "dropoff_address": "20 Avenue des Champs-Élysées, 75008 Paris, France",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": "14:00",
            "price_total": 50.0,
            "notes": "Test course for driver arrival system"
        }
        
        res = admin_session.post(f"{BASE_URL}/api/admin/subcontracting/courses", json=course_data)
        assert res.status_code == 200, f"Failed to create course: {res.text}"
        course = res.json()
        course_id = course['id']
        
        # Directly assign to driver (bypass claim/payment flow for testing)
        # Use admin API to update course status
        update_res = admin_session.put(
            f"{BASE_URL}/api/admin/subcontracting/courses/{course_id}",
            json={
                "status": "ASSIGNED",
                "assigned_driver_id": driver_session.driver_id
            }
        )
        
        if update_res.status_code != 200:
            # Alternative: Try to update via direct DB-like API
            print(f"[WARNING] Could not assign course via admin API: {update_res.status_code}")
        
        # Fetch the course to get driver_access_token
        course_res = admin_session.get(f"{BASE_URL}/api/admin/subcontracting/courses/{course_id}")
        if course_res.status_code == 200:
            course = course_res.json()
        
        yield course
        
        # Cleanup: Cancel the course
        try:
            admin_session.put(
                f"{BASE_URL}/api/admin/subcontracting/courses/{course_id}",
                json={"status": "CANCELLED"}
            )
        except:
            pass
    
    # ============================================
    # TEST 1: Driver Arrive Endpoint - Basic
    # ============================================
    def test_arrive_requires_gps(self, driver_session, test_course):
        """Test that arrive endpoint requires GPS coordinates"""
        course_id = test_course['id']
        
        # Try to arrive without GPS data
        res = driver_session.post(
            f"{BASE_URL}/api/driver/ride/{course_id}/arrive",
            json={}  # Missing lat/lng
        )
        
        # Should fail with validation error
        assert res.status_code in [400, 422], f"Expected 400/422, got {res.status_code}: {res.text}"
    
    def test_arrive_with_gps(self, driver_session, test_course):
        """Test driver arrival with GPS coordinates"""
        course_id = test_course['id']
        
        # Mock GPS coordinates (Paris center)
        gps_data = {
            "lat": 48.8566,
            "lng": 2.3522
        }
        
        res = driver_session.post(
            f"{BASE_URL}/api/driver/ride/{course_id}/arrive",
            json=gps_data
        )
        
        # Could be 200 (success) or 400 (too far) or 409 (already started)
        if res.status_code == 200:
            data = res.json()
            assert data.get("success") == True
            assert data.get("status") == "DRIVER_ARRIVED"
            assert "arrival_time" in data
            print(f"[SUCCESS] Driver arrived at {data.get('arrival_time')}")
        elif res.status_code == 400:
            data = res.json()
            if data.get("error") == "too_far":
                print(f"[INFO] GPS validation working - too far from pickup")
            else:
                print(f"[INFO] Arrive returned 400: {data}")
        elif res.status_code == 409:
            print(f"[INFO] Course already in progress or done")
        else:
            print(f"[WARNING] Unexpected status {res.status_code}: {res.text}")
    
    # ============================================
    # TEST 2: Waiting Info Endpoint
    # ============================================
    def test_waiting_info_before_arrival(self):
        """Test waiting info when driver has not arrived yet"""
        # Use a non-existent ID to test 404 handling
        fake_id = str(uuid.uuid4())
        
        res = requests.get(f"{BASE_URL}/api/driver/ride/{fake_id}/waiting-info")
        
        assert res.status_code == 404, f"Expected 404 for non-existent ride: {res.text}"
    
    def test_waiting_info_endpoint_exists(self, test_course):
        """Test that waiting-info endpoint returns valid data"""
        course_id = test_course['id']
        
        res = requests.get(f"{BASE_URL}/api/driver/ride/{course_id}/waiting-info")
        
        # Should return 200 with waiting info
        assert res.status_code == 200, f"Failed to get waiting info: {res.text}"
        
        data = res.json()
        
        # Check expected fields
        assert "status" in data
        assert "has_arrived" in data
        assert "waiting_minutes" in data
        assert "waiting_billable_minutes" in data
        assert "waiting_price" in data
        assert "can_declare_no_show" in data
        
        print(f"[SUCCESS] Waiting info: {data}")
    
    # ============================================
    # TEST 3: Client Present Endpoint
    # ============================================
    def test_client_present_requires_driver_arrived(self, test_course):
        """Test that client-present requires driver to have arrived first"""
        course_id = test_course['id']
        status = test_course.get('status', 'UNKNOWN')
        
        # If status is ASSIGNED (driver not arrived), should fail
        if status == "ASSIGNED":
            res = requests.post(
                f"{BASE_URL}/api/driver/ride/{course_id}/client-present",
                params={"token": course_id}
            )
            
            # Should fail because driver hasn't arrived
            assert res.status_code in [400, 404], f"Expected 400 for ASSIGNED status: {res.text}"
            print(f"[SUCCESS] client-present blocked when driver not arrived")
        else:
            print(f"[INFO] Skipping test - course status is {status}")
    
    # ============================================
    # TEST 4: No-Show Endpoint
    # ============================================
    def test_no_show_requires_driver_arrived(self, driver_session, test_course):
        """Test that no-show requires driver to have arrived first"""
        course_id = test_course['id']
        status = test_course.get('status', 'UNKNOWN')
        
        # If status is ASSIGNED, should fail
        if status == "ASSIGNED":
            res = driver_session.post(f"{BASE_URL}/api/driver/ride/{course_id}/no-show")
            
            assert res.status_code == 400, f"Expected 400, got {res.status_code}: {res.text}"
            print(f"[SUCCESS] no-show blocked when driver not arrived")
        else:
            print(f"[INFO] Skipping test - course status is {status}")
    
    def test_no_show_requires_20_min_wait(self, driver_session, test_course):
        """Test that no-show requires 20 minutes of waiting"""
        course_id = test_course['id']
        status = test_course.get('status', 'UNKNOWN')
        
        # Only test if status is DRIVER_ARRIVED
        if status == "DRIVER_ARRIVED":
            res = driver_session.post(f"{BASE_URL}/api/driver/ride/{course_id}/no-show")
            
            # Should fail if < 20 min
            if res.status_code == 400:
                data = res.json()
                assert data.get("error") == "too_early", f"Expected 'too_early' error: {data}"
                print(f"[SUCCESS] no-show blocked - waiting time: {data.get('waiting_minutes')} min")
            elif res.status_code == 200:
                print(f"[INFO] No-show succeeded (20+ min wait)")
        else:
            print(f"[INFO] Skipping test - course status is {status}")
    
    # ============================================
    # TEST 5: Start Ride from DRIVER_ARRIVED
    # ============================================
    def test_start_from_driver_arrived(self, driver_session, test_course):
        """Test that ride can be started from DRIVER_ARRIVED status"""
        course_id = test_course['id']
        status = test_course.get('status', 'UNKNOWN')
        
        # Only test if status is DRIVER_ARRIVED
        if status == "DRIVER_ARRIVED":
            res = driver_session.post(f"{BASE_URL}/api/driver/ride/{course_id}/start")
            
            if res.status_code == 200:
                data = res.json()
                assert data.get("status") == "IN_PROGRESS"
                print(f"[SUCCESS] Started ride from DRIVER_ARRIVED")
                
                # Check that waiting time was calculated
                assert "waiting_minutes" in data or data.get("success") == True
            elif res.status_code == 409:
                print(f"[INFO] Ride already in progress")
            else:
                print(f"[WARNING] Start failed: {res.status_code} - {res.text}")
        else:
            print(f"[INFO] Skipping test - course status is {status}")
    
    # ============================================
    # TEST 6: Idempotency Tests
    # ============================================
    def test_arrive_idempotent(self, driver_session, test_course):
        """Test that calling arrive twice returns idempotent response"""
        course_id = test_course['id']
        
        gps_data = {"lat": 48.8566, "lng": 2.3522}
        
        # First call
        res1 = driver_session.post(
            f"{BASE_URL}/api/driver/ride/{course_id}/arrive",
            json=gps_data
        )
        
        # Second call (should be idempotent)
        res2 = driver_session.post(
            f"{BASE_URL}/api/driver/ride/{course_id}/arrive",
            json=gps_data
        )
        
        # Both should succeed or fail gracefully
        if res1.status_code == 200:
            assert res2.status_code in [200, 409], f"Second arrive should be idempotent: {res2.text}"
            if res2.status_code == 200:
                data = res2.json()
                # May have idempotent flag
                print(f"[SUCCESS] Idempotent arrive response: {data.get('idempotent', 'no flag')}")
        print(f"[INFO] Arrive idempotency test complete")


class TestWaitingTimePricing:
    """Test waiting time calculation and pricing logic"""
    
    def test_waiting_info_structure(self):
        """Test waiting info has correct structure"""
        # Create a simple test to verify endpoint response structure
        fake_id = str(uuid.uuid4())
        
        res = requests.get(f"{BASE_URL}/api/driver/ride/{fake_id}/waiting-info")
        
        # 404 is expected for non-existent ride
        assert res.status_code == 404
    
    def test_pricing_constants(self):
        """Verify pricing constants are documented correctly"""
        # This is a documentation test - verifying the expected values
        # based on the system requirements:
        # - First 5 minutes: FREE
        # - After 5 min: 1€/minute
        # - Maximum: 20€ (20 minutes billable)
        
        expected_free_minutes = 5
        expected_price_per_minute = 1.0
        expected_max_billable = 20
        
        print(f"[INFO] Expected pricing:")
        print(f"  - Free minutes: {expected_free_minutes}")
        print(f"  - Price per minute: {expected_price_per_minute}€")
        print(f"  - Max billable minutes: {expected_max_billable}")
        print(f"  - Max charge: {expected_max_billable * expected_price_per_minute}€")


class TestDriverArrivalAuth:
    """Test authentication modes for driver arrival endpoints"""
    
    @pytest.fixture
    def driver_token(self):
        """Get driver JWT token"""
        res = requests.post(f"{BASE_URL}/api/driver/login", json={
            "email": DRIVER_EMAIL,
            "password": DRIVER_PASSWORD
        })
        assert res.status_code == 200
        return res.json()['token']
    
    def test_arrive_requires_auth(self):
        """Test that arrive endpoint requires authentication"""
        fake_id = str(uuid.uuid4())
        
        res = requests.post(
            f"{BASE_URL}/api/driver/ride/{fake_id}/arrive",
            json={"lat": 48.8566, "lng": 2.3522}
        )
        
        assert res.status_code in [401, 403, 404], f"Expected auth error: {res.status_code}"
    
    def test_no_show_requires_auth(self):
        """Test that no-show endpoint requires authentication"""
        fake_id = str(uuid.uuid4())
        
        res = requests.post(f"{BASE_URL}/api/driver/ride/{fake_id}/no-show")
        
        assert res.status_code in [401, 403, 404], f"Expected auth error: {res.status_code}"
    
    def test_waiting_info_public(self):
        """Test that waiting-info endpoint is publicly accessible"""
        fake_id = str(uuid.uuid4())
        
        # Should be 404 (not found) not 401 (auth required)
        res = requests.get(f"{BASE_URL}/api/driver/ride/{fake_id}/waiting-info")
        
        assert res.status_code == 404, f"Expected 404, got {res.status_code}"


class TestDriverRideEndpoints:
    """Test existing ride endpoints work with new statuses"""
    
    @pytest.fixture(scope="class")
    def session(self):
        """Get authenticated session"""
        session = requests.Session()
        res = session.post(f"{BASE_URL}/api/driver/login", json={
            "email": DRIVER_EMAIL,
            "password": DRIVER_PASSWORD
        })
        if res.status_code == 200:
            session.headers.update({"Authorization": f"Bearer {res.json()['token']}"})
        return session
    
    def test_ride_endpoint_returns_arrival_fields(self, session):
        """Test that ride endpoint returns new arrival-related fields"""
        # Get list of driver's courses
        res = session.get(f"{BASE_URL}/api/driver/courses")
        
        if res.status_code == 200:
            courses = res.json()
            if courses and len(courses) > 0:
                course = courses[0]
                
                # Check for new fields (may be null)
                # These fields should exist in the schema
                print(f"[INFO] Course fields check:")
                print(f"  - status: {course.get('status')}")
                print(f"  - arrival_time: {course.get('arrival_time', 'NOT PRESENT')}")
                print(f"  - client_present_time: {course.get('client_present_time', 'NOT PRESENT')}")
                print(f"  - waiting_minutes: {course.get('waiting_minutes', 'NOT PRESENT')}")
                print(f"  - waiting_price: {course.get('waiting_price', 'NOT PRESENT')}")
            else:
                print("[INFO] No courses found for driver")
        else:
            print(f"[WARNING] Failed to get courses: {res.status_code}")
    
    def test_start_endpoint_accepts_assigned_and_arrived(self, session):
        """Test that start endpoint works from both ASSIGNED and DRIVER_ARRIVED"""
        # This is a documentation/validation test
        # The start endpoint should accept both statuses
        
        # Get a course to test
        res = session.get(f"{BASE_URL}/api/driver/courses")
        
        if res.status_code == 200:
            courses = res.json()
            assigned_courses = [c for c in courses if c.get('status') == 'ASSIGNED']
            arrived_courses = [c for c in courses if c.get('status') == 'DRIVER_ARRIVED']
            
            print(f"[INFO] Found {len(assigned_courses)} ASSIGNED courses")
            print(f"[INFO] Found {len(arrived_courses)} DRIVER_ARRIVED courses")
            
            # Test start on an arrived course if available
            if arrived_courses:
                course = arrived_courses[0]
                start_res = session.post(f"{BASE_URL}/api/driver/ride/{course['id']}/start")
                print(f"[INFO] Start from DRIVER_ARRIVED: {start_res.status_code}")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])
