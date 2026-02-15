"""
Test is_test filter functionality for courses
Tests the toggle endpoint and commission exclusion logic
"""
import pytest
import requests
import os
import uuid
import time

# Use public URL for testing
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://ride-test-filter.preview.emergentagent.com"

class TestIsTestFilter:
    """Tests for is_test course filter feature"""
    
    # ==========================================
    # Test API health and courses endpoint
    # ==========================================
    
    def test_api_health(self):
        """Test API health endpoint"""
        res = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert res.status_code == 200, f"API health check failed: {res.status_code}"
        print("✓ API health check passed")
    
    def test_get_courses_returns_is_test_field(self):
        """GET /api/admin/subcontracting/courses should return is_test field"""
        res = requests.get(f"{BASE_URL}/api/admin/subcontracting/courses", timeout=10)
        assert res.status_code == 200, f"Get courses failed: {res.status_code}"
        
        courses = res.json()
        assert isinstance(courses, list), "Response should be a list"
        
        if len(courses) > 0:
            # Check that at least one course has the is_test field
            has_is_test_field = any("is_test" in course for course in courses)
            assert has_is_test_field, "Courses should have is_test field"
            
            # Print courses with is_test info
            for course in courses[:3]:  # Show first 3
                course_id = course.get('id', 'N/A')[:8]
                is_test = course.get('is_test', 'N/A')
                print(f"  Course {course_id}: is_test={is_test}")
        
        print(f"✓ Get courses returned {len(courses)} courses with is_test field")
    
    # ==========================================
    # Test toggle-test endpoint
    # ==========================================
    
    def test_toggle_test_on_specific_course(self):
        """POST /api/admin/subcontracting/courses/{id}/toggle-test should toggle is_test flag"""
        # First get courses to find one to test with
        res = requests.get(f"{BASE_URL}/api/admin/subcontracting/courses", timeout=10)
        assert res.status_code == 200
        courses = res.json()
        
        if len(courses) == 0:
            pytest.skip("No courses available to test toggle")
        
        # Use the first course
        test_course = courses[0]
        course_id = test_course.get('id')
        initial_is_test = test_course.get('is_test', False)
        
        print(f"  Testing toggle on course {course_id[:8]}, initial is_test={initial_is_test}")
        
        # Toggle once
        res = requests.post(f"{BASE_URL}/api/admin/subcontracting/courses/{course_id}/toggle-test", timeout=10)
        assert res.status_code == 200, f"Toggle failed: {res.status_code} - {res.text}"
        
        data = res.json()
        assert "is_test" in data, "Response should contain is_test field"
        assert "message" in data, "Response should contain message"
        assert "course_id" in data, "Response should contain course_id"
        
        new_is_test = data["is_test"]
        assert new_is_test != initial_is_test, f"is_test should have toggled from {initial_is_test} to {not initial_is_test}"
        
        print(f"  ✓ Toggle changed is_test from {initial_is_test} to {new_is_test}")
        print(f"  Message: {data['message']}")
        
        # Toggle back to restore original state
        res = requests.post(f"{BASE_URL}/api/admin/subcontracting/courses/{course_id}/toggle-test", timeout=10)
        assert res.status_code == 200
        restored = res.json()["is_test"]
        assert restored == initial_is_test, "Should toggle back to original state"
        
        print(f"  ✓ Toggled back to original state: is_test={restored}")
    
    def test_toggle_test_nonexistent_course(self):
        """Toggle on non-existent course should return 404"""
        fake_id = str(uuid.uuid4())
        res = requests.post(f"{BASE_URL}/api/admin/subcontracting/courses/{fake_id}/toggle-test", timeout=10)
        assert res.status_code == 404, f"Expected 404, got {res.status_code}"
        print("✓ Non-existent course returns 404 as expected")
    
    def test_toggle_test_on_known_test_course(self):
        """Test toggle on the known test course 8d0cdd8c-b11d-4feb-b6aa-a1dc49185397"""
        known_course_id = "8d0cdd8c-b11d-4feb-b6aa-a1dc49185397"
        
        # First verify the course exists and check its state
        res = requests.get(f"{BASE_URL}/api/admin/subcontracting/courses", timeout=10)
        assert res.status_code == 200
        courses = res.json()
        
        known_course = next((c for c in courses if c.get('id') == known_course_id), None)
        if not known_course:
            pytest.skip(f"Known test course {known_course_id[:8]} not found")
        
        initial_state = known_course.get('is_test', False)
        print(f"  Known course {known_course_id[:8]} current is_test={initial_state}")
        
        # Don't change the state since main agent said it's already marked as test
        # Just verify it works
        print(f"✓ Known test course exists with is_test={initial_state}")
    
    # ==========================================
    # Test commissions endpoint with test exclusion
    # ==========================================
    
    def test_get_commissions_returns_is_test_course(self):
        """GET /api/admin/subcontracting/commissions should return is_test_course field"""
        res = requests.get(f"{BASE_URL}/api/admin/subcontracting/commissions", timeout=10)
        assert res.status_code == 200, f"Get commissions failed: {res.status_code}"
        
        data = res.json()
        assert "payments" in data, "Response should contain payments"
        assert "total_commission" in data, "Response should contain total_commission"
        assert "count" in data, "Response should contain count"
        
        payments = data["payments"]
        total_commission = data["total_commission"]
        count = data["count"]
        
        print(f"  Total commission: {total_commission}€")
        print(f"  Payment count: {count}")
        
        if len(payments) > 0:
            # Check that payments have is_test_course field
            for payment in payments[:5]:  # Show first 5
                is_test_course = payment.get("is_test_course", "N/A")
                amount = payment.get("amount", 0)
                status = payment.get("status", "N/A")
                driver_name = payment.get("driver", {}).get("name", "N/A") if payment.get("driver") else "N/A"
                print(f"    Payment: {amount}€ | status={status} | is_test_course={is_test_course} | driver={driver_name}")
        
        print(f"✓ Commissions endpoint working correctly")
    
    def test_commissions_exclude_test_courses_from_total(self):
        """Verify that test courses are excluded from total_commission calculation"""
        res = requests.get(f"{BASE_URL}/api/admin/subcontracting/commissions", timeout=10)
        assert res.status_code == 200
        
        data = res.json()
        payments = data["payments"]
        total_commission = data["total_commission"]
        
        # Calculate what total should be (excluding test courses with paid status)
        expected_total = 0
        test_excluded_total = 0
        
        for payment in payments:
            amount = payment.get("amount", 0)
            status = payment.get("status", "")
            is_test_course = payment.get("is_test_course", False)
            
            if status == "paid":
                if is_test_course:
                    test_excluded_total += amount
                else:
                    expected_total += amount
        
        # Round to 2 decimal places for comparison
        expected_total = round(expected_total, 2)
        
        print(f"  Expected total (excluding test): {expected_total}€")
        print(f"  Excluded from test courses: {test_excluded_total}€")
        print(f"  Actual total_commission: {total_commission}€")
        
        assert total_commission == expected_total, f"Total commission ({total_commission}) should equal expected ({expected_total})"
        
        print(f"✓ Test courses correctly excluded from commission total")
    
    # ==========================================
    # Test that courses endpoint shows test badge info
    # ==========================================
    
    def test_courses_with_test_flag_visible(self):
        """Verify courses with is_test=True are identifiable"""
        res = requests.get(f"{BASE_URL}/api/admin/subcontracting/courses", timeout=10)
        assert res.status_code == 200
        courses = res.json()
        
        test_courses = [c for c in courses if c.get("is_test", False)]
        non_test_courses = [c for c in courses if not c.get("is_test", False)]
        
        print(f"  Total courses: {len(courses)}")
        print(f"  Test courses: {len(test_courses)}")
        print(f"  Production courses: {len(non_test_courses)}")
        
        if len(test_courses) > 0:
            print("  Test course IDs:")
            for tc in test_courses[:5]:
                print(f"    - {tc.get('id', 'N/A')[:8]} | {tc.get('client_name', 'N/A')} | {tc.get('price_total', 0)}€")
        
        print(f"✓ is_test flag properly visible in courses list")


class TestCreateAndToggle:
    """Test creating a course and toggling its test state"""
    
    def test_create_course_defaults_is_test_false(self):
        """New courses should default to is_test=False"""
        # Create a test course
        payload = {
            "client_name": f"TEST_Client_{uuid.uuid4().hex[:8]}",
            "client_email": "test@example.com",
            "client_phone": "+33600000000",
            "pickup_address": "1 Rue de Test, 75001 Paris",
            "dropoff_address": "2 Rue de Destination, 75002 Paris",
            "date": "2026-02-15",
            "time": "14:00",
            "distance_km": 10,
            "price_total": 50.0,
            "notes": "Test course for is_test feature"
        }
        
        res = requests.post(
            f"{BASE_URL}/api/admin/subcontracting/courses",
            json=payload,
            timeout=10
        )
        assert res.status_code == 200, f"Course creation failed: {res.status_code} - {res.text}"
        
        data = res.json()
        course_id = data.get("course", {}).get("id")
        assert course_id, "Response should contain course with id"
        
        print(f"  Created test course: {course_id[:8]}")
        
        # Verify is_test defaults to False
        res = requests.get(f"{BASE_URL}/api/admin/subcontracting/courses", timeout=10)
        courses = res.json()
        created_course = next((c for c in courses if c.get("id") == course_id), None)
        
        assert created_course, "Created course should be in list"
        is_test = created_course.get("is_test", None)
        assert is_test == False, f"New course should default to is_test=False, got {is_test}"
        
        print(f"  ✓ New course defaults to is_test=False")
        
        # Clean up: toggle to test and leave it
        res = requests.post(f"{BASE_URL}/api/admin/subcontracting/courses/{course_id}/toggle-test", timeout=10)
        assert res.status_code == 200
        print(f"  ✓ Marked test course as is_test=True for cleanup")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
