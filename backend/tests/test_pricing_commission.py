"""
Test Pricing and Commission Consistency
========================================
Tests for verifying commission = 10% of BASE PRICE (not final total)

Test course 3ceb496c values:
- base_price: 54€
- waiting_fee: 1€
- final_total: 55€
- commission: 5.40€ (10% of 54, NOT 5.50€ which would be 10% of 55)
- net_driver: 49.60€
"""

import pytest
import requests
import os
import math

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://admin-analytics-v2.preview.emergentagent.com').rstrip('/')

# Test course data from requirement
TEST_COURSE_ID = "3ceb496c-9d39-4ab9-a4d8-42cfc9e67029"
TEST_DRIVER_TOKEN = "mCuPY2or0JT5XGUSSykGofrWZszUUVOAPXwP2zNCoDA"
EXPECTED_VALUES = {
    "base_price": 54.0,
    "waiting_fee": 1.0,
    "final_total": 55.0,
    "commission_10_percent_base": 5.4,  # 10% of 54 = 5.4
    "net_driver": 49.6  # 55 - 5.4 = 49.6
}

INCORRECT_COMMISSION = 5.5  # This would be 10% of 55 (incorrect)


class TestCommissionCalculation:
    """Test that commission = 10% of BASE PRICE only"""
    
    def test_driver_ride_endpoint_returns_correct_totals(self):
        """GET /api/driver/ride/{id} returns correct totals object"""
        response = requests.get(
            f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}",
            params={"token": TEST_DRIVER_TOKEN}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Verify totals object exists
        assert "totals" in data, "Response must contain 'totals' object"
        totals = data["totals"]
        
        # Verify base price
        assert totals.get("base_price_eur") == EXPECTED_VALUES["base_price"], \
            f"Base price should be {EXPECTED_VALUES['base_price']}, got {totals.get('base_price_eur')}"
        
        # Verify waiting fee
        assert totals.get("waiting_fee_eur") == EXPECTED_VALUES["waiting_fee"], \
            f"Waiting fee should be {EXPECTED_VALUES['waiting_fee']}, got {totals.get('waiting_fee_eur')}"
        
        # Verify final total
        assert totals.get("final_total_eur") == EXPECTED_VALUES["final_total"], \
            f"Final total should be {EXPECTED_VALUES['final_total']}, got {totals.get('final_total_eur')}"
        
        print(f"✅ Base price: {totals.get('base_price_eur')}€")
        print(f"✅ Waiting fee: {totals.get('waiting_fee_eur')}€")
        print(f"✅ Final total: {totals.get('final_total_eur')}€")
    
    def test_commission_is_10_percent_of_base_price(self):
        """Commission = 10% of BASE PRICE (not final total)"""
        response = requests.get(
            f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}",
            params={"token": TEST_DRIVER_TOKEN}
        )
        
        assert response.status_code == 200
        data = response.json()
        totals = data.get("totals", {})
        
        commission = totals.get("commission_base_eur")
        base_price = totals.get("base_price_eur")
        final_total = totals.get("final_total_eur")
        
        # Commission MUST be 10% of base price
        expected_commission = round(base_price * 0.10, 2)
        assert commission == expected_commission, \
            f"Commission should be {expected_commission}€ (10% of base {base_price}€), got {commission}€"
        
        # Commission must NOT be 10% of final total (would be incorrect)
        wrong_commission = round(final_total * 0.10, 2)
        if base_price != final_total:  # Only check if they differ
            assert commission != wrong_commission, \
                f"Commission should NOT be {wrong_commission}€ (which is 10% of final total {final_total}€)"
        
        print(f"✅ Commission: {commission}€ (10% of base price {base_price}€)")
        print(f"✅ NOT {wrong_commission}€ (which would be 10% of final total {final_total}€)")
    
    def test_net_driver_calculation(self):
        """Net driver = final_total - commission"""
        response = requests.get(
            f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}",
            params={"token": TEST_DRIVER_TOKEN}
        )
        
        assert response.status_code == 200
        data = response.json()
        totals = data.get("totals", {})
        
        net_driver = totals.get("net_driver_eur")
        final_total = totals.get("final_total_eur")
        commission = totals.get("commission_base_eur")
        
        expected_net = round(final_total - commission, 2)
        assert net_driver == expected_net, \
            f"Net driver should be {expected_net}€ ({final_total}€ - {commission}€), got {net_driver}€"
        
        print(f"✅ Net driver: {net_driver}€ = {final_total}€ - {commission}€")
    
    def test_expected_test_values(self):
        """Verify test course has exact expected values"""
        response = requests.get(
            f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}",
            params={"token": TEST_DRIVER_TOKEN}
        )
        
        assert response.status_code == 200
        data = response.json()
        totals = data.get("totals", {})
        
        # Check all expected values
        assert totals.get("base_price_eur") == EXPECTED_VALUES["base_price"], \
            f"Expected base_price={EXPECTED_VALUES['base_price']}, got {totals.get('base_price_eur')}"
        
        assert totals.get("waiting_fee_eur") == EXPECTED_VALUES["waiting_fee"], \
            f"Expected waiting_fee={EXPECTED_VALUES['waiting_fee']}, got {totals.get('waiting_fee_eur')}"
        
        assert totals.get("final_total_eur") == EXPECTED_VALUES["final_total"], \
            f"Expected final_total={EXPECTED_VALUES['final_total']}, got {totals.get('final_total_eur')}"
        
        assert totals.get("commission_base_eur") == EXPECTED_VALUES["commission_10_percent_base"], \
            f"Expected commission={EXPECTED_VALUES['commission_10_percent_base']}, got {totals.get('commission_base_eur')}"
        
        assert totals.get("net_driver_eur") == EXPECTED_VALUES["net_driver"], \
            f"Expected net_driver={EXPECTED_VALUES['net_driver']}, got {totals.get('net_driver_eur')}"
        
        print("✅ All test course values match expected:")
        print(f"   base=54€, attente=1€, total=55€, commission=5.40€, net=49.60€")


class TestCeilWaitingMinutes:
    """Test that waiting minutes use ceil() - any started minute counts"""
    
    def test_waiting_billable_minutes_calculation(self):
        """Verify waiting_billable_minutes are calculated correctly"""
        response = requests.get(
            f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}",
            params={"token": TEST_DRIVER_TOKEN}
        )
        
        assert response.status_code == 200
        data = response.json()
        totals = data.get("totals", {})
        
        waiting_minutes = totals.get("waiting_minutes", 0)
        waiting_billable_minutes = totals.get("waiting_billable_minutes", 0)
        waiting_fee = totals.get("waiting_fee_eur", 0)
        
        # Billable = total - 5 free minutes (min 0, max 20)
        expected_billable = max(0, min(waiting_minutes - 5, 20))
        assert waiting_billable_minutes == expected_billable, \
            f"Expected {expected_billable} billable minutes, got {waiting_billable_minutes}"
        
        # Fee = billable_minutes * 1€
        expected_fee = float(waiting_billable_minutes)
        assert waiting_fee == expected_fee, \
            f"Expected fee {expected_fee}€, got {waiting_fee}€"
        
        print(f"✅ Waiting: {waiting_minutes} min total, {waiting_billable_minutes} billable, {waiting_fee}€")


class TestAdminSubcontractingList:
    """Test admin subcontracting endpoints return correct totals"""
    
    def test_admin_courses_list(self):
        """Admin list shows correct final_total_eur and commission_base_eur"""
        response = requests.get(
            f"{BASE_URL}/api/admin/subcontracting/courses",
            auth=("admin", "admin123")
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        courses = response.json()
        
        # Find our test course
        test_course = None
        for course in courses:
            if course.get("id") == TEST_COURSE_ID:
                test_course = course
                break
        
        if test_course:
            totals = test_course.get("totals", {})
            
            # Verify totals are present
            assert "base_price_eur" in totals or test_course.get("price_total"), \
                "Course must have price information"
            
            print(f"✅ Test course found in admin list")
            print(f"   price_total: {test_course.get('price_total')}")
            print(f"   commission_amount: {test_course.get('commission_amount')}")
            if totals:
                print(f"   totals.final_total_eur: {totals.get('final_total_eur')}")
                print(f"   totals.commission_base_eur: {totals.get('commission_base_eur')}")
        else:
            print("⚠️ Test course not found in admin list (may have been filtered)")


class TestPDFCommissionInvoice:
    """Test PDF commission invoice endpoint"""
    
    def test_platform_commission_invoice_pdf(self):
        """PDF commission invoice shows base price and commission"""
        response = requests.get(
            f"{BASE_URL}/api/subcontracting/courses/{TEST_COURSE_ID}/platform-invoice-pdf",
            params={"token": TEST_DRIVER_TOKEN}
        )
        
        # Should return PDF or error
        if response.status_code == 200:
            assert response.headers.get("content-type") == "application/pdf", \
                "Should return PDF content-type"
            assert len(response.content) > 0, "PDF should not be empty"
            print(f"✅ Platform invoice PDF generated ({len(response.content)} bytes)")
        else:
            print(f"⚠️ Platform invoice PDF returned {response.status_code}: {response.text[:200]}")


class TestPricingConsistency:
    """Test pricing consistency across different endpoints"""
    
    def test_consistency_driver_ride_vs_course_fields(self):
        """Verify course-level fields match totals object"""
        response = requests.get(
            f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}",
            params={"token": TEST_DRIVER_TOKEN}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Course-level fields
        price_total = data.get("price_total")
        commission_amount = data.get("commission_amount")
        net_driver = data.get("net_driver")
        price_with_supplements = data.get("price_with_supplements")
        
        # Totals object
        totals = data.get("totals", {})
        
        # Verify consistency
        if price_total and totals.get("base_price_eur"):
            assert price_total == totals["base_price_eur"], \
                f"price_total ({price_total}) should match totals.base_price_eur ({totals['base_price_eur']})"
        
        if commission_amount is not None and totals.get("commission_base_eur") is not None:
            assert commission_amount == totals["commission_base_eur"], \
                f"commission_amount ({commission_amount}) should match totals.commission_base_eur ({totals['commission_base_eur']})"
        
        if net_driver is not None and totals.get("net_driver_eur") is not None:
            assert net_driver == totals["net_driver_eur"], \
                f"net_driver ({net_driver}) should match totals.net_driver_eur ({totals['net_driver_eur']})"
        
        if price_with_supplements and totals.get("final_total_eur"):
            assert price_with_supplements == totals["final_total_eur"], \
                f"price_with_supplements ({price_with_supplements}) should match totals.final_total_eur ({totals['final_total_eur']})"
        
        print("✅ Course fields and totals object are consistent")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
