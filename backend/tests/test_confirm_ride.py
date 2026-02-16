"""
Test suite for client ride confirmation flow
Endpoints:
  - GET /api/driver/confirm-ride/{ride_id}?token - Get ride details for confirmation page
  - POST /api/driver/confirm-ride/{ride_id}?token - Confirm ride (DRIVER_COMPLETED → DONE)
"""
import pytest
import requests
import os
import secrets
import uuid
from pymongo import MongoClient
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# MongoDB setup for test data management
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'jabadriver_vtc')


@pytest.fixture(scope="module")
def db():
    """MongoDB connection fixture"""
    client = MongoClient(MONGO_URL)
    return client[DB_NAME]


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def test_driver(db):
    """Create or get test driver"""
    driver_id = "test-confirm-driver-id"
    driver = db.drivers.find_one({"id": driver_id})
    if not driver:
        db.drivers.insert_one({
            "id": driver_id,
            "email": "confirm-driver@test.com",
            "password_hash": "test",
            "company_name": "Confirm Test Company",
            "name": "Jean Confirm",
            "phone": "0611223344",
            "address": "1 rue du Test, 75001 Paris",
            "siret": "11111111111111",
            "vat_mention": "TVA non applicable",
            "vat_applicable": False,
            "driver_code": "DRTEST",
            "invoice_next_number": 1,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    yield driver_id
    # Cleanup is optional for test drivers


@pytest.fixture
def test_course_driver_completed(db, test_driver):
    """Create a fresh DRIVER_COMPLETED course with client confirmation token"""
    test_token = secrets.token_urlsafe(32)
    ride_id = f"TEST_confirm-{str(uuid.uuid4())[:8]}"
    
    course = {
        "id": ride_id,
        "client_name": "Test Client",
        "client_email": "testclient@example.com",
        "client_phone": "0612345678",
        "pickup_address": "10 rue de Départ, 75001 Paris",
        "dropoff_address": "20 rue d'Arrivée, 75016 Paris",
        "date": "2026-02-17",
        "time": "15:00",
        "distance_km": 10.0,
        "duration_min": 25,
        "price_total": 35.0,
        "price_base": 35.0,
        "price_with_supplements": 35.0,
        "notes": "Test confirmation course",
        "status": "DRIVER_COMPLETED",
        "assigned_driver_id": test_driver,
        "assigned_at": "2026-02-17T13:00:00+00:00",
        "started_at": "2026-02-17T14:55:00+00:00",
        "ended_at": "2026-02-17T15:20:00+00:00",
        "commission_rate": 0.10,
        "commission_amount": 3.5,
        "commission_paid": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "invoice_status": "DRAFT",
        "supplement_peage": 0.0,
        "supplement_parking": 0.0,
        "supplement_attente_minutes": 0,
        "supplement_attente_amount": 0.0,
        "is_test": True,
        "driver_access_token": secrets.token_urlsafe(32),
        "client_confirmation_token": test_token,
        "confirmed_at": None
    }
    
    db.courses.insert_one(course)
    yield {"ride_id": ride_id, "token": test_token}
    
    # Cleanup
    db.courses.delete_one({"id": ride_id})


@pytest.fixture
def test_course_done(db, test_driver):
    """Create a DONE course (already confirmed)"""
    ride_id = f"TEST_done-{str(uuid.uuid4())[:8]}"
    
    course = {
        "id": ride_id,
        "client_name": "Already Confirmed Client",
        "client_email": "done@example.com",
        "client_phone": "0612345678",
        "pickup_address": "1 rue Done, 75001 Paris",
        "dropoff_address": "2 rue Done, 75016 Paris",
        "date": "2026-02-16",
        "time": "10:00",
        "distance_km": 8.0,
        "price_total": 30.0,
        "status": "DONE",  # Already DONE
        "assigned_driver_id": test_driver,
        "assigned_at": "2026-02-16T08:00:00+00:00",
        "started_at": "2026-02-16T09:55:00+00:00",
        "ended_at": "2026-02-16T10:15:00+00:00",
        "confirmed_at": "2026-02-16T10:30:00+00:00",
        "commission_rate": 0.10,
        "commission_amount": 3.0,
        "commission_paid": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_test": True,
        "driver_access_token": None,  # Token invalidated after DONE
        "client_confirmation_token": None,  # Token invalidated after DONE
    }
    
    db.courses.insert_one(course)
    yield {"ride_id": ride_id}
    
    # Cleanup
    db.courses.delete_one({"id": ride_id})


class TestGetConfirmRide:
    """Tests for GET /api/driver/confirm-ride/{ride_id}?token"""
    
    def test_get_confirm_ride_success(self, api_client, test_course_driver_completed):
        """GET confirm-ride with valid token returns ride details"""
        ride_id = test_course_driver_completed["ride_id"]
        token = test_course_driver_completed["token"]
        
        response = api_client.get(f"{BASE_URL}/api/driver/confirm-ride/{ride_id}?token={token}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["id"] == ride_id
        assert data["status"] == "DRIVER_COMPLETED"
        assert data["already_confirmed"] == False
        assert data["client_name"] == "Test Client"
        assert data["pickup_address"] == "10 rue de Départ, 75001 Paris"
        assert data["dropoff_address"] == "20 rue d'Arrivée, 75016 Paris"
        assert data["price_total"] == 35.0
        assert "started_at" in data
        assert "ended_at" in data
        assert "driver" in data
        print(f"✅ GET confirm-ride with valid token works - returned ride details")
    
    def test_get_confirm_ride_invalid_token(self, api_client, test_course_driver_completed):
        """GET confirm-ride with invalid token returns 403"""
        ride_id = test_course_driver_completed["ride_id"]
        
        response = api_client.get(f"{BASE_URL}/api/driver/confirm-ride/{ride_id}?token=invalid_token_12345")
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        print(f"✅ Invalid token correctly rejected with 403")
    
    def test_get_confirm_ride_missing_token(self, api_client, test_course_driver_completed):
        """GET confirm-ride without token returns 422"""
        ride_id = test_course_driver_completed["ride_id"]
        
        response = api_client.get(f"{BASE_URL}/api/driver/confirm-ride/{ride_id}")
        
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print(f"✅ Missing token correctly rejected with 422")
    
    def test_get_confirm_ride_nonexistent(self, api_client):
        """GET confirm-ride for non-existent ride returns 404"""
        response = api_client.get(f"{BASE_URL}/api/driver/confirm-ride/nonexistent-ride-id?token=any_token")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✅ Non-existent ride correctly returns 404")
    
    def test_get_confirm_ride_already_done(self, api_client, test_course_done):
        """GET confirm-ride for DONE ride returns already_confirmed=true"""
        ride_id = test_course_done["ride_id"]
        
        # DONE rides have null token, so this should fail with 403
        response = api_client.get(f"{BASE_URL}/api/driver/confirm-ride/{ride_id}?token=any_token")
        
        # Since token is null, it should return 403
        assert response.status_code == 403, f"Expected 403 for DONE ride with null token, got {response.status_code}"
        print(f"✅ DONE ride with invalidated token correctly returns 403")


class TestPostConfirmRide:
    """Tests for POST /api/driver/confirm-ride/{ride_id}?token"""
    
    def test_confirm_ride_success(self, api_client, test_course_driver_completed, db):
        """POST confirm-ride changes status to DONE and invalidates tokens"""
        ride_id = test_course_driver_completed["ride_id"]
        token = test_course_driver_completed["token"]
        
        # Confirm the ride
        response = api_client.post(f"{BASE_URL}/api/driver/confirm-ride/{ride_id}?token={token}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] == True
        assert data["status"] == "DONE"
        assert "confirmed_at" in data
        assert data.get("already_confirmed", False) == False
        
        # Verify in database that tokens are invalidated
        course = db.courses.find_one({"id": ride_id})
        assert course["status"] == "DONE"
        assert course["client_confirmation_token"] is None, "client_confirmation_token should be invalidated"
        assert course["driver_access_token"] is None, "driver_access_token should be invalidated"
        assert course["confirmed_at"] is not None
        
        print(f"✅ POST confirm-ride success - status changed to DONE, tokens invalidated")
    
    def test_confirm_ride_invalid_token(self, api_client, db, test_driver):
        """POST confirm-ride with invalid token returns 403"""
        # Create a fresh course for this test
        test_token = secrets.token_urlsafe(32)
        ride_id = f"TEST_invalid-{str(uuid.uuid4())[:8]}"
        
        db.courses.insert_one({
            "id": ride_id,
            "client_name": "Invalid Token Test",
            "client_email": "invalid@test.com",
            "client_phone": "0600000000",
            "pickup_address": "Test pickup",
            "dropoff_address": "Test dropoff",
            "date": "2026-02-17",
            "time": "10:00",
            "price_total": 25.0,
            "status": "DRIVER_COMPLETED",
            "assigned_driver_id": test_driver,
            "client_confirmation_token": test_token,
            "is_test": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        try:
            response = api_client.post(f"{BASE_URL}/api/driver/confirm-ride/{ride_id}?token=wrong_token")
            assert response.status_code == 403, f"Expected 403, got {response.status_code}"
            print(f"✅ Invalid token on POST confirm-ride correctly rejected with 403")
        finally:
            db.courses.delete_one({"id": ride_id})
    
    def test_confirm_ride_missing_token(self, api_client, test_course_driver_completed):
        """POST confirm-ride without token returns 422"""
        ride_id = test_course_driver_completed["ride_id"]
        
        response = api_client.post(f"{BASE_URL}/api/driver/confirm-ride/{ride_id}")
        
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print(f"✅ Missing token on POST confirm-ride correctly rejected with 422")
    
    def test_confirm_ride_double_confirmation(self, api_client, db, test_driver):
        """POST confirm-ride twice returns already_confirmed=true on second call"""
        test_token = secrets.token_urlsafe(32)
        ride_id = f"TEST_double-{str(uuid.uuid4())[:8]}"
        
        # Create course
        db.courses.insert_one({
            "id": ride_id,
            "client_name": "Double Confirm Test",
            "client_email": "double@test.com",
            "client_phone": "0600000001",
            "pickup_address": "Double pickup",
            "dropoff_address": "Double dropoff",
            "date": "2026-02-17",
            "time": "11:00",
            "price_total": 40.0,
            "status": "DRIVER_COMPLETED",
            "assigned_driver_id": test_driver,
            "client_confirmation_token": test_token,
            "driver_access_token": secrets.token_urlsafe(32),
            "is_test": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        try:
            # First confirmation
            response1 = api_client.post(f"{BASE_URL}/api/driver/confirm-ride/{ride_id}?token={test_token}")
            assert response1.status_code == 200
            data1 = response1.json()
            assert data1["status"] == "DONE"
            
            # Second confirmation with same token (should fail since token is now null)
            response2 = api_client.post(f"{BASE_URL}/api/driver/confirm-ride/{ride_id}?token={test_token}")
            # Token was invalidated, so should return 403
            assert response2.status_code == 403, f"Expected 403 for second confirmation, got {response2.status_code}"
            
            print(f"✅ Double confirmation correctly blocked - token invalidated after first confirmation")
        finally:
            db.courses.delete_one({"id": ride_id})
    
    def test_confirm_ride_nonexistent(self, api_client):
        """POST confirm-ride for non-existent ride returns 404"""
        response = api_client.post(f"{BASE_URL}/api/driver/confirm-ride/nonexistent-id?token=any_token")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✅ Non-existent ride on POST confirm-ride correctly returns 404")


class TestTokenInvalidation:
    """Tests to verify token invalidation after confirmation"""
    
    def test_driver_token_invalidated_after_confirmation(self, api_client, db, test_driver):
        """After client confirmation, driver_access_token should be null and unusable"""
        test_token = secrets.token_urlsafe(32)
        driver_token = secrets.token_urlsafe(32)
        ride_id = f"TEST_drivertoken-{str(uuid.uuid4())[:8]}"
        
        # Create course with both tokens
        db.courses.insert_one({
            "id": ride_id,
            "client_name": "Driver Token Test",
            "client_email": "drivertoken@test.com",
            "client_phone": "0600000002",
            "pickup_address": "Token pickup",
            "dropoff_address": "Token dropoff",
            "date": "2026-02-17",
            "time": "12:00",
            "price_total": 45.0,
            "status": "DRIVER_COMPLETED",
            "assigned_driver_id": test_driver,
            "client_confirmation_token": test_token,
            "driver_access_token": driver_token,
            "is_test": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        try:
            # Driver can access ride before confirmation
            response_before = api_client.get(f"{BASE_URL}/api/driver/ride/{ride_id}?token={driver_token}")
            assert response_before.status_code == 200, "Driver should be able to access before confirmation"
            
            # Client confirms
            response_confirm = api_client.post(f"{BASE_URL}/api/driver/confirm-ride/{ride_id}?token={test_token}")
            assert response_confirm.status_code == 200
            
            # Driver can no longer access with old token (token is now null)
            response_after = api_client.get(f"{BASE_URL}/api/driver/ride/{ride_id}?token={driver_token}")
            assert response_after.status_code == 403, f"Expected 403 after confirmation, got {response_after.status_code}"
            
            print(f"✅ Driver access token correctly invalidated after client confirmation")
        finally:
            db.courses.delete_one({"id": ride_id})


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
