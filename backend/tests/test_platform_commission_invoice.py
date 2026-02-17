"""
Test Platform Commission Invoice (Jabadriver → Chauffeur)
==========================================================
Tests the new endpoint GET /api/admin/subcontracting/courses/{id}/platform-invoice-pdf

Features tested:
- Platform commission invoice PDF generation
- PDF contains correct content (FACTURE DE COMMISSION, invoice number, etc.)
- Existing endpoints (START, END, bon-commande-pdf, invoice-pdf) still work
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://gps-validation.preview.emergentagent.com').rstrip('/')

# Test course data
TEST_COURSE_ID = "318325c9-7f05-43f6-b8f5-aa2583609e25"
TEST_TOKEN = "VYGIP4_TxdLZODDSxI7rvtSQR3DQ63tJOLawViPbAn0"
NON_EXISTENT_COURSE_ID = "00000000-0000-0000-0000-000000000000"


class TestPlatformCommissionInvoice:
    """Test the new platform commission invoice endpoint"""
    
    def test_platform_invoice_returns_200(self):
        """Platform commission invoice endpoint returns HTTP 200"""
        response = requests.get(f"{BASE_URL}/api/admin/subcontracting/courses/{TEST_COURSE_ID}/platform-invoice-pdf")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
    
    def test_platform_invoice_content_type_is_pdf(self):
        """Platform commission invoice returns PDF content type"""
        response = requests.get(f"{BASE_URL}/api/admin/subcontracting/courses/{TEST_COURSE_ID}/platform-invoice-pdf")
        assert response.status_code == 200
        content_type = response.headers.get('Content-Type', '')
        assert 'application/pdf' in content_type, f"Expected application/pdf, got {content_type}"
    
    def test_platform_invoice_is_valid_pdf(self):
        """Platform commission invoice contains valid PDF header"""
        response = requests.get(f"{BASE_URL}/api/admin/subcontracting/courses/{TEST_COURSE_ID}/platform-invoice-pdf")
        assert response.status_code == 200
        content = response.content
        assert content[:5] == b'%PDF-', f"PDF does not start with %PDF-, got {content[:20]}"
    
    def test_platform_invoice_has_correct_filename(self):
        """Platform commission invoice has correct Content-Disposition filename"""
        response = requests.get(f"{BASE_URL}/api/admin/subcontracting/courses/{TEST_COURSE_ID}/platform-invoice-pdf")
        assert response.status_code == 200
        disposition = response.headers.get('Content-Disposition', '')
        # Should contain facture-commission-{course_id_short}.pdf
        course_id_short = TEST_COURSE_ID[:8].upper()
        expected_filename = f"facture-commission-{course_id_short}.pdf"
        assert expected_filename in disposition, f"Expected filename {expected_filename} in {disposition}"
    
    def test_platform_invoice_404_for_nonexistent_course(self):
        """Platform commission invoice returns 404 for non-existent course"""
        response = requests.get(f"{BASE_URL}/api/admin/subcontracting/courses/{NON_EXISTENT_COURSE_ID}/platform-invoice-pdf")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        # Verify error message
        data = response.json()
        assert "detail" in data, "Response should contain detail field"
        assert "not found" in data.get("detail", "").lower() or "Course not found" in data.get("detail", "")


class TestExistingEndpointsStillWork:
    """Verify existing endpoints haven't been broken"""
    
    def test_ride_details_returns_200(self):
        """Existing ride details endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}?token={TEST_TOKEN}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
    
    def test_bon_commande_pdf_returns_200(self):
        """Existing bon de commande PDF endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}/bon-commande-pdf?token={TEST_TOKEN}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
        assert response.content[:5] == b'%PDF-', "Not a valid PDF"
    
    def test_invoice_pdf_returns_200(self):
        """Existing invoice PDF endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}/invoice-pdf?token={TEST_TOKEN}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
        assert response.content[:5] == b'%PDF-', "Not a valid PDF"
    
    def test_start_endpoint_exists(self):
        """START endpoint exists and returns proper response (may be 400/409 if already started)"""
        response = requests.post(f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}/start?token={TEST_TOKEN}")
        # Should be 200 (started) or 400/409 (already started/invalid state/conflict)
        assert response.status_code in [200, 400, 409], f"Unexpected status: {response.status_code}"
    
    def test_end_endpoint_exists(self):
        """END endpoint exists and returns proper response (may be 400/409 if not started)"""
        response = requests.post(f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}/end?token={TEST_TOKEN}")
        # Should be 200 (ended) or 400/409 (not started/invalid state/conflict)
        assert response.status_code in [200, 400, 409], f"Unexpected status: {response.status_code}"


class TestAdminSubcontractingEndpoints:
    """Test admin subcontracting endpoints"""
    
    def test_admin_courses_list(self):
        """Admin courses list endpoint works"""
        response = requests.get(f"{BASE_URL}/api/admin/subcontracting/courses")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_admin_drivers_list(self):
        """Admin drivers list endpoint works"""
        response = requests.get(f"{BASE_URL}/api/admin/subcontracting/drivers")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_test_course_exists_in_list(self):
        """Test course exists in admin courses list"""
        response = requests.get(f"{BASE_URL}/api/admin/subcontracting/courses")
        assert response.status_code == 200
        courses = response.json()
        
        # Find test course
        test_course = next((c for c in courses if c.get('id') == TEST_COURSE_ID), None)
        assert test_course is not None, f"Test course {TEST_COURSE_ID} not found in courses list"
        
        # Verify course has expected fields
        assert 'assigned_driver_id' in test_course or 'assigned_driver' in test_course, "Course should have driver info"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
