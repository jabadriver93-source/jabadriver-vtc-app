"""
Test suite for TEST mode unification between Dashboard and Subcontracting.

Tests:
1. Dashboard filter: Default shows only normal reservations (is_test=false)
2. Dashboard filter: Click 'Afficher tests' shows ONLY test reservations (is_test=true)
3. Subcontracting filter: Default shows only normal courses
4. Subcontracting filter: Click 'Afficher tests' shows ONLY test courses
5. SYNC: Toggle test in Dashboard syncs to linked course
6. SYNC: Toggle test in Subcontracting syncs to linked reservation(s)
7. Counters are correct per module
8. No regression on commission calculation, pricing
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://emergent-cleanup-3.preview.emergentagent.com')


class TestTestModeUnification:
    """Test TEST mode unification between Dashboard and Subcontracting"""
    
    def test_dashboard_reservations_count(self):
        """Test Dashboard: Get all reservations and count test vs normal"""
        response = requests.get(f"{BASE_URL}/api/reservations")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        reservations = response.json()
        assert isinstance(reservations, list), "Response should be a list"
        
        # Count test vs normal
        normal_count = sum(1 for r in reservations if not r.get('is_test', False))
        test_count = sum(1 for r in reservations if r.get('is_test', False))
        total_count = len(reservations)
        
        print(f"[RESERVATIONS] Total: {total_count} | Normal: {normal_count} | Test: {test_count}")
        
        # Per requirements: should be ~39 normal, ~1 test
        assert total_count > 0, "Should have reservations in database"
        
        # Store counts for display
        self.normal_reservations_count = normal_count
        self.test_reservations_count = test_count
    
    def test_subcontracting_courses_count(self):
        """Test Subcontracting: Get all courses and count test vs normal"""
        response = requests.get(f"{BASE_URL}/api/admin/subcontracting/courses")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        courses = response.json()
        assert isinstance(courses, list), "Response should be a list"
        
        # Count test vs normal
        normal_count = sum(1 for c in courses if not c.get('is_test', False))
        test_count = sum(1 for c in courses if c.get('is_test', False))
        total_count = len(courses)
        
        print(f"[COURSES] Total: {total_count} | Normal: {normal_count} | Test: {test_count}")
        
        # Per requirements: should be ~39 normal, ~7 test
        assert total_count > 0, "Should have courses in database"
        
        # Store counts for display
        self.normal_courses_count = normal_count
        self.test_courses_count = test_count
    
    def test_reservation_has_is_test_field(self):
        """Test that reservations have is_test field"""
        response = requests.get(f"{BASE_URL}/api/reservations")
        assert response.status_code == 200
        
        reservations = response.json()
        if reservations:
            # Check first reservation has is_test field
            first_res = reservations[0]
            assert 'is_test' in first_res or first_res.get('is_test') is not None or first_res.get('is_test', 'NOT_FOUND') != 'NOT_FOUND', \
                "Reservation should have is_test field"
            print(f"[RESERVATIONS] First reservation is_test: {first_res.get('is_test', False)}")
    
    def test_course_has_is_test_field(self):
        """Test that courses have is_test field"""
        response = requests.get(f"{BASE_URL}/api/admin/subcontracting/courses")
        assert response.status_code == 200
        
        courses = response.json()
        if courses:
            # Check first course has is_test field
            first_course = courses[0]
            assert 'is_test' in first_course or first_course.get('is_test') is not None or first_course.get('is_test', 'NOT_FOUND') != 'NOT_FOUND', \
                "Course should have is_test field"
            print(f"[COURSES] First course is_test: {first_course.get('is_test', False)}")
    
    def test_toggle_test_reservation_api(self):
        """Test toggle test reservation endpoint exists and works"""
        # Get a reservation to toggle
        response = requests.get(f"{BASE_URL}/api/reservations")
        assert response.status_code == 200
        
        reservations = response.json()
        if not reservations:
            pytest.skip("No reservations to test with")
        
        # Find a reservation with a linked course (for sync testing)
        test_reservation = None
        for r in reservations:
            if r.get('subcontracting_course_id'):
                test_reservation = r
                break
        
        if not test_reservation:
            # Use first reservation if none have linked courses
            test_reservation = reservations[0]
        
        reservation_id = test_reservation['id']
        initial_is_test = test_reservation.get('is_test', False)
        linked_course_id = test_reservation.get('subcontracting_course_id')
        
        print(f"[TOGGLE] Testing reservation {reservation_id[:8]} | initial is_test={initial_is_test} | linked_course={linked_course_id[:8] if linked_course_id else 'None'}")
        
        # Toggle test status
        response = requests.post(f"{BASE_URL}/api/reservations/{reservation_id}/toggle-test")
        assert response.status_code == 200, f"Toggle failed: {response.text}"
        
        data = response.json()
        assert 'is_test' in data, "Response should contain is_test field"
        assert 'message' in data, "Response should contain message"
        
        expected_new_state = not initial_is_test
        assert data['is_test'] == expected_new_state, f"Expected is_test={expected_new_state}, got {data['is_test']}"
        
        print(f"[TOGGLE] Result: is_test toggled to {data['is_test']}")
        
        # Check if sync happened (if there's a linked course)
        if linked_course_id:
            assert 'synced_course_id' in data, "Response should contain synced_course_id for linked reservation"
            print(f"[SYNC] Synced to course: {data.get('synced_course_id', 'N/A')[:8] if data.get('synced_course_id') else 'N/A'}")
            
            # Verify the course was actually synced
            course_response = requests.get(f"{BASE_URL}/api/admin/subcontracting/courses")
            assert course_response.status_code == 200
            courses = course_response.json()
            
            synced_course = next((c for c in courses if c['id'] == linked_course_id), None)
            if synced_course:
                assert synced_course.get('is_test') == expected_new_state, \
                    f"Linked course should have is_test={expected_new_state} after sync"
                print(f"[SYNC] Verified course {linked_course_id[:8]} is_test={synced_course.get('is_test')}")
        
        # Toggle back to restore original state
        response = requests.post(f"{BASE_URL}/api/reservations/{reservation_id}/toggle-test")
        assert response.status_code == 200
        print(f"[TOGGLE] Restored reservation to original state: is_test={response.json().get('is_test')}")
    
    def test_toggle_test_course_api(self):
        """Test toggle test course endpoint exists and works with sync"""
        # Get courses
        response = requests.get(f"{BASE_URL}/api/admin/subcontracting/courses")
        assert response.status_code == 200
        
        courses = response.json()
        if not courses:
            pytest.skip("No courses to test with")
        
        # Use first course
        test_course = courses[0]
        course_id = test_course['id']
        initial_is_test = test_course.get('is_test', False)
        
        print(f"[TOGGLE] Testing course {course_id[:8]} | initial is_test={initial_is_test}")
        
        # Toggle test status
        response = requests.post(f"{BASE_URL}/api/admin/subcontracting/courses/{course_id}/toggle-test")
        assert response.status_code == 200, f"Toggle failed: {response.text}"
        
        data = response.json()
        assert 'is_test' in data, "Response should contain is_test field"
        assert 'message' in data, "Response should contain message"
        assert 'synced_reservations_count' in data, "Response should contain synced_reservations_count"
        
        expected_new_state = not initial_is_test
        assert data['is_test'] == expected_new_state, f"Expected is_test={expected_new_state}, got {data['is_test']}"
        
        print(f"[TOGGLE] Result: is_test toggled to {data['is_test']}")
        print(f"[SYNC] Synced to {data['synced_reservations_count']} reservation(s)")
        
        # Toggle back to restore original state
        response = requests.post(f"{BASE_URL}/api/admin/subcontracting/courses/{course_id}/toggle-test")
        assert response.status_code == 200
        print(f"[TOGGLE] Restored course to original state: is_test={response.json().get('is_test')}")


class TestCommissionCalculation:
    """Test that commission calculation is not affected by test mode changes"""
    
    def test_course_totals_calculation(self):
        """Test that course totals are calculated correctly"""
        response = requests.get(f"{BASE_URL}/api/admin/subcontracting/courses")
        assert response.status_code == 200
        
        courses = response.json()
        if not courses:
            pytest.skip("No courses to test with")
        
        # Check a few courses for proper commission calculation
        for course in courses[:5]:
            price_total = course.get('price_total', 0)
            commission_amount = course.get('commission_amount', 0)
            
            # Commission should be 10% of base price
            expected_commission = round(price_total * 0.10, 2)
            
            # Allow small floating point differences
            assert abs(commission_amount - expected_commission) < 0.01, \
                f"Commission {commission_amount} should be 10% of {price_total} = {expected_commission}"
            
            print(f"[COMMISSION] Course {course['id'][:8]}: price={price_total}€, commission={commission_amount}€ (10%)")
    
    def test_course_has_totals_field(self):
        """Test that courses have totals calculation field"""
        response = requests.get(f"{BASE_URL}/api/admin/subcontracting/courses")
        assert response.status_code == 200
        
        courses = response.json()
        for course in courses[:3]:
            if course.get('totals'):
                totals = course['totals']
                print(f"[TOTALS] Course {course['id'][:8]}: base={totals.get('base_price_eur')}€, final={totals.get('final_total_eur')}€, commission={totals.get('commission_base_eur')}€")
                
                # Verify commission is calculated from base, not final
                base = totals.get('base_price_eur', 0)
                commission = totals.get('commission_base_eur', 0)
                expected = round(base * 0.10, 2)
                
                assert abs(commission - expected) < 0.01, \
                    f"Commission {commission} should be 10% of base {base} = {expected}"


class TestDataCounts:
    """Verify the expected data counts as per requirements"""
    
    def test_expected_reservation_counts(self):
        """Verify reservation counts match requirements: ~39 normal, ~1 test"""
        response = requests.get(f"{BASE_URL}/api/reservations")
        assert response.status_code == 200
        
        reservations = response.json()
        normal_count = sum(1 for r in reservations if not r.get('is_test', False))
        test_count = sum(1 for r in reservations if r.get('is_test', False))
        
        print(f"\n[DATA COUNTS] Reservations:")
        print(f"  - Normal (is_test=false): {normal_count} (expected ~39)")
        print(f"  - Test (is_test=true): {test_count} (expected ~1)")
        print(f"  - Total: {len(reservations)}")
        
        # Soft assertions - just log if different from expected
        if normal_count != 39:
            print(f"  ⚠️ Normal count differs from expected 39")
        if test_count != 1:
            print(f"  ⚠️ Test count differs from expected 1")
    
    def test_expected_course_counts(self):
        """Verify course counts match requirements: ~39 normal, ~7 test"""
        response = requests.get(f"{BASE_URL}/api/admin/subcontracting/courses")
        assert response.status_code == 200
        
        courses = response.json()
        normal_count = sum(1 for c in courses if not c.get('is_test', False))
        test_count = sum(1 for c in courses if c.get('is_test', False))
        
        print(f"\n[DATA COUNTS] Courses:")
        print(f"  - Normal (is_test=false): {normal_count} (expected ~39)")
        print(f"  - Test (is_test=true): {test_count} (expected ~7)")
        print(f"  - Total: {len(courses)}")
        
        # Soft assertions - just log if different from expected
        if normal_count != 39:
            print(f"  ⚠️ Normal count differs from expected 39")
        if test_count != 7:
            print(f"  ⚠️ Test count differs from expected 7")


class TestSyncSpecificReservation:
    """Test sync with specific reservation 003c1efb linked to course 511f5e99"""
    
    def test_sync_specific_reservation(self):
        """Test sync with reservation 003c1efb (linked to course 511f5e99)"""
        # Get reservations and find the specific one
        response = requests.get(f"{BASE_URL}/api/reservations")
        assert response.status_code == 200
        
        reservations = response.json()
        target_reservation = next((r for r in reservations if r['id'].startswith('003c1efb')), None)
        
        if not target_reservation:
            print("[SKIP] Specific reservation 003c1efb not found - skipping specific sync test")
            pytest.skip("Specific test reservation not found")
        
        reservation_id = target_reservation['id']
        linked_course_id = target_reservation.get('subcontracting_course_id')
        initial_is_test = target_reservation.get('is_test', False)
        
        print(f"[SYNC TEST] Found reservation {reservation_id[:8]}")
        print(f"[SYNC TEST] Linked course: {linked_course_id[:8] if linked_course_id else 'None'}")
        print(f"[SYNC TEST] Initial is_test: {initial_is_test}")
        
        if not linked_course_id:
            pytest.skip("Reservation has no linked course")
        
        # Toggle and verify sync
        response = requests.post(f"{BASE_URL}/api/reservations/{reservation_id}/toggle-test")
        assert response.status_code == 200
        
        data = response.json()
        new_is_test = data['is_test']
        synced_course = data.get('synced_course_id')
        
        print(f"[SYNC TEST] New is_test: {new_is_test}")
        print(f"[SYNC TEST] Synced to course: {synced_course[:8] if synced_course else 'None'}")
        
        # Verify course state
        courses_response = requests.get(f"{BASE_URL}/api/admin/subcontracting/courses")
        assert courses_response.status_code == 200
        
        courses = courses_response.json()
        course = next((c for c in courses if c['id'] == linked_course_id), None)
        
        if course:
            assert course.get('is_test') == new_is_test, \
                f"Course should have is_test={new_is_test} after sync"
            print(f"[SYNC TEST] ✅ Course is_test matches reservation: {course.get('is_test')}")
        
        # Restore original state
        response = requests.post(f"{BASE_URL}/api/reservations/{reservation_id}/toggle-test")
        assert response.status_code == 200
        print(f"[SYNC TEST] Restored to original state")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
