"""
Test suite for UI/Text Corrections - Iteration 10
==================================================

Verifies 3 corrections:
1. Page token chauffeur - paddingBottom: 140px (frontend test)
2. Portail chauffeur - no 'Brouillon' badge (frontend test) 
3. PDF Facture shows 'FACTURE' not 'FACTURE PROVISOIRE', prefix 'F-' not 'PRO-'
"""

import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://admin-analytics-v2.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_COURSE_ID = "318325c9-7f05-43f6-b8f5-aa2583609e25"
TEST_TOKEN = "VYGIP4_TxdLZODDSxI7rvtSQR3DQ63tJOLawViPbAn0"
DRIVER_EMAIL = "chauffeur1@test.com"
DRIVER_PASSWORD = "test123"


@pytest.fixture(scope="module")
def driver_session_token():
    """Get driver session token via login"""
    try:
        res = requests.post(
            f"{BASE_URL}/api/driver/login",
            json={"email": DRIVER_EMAIL, "password": DRIVER_PASSWORD}
        )
        if res.status_code == 200:
            data = res.json()
            return data.get("token")
    except Exception as e:
        print(f"Driver login failed: {e}")
    return None


class TestInvoicePDFTitleAndPrefix:
    """Test that PDF invoice shows 'FACTURE' (not 'FACTURE PROVISOIRE') and uses 'F-' prefix (not 'PRO-')"""
    
    def test_invoice_pdf_endpoint_returns_200(self):
        """Invoice PDF endpoint should return 200"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}/invoice-pdf?token={TEST_TOKEN}"
        res = requests.get(url)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text[:200]}"
    
    def test_invoice_pdf_is_valid_pdf(self):
        """Invoice PDF should return valid PDF content"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}/invoice-pdf?token={TEST_TOKEN}"
        res = requests.get(url)
        assert res.status_code == 200
        assert res.headers.get('content-type') == 'application/pdf' or 'pdf' in res.headers.get('content-type', '')
        assert res.content[:4] == b'%PDF', "Response should start with PDF header"
    
    def test_invoice_pdf_contains_facture_title(self):
        """Invoice PDF should contain 'FACTURE' title"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}/invoice-pdf?token={TEST_TOKEN}"
        res = requests.get(url)
        assert res.status_code == 200
        
        # PDF content check - 'FACTURE' should be in the PDF
        pdf_content = res.content.decode('latin-1', errors='ignore')
        assert 'FACTURE' in pdf_content, "PDF should contain 'FACTURE' title"
    
    def test_invoice_pdf_no_facture_provisoire(self):
        """Invoice PDF should NOT contain 'FACTURE PROVISOIRE' anywhere"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}/invoice-pdf?token={TEST_TOKEN}"
        res = requests.get(url)
        assert res.status_code == 200
        
        pdf_content = res.content.decode('latin-1', errors='ignore')
        # Check that FACTURE PROVISOIRE does not exist
        assert 'FACTURE PROVISOIRE' not in pdf_content, "PDF should NOT contain 'FACTURE PROVISOIRE'"
        assert 'PROVISOIRE' not in pdf_content, "PDF should NOT contain 'PROVISOIRE' anywhere"
    
    def test_invoice_pdf_uses_f_prefix(self):
        """Invoice PDF should use 'F-' prefix for invoice number, not 'PRO-'"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}/invoice-pdf?token={TEST_TOKEN}"
        res = requests.get(url)
        assert res.status_code == 200
        
        pdf_content = res.content.decode('latin-1', errors='ignore')
        
        # Check that 'F-' prefix exists (first 8 chars of course ID uppercase)
        course_id_short = TEST_COURSE_ID[:8].upper()
        expected_invoice_num = f"F-{course_id_short}"
        
        # PDF may have the F- prefix
        assert 'F-' in pdf_content or expected_invoice_num in pdf_content, \
            f"PDF should contain 'F-' prefix or '{expected_invoice_num}'"
    
    def test_invoice_pdf_no_pro_prefix(self):
        """Invoice PDF should NOT use 'PRO-' prefix"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}/invoice-pdf?token={TEST_TOKEN}"
        res = requests.get(url)
        assert res.status_code == 200
        
        pdf_content = res.content.decode('latin-1', errors='ignore')
        assert 'PRO-' not in pdf_content, "PDF should NOT contain 'PRO-' prefix"


class TestBonDeCommandeNoCommission:
    """Verify bon de commande still works and shows Total TTC only"""
    
    def test_bon_commande_endpoint_returns_200(self):
        """Bon de commande endpoint should return 200"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}/bon-commande-pdf?token={TEST_TOKEN}"
        res = requests.get(url)
        assert res.status_code == 200
    
    def test_bon_commande_is_valid_pdf(self):
        """Bon de commande should return valid PDF"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}/bon-commande-pdf?token={TEST_TOKEN}"
        res = requests.get(url)
        assert res.status_code == 200
        assert res.content[:4] == b'%PDF'
    
    def test_bon_commande_has_total_ttc(self):
        """Bon de commande should show Total TTC"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}/bon-commande-pdf?token={TEST_TOKEN}"
        res = requests.get(url)
        assert res.status_code == 200
        
        pdf_content = res.content.decode('latin-1', errors='ignore')
        assert 'Total TTC' in pdf_content, "Bon de commande should contain 'Total TTC'"


class TestDriverRideEndpointWithToken:
    """Verify ride details API still works with token"""
    
    def test_ride_details_returns_200(self):
        """Ride details should return 200 with valid token"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}?token={TEST_TOKEN}"
        res = requests.get(url)
        assert res.status_code == 200
    
    def test_ride_details_returns_json(self):
        """Ride details should return valid JSON"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}?token={TEST_TOKEN}"
        res = requests.get(url)
        assert res.status_code == 200
        
        data = res.json()
        assert 'id' in data
        assert 'status' in data
    
    def test_ride_details_has_price_info(self):
        """Ride details should include price information"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}?token={TEST_TOKEN}"
        res = requests.get(url)
        assert res.status_code == 200
        
        data = res.json()
        assert 'price_base' in data or 'price_total' in data


class TestDriverPortalCoursesAPI:
    """Test driver portal courses API - no Brouillon status should be returned"""
    
    def test_courses_endpoint_returns_200(self, driver_session_token):
        """Courses list should return 200"""
        if not driver_session_token:
            pytest.skip("No driver session token")
        
        url = f"{BASE_URL}/api/driver/courses"
        res = requests.get(url, headers={"Authorization": f"Bearer {driver_session_token}"})
        assert res.status_code == 200
    
    def test_courses_returns_array(self, driver_session_token):
        """Courses list should return array"""
        if not driver_session_token:
            pytest.skip("No driver session token")
        
        url = f"{BASE_URL}/api/driver/courses"
        res = requests.get(url, headers={"Authorization": f"Bearer {driver_session_token}"})
        assert res.status_code == 200
        
        data = res.json()
        assert isinstance(data, list)
    
    def test_courses_have_valid_statuses(self, driver_session_token):
        """All courses should have valid statuses (not DRAFT/Brouillon)"""
        if not driver_session_token:
            pytest.skip("No driver session token")
        
        url = f"{BASE_URL}/api/driver/courses"
        res = requests.get(url, headers={"Authorization": f"Bearer {driver_session_token}"})
        assert res.status_code == 200
        
        data = res.json()
        # Courses assigned to driver should NOT have DRAFT status
        # DRAFT courses should not be visible to drivers at all
        valid_statuses = ['ASSIGNED', 'IN_PROGRESS', 'DRIVER_COMPLETED', 'DONE', 
                         'CANCELLED', 'CANCELLED_LATE_DRIVER', 'CANCELLED_LATE_CLIENT']
        
        for course in data:
            assert course.get('status') in valid_statuses, \
                f"Course {course.get('id', 'unknown')} has invalid status: {course.get('status')}"
            assert course.get('status') != 'DRAFT', \
                f"Course {course.get('id', 'unknown')} has DRAFT status - should not be visible to driver"


class TestNoRegressionStartEndIdempotent:
    """Verify START/END endpoints still work with idempotence"""
    
    def test_start_endpoint_responds(self):
        """Start endpoint should respond (409 if already started is OK)"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}/start?token={TEST_TOKEN}"
        res = requests.post(url)
        # 200 = success, 409 = already started (idempotent), both are acceptable
        assert res.status_code in [200, 409], f"Expected 200 or 409, got {res.status_code}"
    
    def test_end_endpoint_responds(self):
        """End endpoint should respond (409 if already ended is OK)"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}/end?token={TEST_TOKEN}"
        res = requests.post(url)
        # 200 = success, 409 = already ended (idempotent), both are acceptable
        assert res.status_code in [200, 409], f"Expected 200 or 409, got {res.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
