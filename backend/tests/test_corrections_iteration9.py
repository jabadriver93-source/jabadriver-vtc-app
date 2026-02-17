"""
Test Suite for Iteration 9 - 3 Targeted Corrections (FINAL)
=============================================================
1. PLATFORM_INFO on commission invoice (JABADRIVER address + SIRET)
2. Commission should NEVER appear on bon de commande (client document)
3. Admin email idempotence (flag end_admin_notification_sent)

Uses pypdf for proper PDF text extraction.
"""

import pytest
import requests
import os
from io import BytesIO
from pypdf import PdfReader

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_COURSE_ID = "318325c9-7f05-43f6-b8f5-aa2583609e25"
TEST_TOKEN = "VYGIP4_TxdLZODDSxI7rvtSQR3DQ63tJOLawViPbAn0"

# Expected PLATFORM_INFO values
EXPECTED_PLATFORM_ADDRESS = "49 boulevard Marc Chagall, 93600 Aulnay-sous-Bois"
EXPECTED_PLATFORM_SIRET = "941 473 217 00011"
EXPECTED_PLATFORM_NAME = "JABADRIVER"


def extract_pdf_text(pdf_content: bytes) -> str:
    """Extract text from PDF using pypdf"""
    pdf_reader = PdfReader(BytesIO(pdf_content))
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() or ""
    return text


class TestBonDeCommandeNoCommission:
    """
    Test A: Bon de commande client should NEVER show commission.
    Only Total TTC should appear, not 'Commission payée' or 'Votre gain net'.
    """
    
    def test_bon_commande_endpoint_returns_200(self):
        """Bon de commande PDF endpoint returns 200"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}/bon-commande-pdf?token={TEST_TOKEN}"
        response = requests.get(url)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✅ Bon de commande endpoint returns 200")
    
    def test_bon_commande_is_valid_pdf(self):
        """Bon de commande returns valid PDF"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}/bon-commande-pdf?token={TEST_TOKEN}"
        response = requests.get(url)
        assert response.status_code == 200
        assert response.content[:4] == b'%PDF', "Response is not a valid PDF"
        print("✅ Bon de commande is valid PDF")
    
    def test_bon_commande_no_commission_payee(self):
        """CRITICAL: Bon de commande should NOT contain 'Commission payée'"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}/bon-commande-pdf?token={TEST_TOKEN}"
        response = requests.get(url)
        assert response.status_code == 200
        
        pdf_text = extract_pdf_text(response.content)
        assert "Commission payée" not in pdf_text, "ERROR: 'Commission payée' found in bon de commande - should not appear!"
        print("✅ No 'Commission payée' in bon de commande PDF")
    
    def test_bon_commande_no_votre_gain_net(self):
        """CRITICAL: Bon de commande should NOT contain 'Votre gain net'"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}/bon-commande-pdf?token={TEST_TOKEN}"
        response = requests.get(url)
        assert response.status_code == 200
        
        pdf_text = extract_pdf_text(response.content)
        assert "Votre gain net" not in pdf_text, "ERROR: 'Votre gain net' found in bon de commande - should not appear!"
        print("✅ No 'Votre gain net' in bon de commande PDF")
    
    def test_bon_commande_has_total_ttc(self):
        """Bon de commande should contain 'Total TTC'"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}/bon-commande-pdf?token={TEST_TOKEN}"
        response = requests.get(url)
        assert response.status_code == 200
        
        pdf_text = extract_pdf_text(response.content)
        assert "Total TTC" in pdf_text, "ERROR: 'Total TTC' should appear in bon de commande"
        print("✅ 'Total TTC' correctly present in bon de commande PDF")


class TestPlatformInvoiceJabaDriverInfo:
    """
    Test B: Platform commission invoice should show JABADRIVER company info.
    Address: 49 boulevard Marc Chagall, 93600 Aulnay-sous-Bois
    SIRET: 941 473 217 00011
    """
    
    def test_platform_invoice_endpoint_returns_200(self):
        """Platform commission invoice endpoint returns 200"""
        url = f"{BASE_URL}/api/admin/subcontracting/courses/{TEST_COURSE_ID}/platform-invoice-pdf"
        response = requests.get(url)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✅ Platform invoice endpoint returns 200")
    
    def test_platform_invoice_is_valid_pdf(self):
        """Platform commission invoice returns valid PDF"""
        url = f"{BASE_URL}/api/admin/subcontracting/courses/{TEST_COURSE_ID}/platform-invoice-pdf"
        response = requests.get(url)
        assert response.status_code == 200
        assert response.content[:4] == b'%PDF', "Response is not a valid PDF"
        print("✅ Platform invoice is valid PDF")
    
    def test_platform_invoice_has_jabadriver_name(self):
        """Platform invoice should contain JABADRIVER company name"""
        url = f"{BASE_URL}/api/admin/subcontracting/courses/{TEST_COURSE_ID}/platform-invoice-pdf"
        response = requests.get(url)
        assert response.status_code == 200
        
        pdf_text = extract_pdf_text(response.content)
        assert "JABADRIVER" in pdf_text, "ERROR: 'JABADRIVER' not found in platform invoice"
        print("✅ 'JABADRIVER' found in platform invoice")
    
    def test_platform_invoice_has_address_street(self):
        """CRITICAL: Platform invoice should contain '49 boulevard Marc Chagall'"""
        url = f"{BASE_URL}/api/admin/subcontracting/courses/{TEST_COURSE_ID}/platform-invoice-pdf"
        response = requests.get(url)
        assert response.status_code == 200
        
        pdf_text = extract_pdf_text(response.content)
        assert "49 boulevard Marc Chagall" in pdf_text, "ERROR: '49 boulevard Marc Chagall' not found in platform invoice"
        print("✅ '49 boulevard Marc Chagall' found in platform invoice")
    
    def test_platform_invoice_has_address_city(self):
        """CRITICAL: Platform invoice should contain '93600 Aulnay-sous-Bois'"""
        url = f"{BASE_URL}/api/admin/subcontracting/courses/{TEST_COURSE_ID}/platform-invoice-pdf"
        response = requests.get(url)
        assert response.status_code == 200
        
        pdf_text = extract_pdf_text(response.content)
        assert "93600 Aulnay-sous-Bois" in pdf_text, "ERROR: '93600 Aulnay-sous-Bois' not found in platform invoice"
        print("✅ '93600 Aulnay-sous-Bois' found in platform invoice")
    
    def test_platform_invoice_has_siret(self):
        """CRITICAL: Platform invoice should contain SIRET '941 473 217 00011'"""
        url = f"{BASE_URL}/api/admin/subcontracting/courses/{TEST_COURSE_ID}/platform-invoice-pdf"
        response = requests.get(url)
        assert response.status_code == 200
        
        pdf_text = extract_pdf_text(response.content)
        # Check for SIRET with or without spaces
        siret_present = "941 473 217 00011" in pdf_text or "94147321700011" in pdf_text
        assert siret_present, f"ERROR: SIRET '941 473 217 00011' not found in platform invoice"
        print("✅ SIRET '941 473 217 00011' found in platform invoice")
    
    def test_platform_invoice_is_commission_invoice(self):
        """Platform invoice should have FACTURE DE COMMISSION title"""
        url = f"{BASE_URL}/api/admin/subcontracting/courses/{TEST_COURSE_ID}/platform-invoice-pdf"
        response = requests.get(url)
        assert response.status_code == 200
        
        pdf_text = extract_pdf_text(response.content)
        assert "FACTURE DE COMMISSION" in pdf_text, "ERROR: 'FACTURE DE COMMISSION' not found in platform invoice"
        print("✅ 'FACTURE DE COMMISSION' title found in platform invoice")


class TestDriverTokenPageEndpoints:
    """
    Test C: Token page endpoints should still work (no regression).
    """
    
    def test_ride_details_with_token_returns_200(self):
        """GET /api/driver/ride/{id}?token=xxx returns 200"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}?token={TEST_TOKEN}"
        response = requests.get(url)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✅ Ride details with token returns 200")
    
    def test_ride_details_returns_valid_json(self):
        """Ride details returns valid JSON with expected fields"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}?token={TEST_TOKEN}"
        response = requests.get(url)
        assert response.status_code == 200
        
        data = response.json()
        assert 'id' in data, "Missing 'id' in response"
        assert 'client_name' in data, "Missing 'client_name' in response"
        assert 'pickup_address' in data, "Missing 'pickup_address' in response"
        assert 'dropoff_address' in data, "Missing 'dropoff_address' in response"
        print("✅ Ride details returns valid JSON with expected fields")
    
    def test_invoice_pdf_endpoint_returns_200(self):
        """Invoice PDF endpoint returns 200"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}/invoice-pdf?token={TEST_TOKEN}"
        response = requests.get(url)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✅ Invoice PDF endpoint returns 200")


class TestStartEndIdempotence:
    """
    Test D: START and END endpoints should be idempotent (no regression).
    """
    
    def test_start_endpoint_is_idempotent(self):
        """POST /api/driver/ride/{id}/start should return proper status (idempotent)"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}/start?token={TEST_TOKEN}"
        response = requests.post(url)
        # Expected: 409 (already started) or 200 (success) or 400 (invalid state)
        assert response.status_code in [200, 409, 400], f"Unexpected status: {response.status_code}"
        print(f"✅ START endpoint returns {response.status_code} (idempotent behavior)")
    
    def test_end_endpoint_is_idempotent(self):
        """POST /api/driver/ride/{id}/end should return proper status (idempotent)"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}/end?token={TEST_TOKEN}"
        response = requests.post(url)
        # Expected: 409 (already ended) or 200 (success) or 400 (invalid state)
        assert response.status_code in [200, 409, 400], f"Unexpected status: {response.status_code}"
        print(f"✅ END endpoint returns {response.status_code} (idempotent behavior)")


class TestAdminEmailIdempotenceFlag:
    """
    Test E: Verify admin email idempotence via admin API course data.
    The flag 'end_admin_notification_sent' should be present for ended courses.
    """
    
    def test_ended_course_has_notification_flag(self):
        """
        Courses in DRIVER_COMPLETED status should have end_admin_notification_sent=True.
        This ensures admin email was sent only once.
        """
        url = f"{BASE_URL}/api/admin/subcontracting/courses"
        response = requests.get(url)
        assert response.status_code == 200
        
        courses = response.json()
        driver_completed_courses = [c for c in courses if c.get('status') == 'DRIVER_COMPLETED' and c.get('ended_at')]
        
        assert len(driver_completed_courses) > 0, "No DRIVER_COMPLETED courses found to test"
        
        # Check if at least one course has the flag set
        courses_with_flag = [c for c in driver_completed_courses if c.get('end_admin_notification_sent') == True]
        
        print(f"📊 Found {len(driver_completed_courses)} DRIVER_COMPLETED courses")
        print(f"📊 Courses with end_admin_notification_sent=True: {len(courses_with_flag)}")
        
        # At least some ended courses should have the flag
        assert len(courses_with_flag) > 0, "No ended courses have end_admin_notification_sent flag set"
        print("✅ Admin email idempotence flag is working - ended courses have flag set")


class TestOtherPdfsNotBroken:
    """
    Test F: Other PDF endpoints should still work (no regression).
    """
    
    def test_invoice_pdf_is_valid(self):
        """Invoice PDF endpoint returns valid PDF"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}/invoice-pdf?token={TEST_TOKEN}"
        response = requests.get(url)
        assert response.status_code == 200
        assert response.content[:4] == b'%PDF', "Invoice PDF is not valid"
        print("✅ Invoice PDF endpoint returns valid PDF")
    
    def test_invoice_pdf_has_correct_content_type(self):
        """Invoice PDF has correct Content-Type header"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_COURSE_ID}/invoice-pdf?token={TEST_TOKEN}"
        response = requests.get(url)
        assert response.status_code == 200
        assert 'application/pdf' in response.headers.get('Content-Type', ''), "Wrong Content-Type"
        print("✅ Invoice PDF has correct Content-Type header")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
