"""
Test Admin Dashboard Filter and Financial Data Features
- Course type filter (Toutes/Mes courses/Sous-traitées)
- Financial data in API (final_price_eur, base_price_eur, supplements_eur, commission_eur)
- is_subcontracted flag
- CA stats with breakdown (direct vs subcontracted)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAdminDashboardFilters:
    """Test Admin Dashboard filter and financial data features"""
    
    def test_api_reservations_returns_is_subcontracted(self):
        """GET /api/reservations should return is_subcontracted field for all reservations"""
        response = requests.get(f"{BASE_URL}/api/reservations")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) > 0, "Should have at least one reservation"
        
        # Check that is_subcontracted field exists
        for res in data[:5]:  # Check first 5
            assert "is_subcontracted" in res, f"Missing is_subcontracted field in reservation {res.get('id')}"
            assert isinstance(res["is_subcontracted"], bool), "is_subcontracted should be boolean"
    
    def test_api_reservations_returns_financial_data(self):
        """GET /api/reservations should return financial_data for subcontracted courses"""
        response = requests.get(f"{BASE_URL}/api/reservations")
        assert response.status_code == 200
        
        data = response.json()
        
        # Find subcontracted reservations
        subcontracted = [r for r in data if r.get("is_subcontracted")]
        assert len(subcontracted) > 0, "Should have at least one subcontracted reservation"
        
        # Check financial_data structure
        for res in subcontracted:
            fd = res.get("financial_data")
            assert fd is not None, f"Subcontracted reservation {res.get('name')} should have financial_data"
            
            # Verify all required fields
            required_fields = ["final_price_eur", "base_price_eur", "supplements_eur", "commission_eur", "driver_revenue_eur"]
            for field in required_fields:
                assert field in fd, f"financial_data should contain {field}"
    
    def test_filter_subcontracted_courses(self):
        """GET /api/reservations?course_type=subcontracted should return only subcontracted courses"""
        response = requests.get(f"{BASE_URL}/api/reservations?course_type=subcontracted")
        assert response.status_code == 200
        
        data = response.json()
        # All returned should be subcontracted
        for res in data:
            assert res.get("is_subcontracted") == True, f"Course {res.get('name')} should be subcontracted"
    
    def test_filter_direct_courses(self):
        """GET /api/reservations?course_type=direct should return only direct (non-subcontracted) courses"""
        response = requests.get(f"{BASE_URL}/api/reservations?course_type=direct")
        assert response.status_code == 200
        
        data = response.json()
        # All returned should NOT be subcontracted
        for res in data:
            assert res.get("is_subcontracted") == False, f"Course {res.get('name')} should NOT be subcontracted"
    
    def test_test_pricing_reservation_data(self):
        """Verify 'Test Pricing (Sous-traitée)' has correct financial data"""
        response = requests.get(f"{BASE_URL}/api/reservations")
        assert response.status_code == 200
        
        data = response.json()
        
        # Find the test pricing reservation
        test_pricing = None
        for res in data:
            if "Pricing" in res.get("name", "") and res.get("is_subcontracted"):
                test_pricing = res
                break
        
        if test_pricing is None:
            pytest.skip("Test Pricing (Sous-traitée) reservation not found")
        
        fd = test_pricing.get("financial_data", {})
        
        # Verify the expected values
        assert fd.get("final_price_eur") == 55.0, f"Expected final_price 55€, got {fd.get('final_price_eur')}"
        assert fd.get("base_price_eur") == 54.0, f"Expected base_price 54€, got {fd.get('base_price_eur')}"
        assert fd.get("supplements_eur") == 1.0, f"Expected supplements 1€, got {fd.get('supplements_eur')}"
        
        # Commission should be 10% of BASE price (54€ * 10% = 5.40€)
        assert abs(fd.get("commission_eur", 0) - 5.4) < 0.01, f"Expected commission 5.40€, got {fd.get('commission_eur')}"
    
    def test_commission_calculated_from_base_price(self):
        """Verify commission is calculated from base price, not final price"""
        response = requests.get(f"{BASE_URL}/api/reservations")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check subcontracted reservations
        subcontracted = [r for r in data if r.get("is_subcontracted") and r.get("financial_data")]
        
        for res in subcontracted:
            fd = res.get("financial_data", {})
            base_price = fd.get("base_price_eur", 0)
            commission = fd.get("commission_eur", 0)
            
            if base_price > 0:
                # Commission should be 10% of base price
                expected_commission = base_price * 0.10
                assert abs(commission - expected_commission) < 0.01, \
                    f"Commission for {res.get('name')} should be {expected_commission}€ (10% of base {base_price}€), got {commission}€"


class TestStatsCalculation:
    """Test CA stats calculation with direct/subcontracted breakdown"""
    
    def test_revenue_breakdown_calculation(self):
        """Verify total revenue equals direct + subcontracted revenue"""
        response = requests.get(f"{BASE_URL}/api/reservations")
        assert response.status_code == 200
        
        data = response.json()
        
        # Calculate totals (excluding test reservations)
        total_revenue = 0
        direct_revenue = 0
        subcontracted_revenue = 0
        
        for res in data:
            if res.get("is_test"):
                continue
            
            fd = res.get("financial_data")
            if fd:
                final_price = fd.get("final_price_eur", 0)
            else:
                # For non-subcontracted without financial_data, use estimated_price
                final_price = res.get("estimated_price", 0) or res.get("final_price", 0) or 0
            
            total_revenue += final_price
            
            if res.get("is_subcontracted"):
                subcontracted_revenue += final_price
            else:
                direct_revenue += final_price
        
        # Verify breakdown
        assert abs(total_revenue - (direct_revenue + subcontracted_revenue)) < 0.01, \
            f"Total ({total_revenue}) should equal direct ({direct_revenue}) + subcontracted ({subcontracted_revenue})"
        
        print(f"\nRevenue breakdown:")
        print(f"  Total: {total_revenue:.2f}€")
        print(f"  Direct (🏠): {direct_revenue:.2f}€")
        print(f"  Subcontracted (🚚): {subcontracted_revenue:.2f}€")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
