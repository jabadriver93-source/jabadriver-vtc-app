"""
Test Driver Documents (BDC and Invoice) for Subcontracted Courses
Tests admin endpoints that generate PDFs au nom du CHAUFFEUR (pas Jabadriver)

Test Course: 3ceb496c-9d39-4ab9-a4d8-42cfc9e67029 (Test Pricing - sous-traitée)
Expected values:
  - Base price: 54€
  - Waiting fee: 1€ (1 minute billable)
  - Final total: 55€
  - Commission: 5.40€ (10% of 54€ BASE PRICE, not 55€)
  - Driver: VTC Express (Jean Dupont)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_COURSE_ID = "3ceb496c-9d39-4ab9-a4d8-42cfc9e67029"

class TestAdminSubcontractingCourses:
    """Test admin subcontracting courses API with calculated totals"""
    
    def test_get_all_courses_returns_totals(self):
        """GET /api/admin/subcontracting/courses returns courses with totals"""
        response = requests.get(f"{BASE_URL}/api/admin/subcontracting/courses")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        courses = response.json()
        assert isinstance(courses, list), "Response should be a list"
        
        # Find test course
        test_course = next((c for c in courses if c.get('id') == TEST_COURSE_ID), None)
        assert test_course is not None, f"Test course {TEST_COURSE_ID} not found"
        
        # Verify totals are present
        assert 'totals' in test_course, "Course should have 'totals' field"
        totals = test_course['totals']
        
        # Verify pricing breakdown
        assert totals.get('base_price_eur') == 54.0, f"Base price should be 54€, got {totals.get('base_price_eur')}"
        assert totals.get('waiting_fee_eur') == 1.0, f"Waiting fee should be 1€, got {totals.get('waiting_fee_eur')}"
        assert totals.get('final_total_eur') == 55.0, f"Final total should be 55€, got {totals.get('final_total_eur')}"
        
        # CRITICAL: Commission should be 10% of BASE price (54€), NOT final total (55€)
        assert totals.get('commission_base_eur') == 5.4, f"Commission should be 5.40€ (10% of 54€), got {totals.get('commission_base_eur')}"
        
        print(f"✅ Test course found with correct totals: base={totals['base_price_eur']}€, waiting={totals['waiting_fee_eur']}€, total={totals['final_total_eur']}€, commission={totals['commission_base_eur']}€")
    
    def test_course_has_assigned_driver(self):
        """Test course should have driver VTC Express assigned"""
        response = requests.get(f"{BASE_URL}/api/admin/subcontracting/courses")
        assert response.status_code == 200
        
        courses = response.json()
        test_course = next((c for c in courses if c.get('id') == TEST_COURSE_ID), None)
        assert test_course is not None
        
        # Verify assigned driver
        assert test_course.get('assigned_driver_id') is not None, "Course should have assigned_driver_id"
        assert test_course.get('assigned_driver') is not None, "Course should have assigned_driver details"
        
        driver = test_course['assigned_driver']
        assert driver.get('company_name') == 'VTC Express', f"Driver should be VTC Express, got {driver.get('company_name')}"
        
        print(f"✅ Course assigned to driver: {driver['company_name']} ({driver['name']})")


class TestDriverBonCommandePDF:
    """Test driver bon de commande PDF endpoint"""
    
    def test_driver_bdc_pdf_returns_pdf(self):
        """GET /api/admin/subcontracting/courses/{id}/driver-bon-commande-pdf returns PDF"""
        response = requests.get(f"{BASE_URL}/api/admin/subcontracting/courses/{TEST_COURSE_ID}/driver-bon-commande-pdf")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.headers.get('content-type') == 'application/pdf', f"Expected PDF, got {response.headers.get('content-type')}"
        
        # Verify it's a valid PDF (starts with %PDF)
        content = response.content
        assert content[:4] == b'%PDF', "Response should be a valid PDF file"
        
        # Check filename in Content-Disposition
        content_disp = response.headers.get('content-disposition', '')
        assert 'bdc_chauffeur' in content_disp, f"Filename should contain 'bdc_chauffeur', got {content_disp}"
        
        print(f"✅ Driver BDC PDF generated: {len(content)} bytes, filename: {content_disp}")
    
    def test_driver_bdc_pdf_returns_404_for_unknown_course(self):
        """GET with invalid course ID returns 404"""
        response = requests.get(f"{BASE_URL}/api/admin/subcontracting/courses/invalid-course-id/driver-bon-commande-pdf")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


class TestDriverInvoicePDF:
    """Test driver invoice PDF endpoint"""
    
    def test_driver_invoice_pdf_returns_pdf(self):
        """GET /api/admin/subcontracting/courses/{id}/driver-invoice-pdf returns PDF"""
        response = requests.get(f"{BASE_URL}/api/admin/subcontracting/courses/{TEST_COURSE_ID}/driver-invoice-pdf")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.headers.get('content-type') == 'application/pdf', f"Expected PDF, got {response.headers.get('content-type')}"
        
        # Verify it's a valid PDF (starts with %PDF)
        content = response.content
        assert content[:4] == b'%PDF', "Response should be a valid PDF file"
        
        # Check filename in Content-Disposition
        content_disp = response.headers.get('content-disposition', '')
        assert 'facture_chauffeur' in content_disp, f"Filename should contain 'facture_chauffeur', got {content_disp}"
        
        print(f"✅ Driver Invoice PDF generated: {len(content)} bytes, filename: {content_disp}")
    
    def test_driver_invoice_pdf_returns_404_for_unknown_course(self):
        """GET with invalid course ID returns 404"""
        response = requests.get(f"{BASE_URL}/api/admin/subcontracting/courses/invalid-course-id/driver-invoice-pdf")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


class TestNonSubcontractedReservation:
    """Test that non-subcontracted reservations use normal BDC/Invoice endpoints"""
    
    def test_driver_bdc_returns_400_for_non_subcontracted(self):
        """Driver BDC endpoint returns 400 for course without assigned_driver_id"""
        # This test would need a non-subcontracted course
        # Skip for now since all test courses may be subcontracted
        pytest.skip("Requires a non-subcontracted course to test")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
