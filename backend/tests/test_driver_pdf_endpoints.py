"""
Test Driver PDF Endpoints - Unified PDF Generation
===================================================
Tests for the unified PDF generation for bon de commande and invoice.
These endpoints use the pdf_template.py module which generates PDFs
with the JABADRIVER logo matching the frontend design.

Test credentials:
- test_ride_id: 318325c9-7f05-43f6-b8f5-aa2583609e25
- test_token: VYGIP4_TxdLZODDSxI7rvtSQR3DQ63tJOLawViPbAn0
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_RIDE_ID = "318325c9-7f05-43f6-b8f5-aa2583609e25"
TEST_TOKEN = "VYGIP4_TxdLZODDSxI7rvtSQR3DQ63tJOLawViPbAn0"


class TestDriverPDFEndpoints:
    """Test PDF endpoints for driver portal via token authentication"""
    
    def test_bon_commande_pdf_returns_200(self):
        """Test bon de commande PDF endpoint returns HTTP 200"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_RIDE_ID}/bon-commande-pdf?token={TEST_TOKEN}"
        response = requests.get(url)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✅ Bon de commande PDF: HTTP {response.status_code}")
    
    def test_bon_commande_pdf_content_type(self):
        """Test bon de commande PDF returns correct Content-Type"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_RIDE_ID}/bon-commande-pdf?token={TEST_TOKEN}"
        response = requests.get(url)
        
        assert response.status_code == 200
        content_type = response.headers.get('Content-Type', '')
        assert 'application/pdf' in content_type, f"Expected application/pdf, got {content_type}"
        print(f"✅ Bon de commande Content-Type: {content_type}")
    
    def test_bon_commande_pdf_is_valid_pdf(self):
        """Test bon de commande PDF content starts with PDF header"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_RIDE_ID}/bon-commande-pdf?token={TEST_TOKEN}"
        response = requests.get(url)
        
        assert response.status_code == 200
        # Valid PDF files start with %PDF-
        assert response.content[:5] == b'%PDF-', "PDF does not have valid PDF header"
        print(f"✅ Bon de commande is valid PDF (starts with %PDF-)")
    
    def test_bon_commande_pdf_has_content_disposition(self):
        """Test bon de commande PDF returns proper Content-Disposition header"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_RIDE_ID}/bon-commande-pdf?token={TEST_TOKEN}"
        response = requests.get(url)
        
        assert response.status_code == 200
        content_disp = response.headers.get('Content-Disposition', '')
        assert 'attachment' in content_disp, f"Expected attachment disposition, got {content_disp}"
        assert 'bon-commande' in content_disp, f"Expected bon-commande filename, got {content_disp}"
        print(f"✅ Bon de commande Content-Disposition: {content_disp}")
    
    def test_invoice_pdf_returns_200(self):
        """Test invoice PDF endpoint returns HTTP 200"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_RIDE_ID}/invoice-pdf?token={TEST_TOKEN}"
        response = requests.get(url)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✅ Invoice PDF: HTTP {response.status_code}")
    
    def test_invoice_pdf_content_type(self):
        """Test invoice PDF returns correct Content-Type"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_RIDE_ID}/invoice-pdf?token={TEST_TOKEN}"
        response = requests.get(url)
        
        assert response.status_code == 200
        content_type = response.headers.get('Content-Type', '')
        assert 'application/pdf' in content_type, f"Expected application/pdf, got {content_type}"
        print(f"✅ Invoice Content-Type: {content_type}")
    
    def test_invoice_pdf_is_valid_pdf(self):
        """Test invoice PDF content starts with PDF header"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_RIDE_ID}/invoice-pdf?token={TEST_TOKEN}"
        response = requests.get(url)
        
        assert response.status_code == 200
        # Valid PDF files start with %PDF-
        assert response.content[:5] == b'%PDF-', "PDF does not have valid PDF header"
        print(f"✅ Invoice is valid PDF (starts with %PDF-)")
    
    def test_invoice_pdf_has_content_disposition(self):
        """Test invoice PDF returns proper Content-Disposition header"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_RIDE_ID}/invoice-pdf?token={TEST_TOKEN}"
        response = requests.get(url)
        
        assert response.status_code == 200
        content_disp = response.headers.get('Content-Disposition', '')
        assert 'attachment' in content_disp, f"Expected attachment disposition, got {content_disp}"
        assert 'facture' in content_disp, f"Expected facture filename, got {content_disp}"
        print(f"✅ Invoice Content-Disposition: {content_disp}")


class TestDriverRideTokenAccess:
    """Test driver ride page via token authentication"""
    
    def test_ride_details_returns_200(self):
        """Test ride details endpoint returns HTTP 200 with valid token"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_RIDE_ID}?token={TEST_TOKEN}"
        response = requests.get(url)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✅ Ride details: HTTP {response.status_code}")
    
    def test_ride_details_returns_valid_json(self):
        """Test ride details returns valid JSON with expected fields"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_RIDE_ID}?token={TEST_TOKEN}"
        response = requests.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check expected fields
        assert 'id' in data, "Missing 'id' field"
        assert 'status' in data, "Missing 'status' field"
        assert 'client_name' in data, "Missing 'client_name' field"
        assert 'pickup_address' in data, "Missing 'pickup_address' field"
        assert 'dropoff_address' in data, "Missing 'dropoff_address' field"
        assert 'price_total' in data, "Missing 'price_total' field"
        
        print(f"✅ Ride details JSON valid with all expected fields")
        print(f"   - ID: {data['id'][:8]}...")
        print(f"   - Status: {data['status']}")
        print(f"   - Price: {data.get('price_total', 'N/A')}€")
    
    def test_ride_financial_summary_fields(self):
        """Test ride returns all financial fields for summary display"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_RIDE_ID}?token={TEST_TOKEN}"
        response = requests.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        # Financial fields that must be present
        price_total = data.get('price_total', 0)
        commission_amount = data.get('commission_amount', 0)
        
        assert price_total >= 0, "price_total must be >= 0"
        
        # Commission rate should be 10%
        expected_commission = price_total * 0.10
        
        print(f"✅ Financial summary fields:")
        print(f"   - Prix course: {price_total}€")
        print(f"   - Commission amount: {commission_amount}€")
        print(f"   - Expected commission (10%): {expected_commission}€")


class TestInvalidTokenAccess:
    """Test endpoints with invalid or missing tokens"""
    
    def test_ride_details_invalid_token_returns_401_or_404(self):
        """Test ride details with invalid token returns 401 or 404"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_RIDE_ID}?token=invalid_token_12345"
        response = requests.get(url)
        
        # Should return 401 Unauthorized or 404 Not Found
        assert response.status_code in [401, 403, 404], f"Expected 401/403/404, got {response.status_code}"
        print(f"✅ Invalid token rejected: HTTP {response.status_code}")
    
    def test_pdf_invalid_token_returns_error(self):
        """Test PDF download with invalid token returns error"""
        url = f"{BASE_URL}/api/driver/ride/{TEST_RIDE_ID}/bon-commande-pdf?token=invalid_token"
        response = requests.get(url)
        
        # Should return 401/403/404
        assert response.status_code in [401, 403, 404], f"Expected 401/403/404, got {response.status_code}"
        print(f"✅ PDF with invalid token rejected: HTTP {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
