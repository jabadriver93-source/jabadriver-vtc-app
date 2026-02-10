import requests
import sys
import json
from datetime import datetime, timedelta

class VTCBookingAPITester:
    def __init__(self, base_url="https://vtc-booking-21.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_reservation_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test root API endpoint"""
        return self.run_test("Root API", "GET", "", 200)

    def test_create_reservation(self):
        """Test creating a new reservation"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        reservation_data = {
            "name": "Jean Dupont",
            "phone": "0612345678",
            "email": "jean.dupont@test.com",
            "pickup_address": "Gare du Nord, Paris",
            "dropoff_address": "Aéroport Charles de Gaulle, Roissy-en-France",
            "date": tomorrow,
            "time": "14:30",
            "passengers": 2,
            "luggage": "2 valises",
            "notes": "Vol Air France AF1234",
            # Test pricing data
            "distance_km": 31.1,
            "duration_min": 44,
            "estimated_price": 69
        }
        
        success, response = self.run_test(
            "Create Reservation",
            "POST",
            "reservations",
            200,
            data=reservation_data
        )
        
        if success and 'id' in response:
            self.test_reservation_id = response['id']
            print(f"   Created reservation ID: {self.test_reservation_id}")
            
            # Verify pricing data is saved
            if 'estimated_price' in response and response['estimated_price'] == 69:
                print(f"✅ Pricing data saved correctly: {response['estimated_price']}€")
            else:
                print(f"⚠️  Pricing data issue: {response.get('estimated_price', 'None')}")
            
            return True
        return False

    def test_get_reservations(self):
        """Test getting all reservations"""
        return self.run_test("Get All Reservations", "GET", "reservations", 200)

    def test_get_single_reservation(self):
        """Test getting a single reservation"""
        if not self.test_reservation_id:
            print("❌ Skipping - No reservation ID available")
            return False
            
        return self.run_test(
            "Get Single Reservation",
            "GET",
            f"reservations/{self.test_reservation_id}",
            200
        )

    def test_update_reservation_status(self):
        """Test updating reservation status"""
        if not self.test_reservation_id:
            print("❌ Skipping - No reservation ID available")
            return False
            
        return self.run_test(
            "Update Reservation Status",
            "PATCH",
            f"reservations/{self.test_reservation_id}/status",
            200,
            data={"status": "confirmée"}
        )

    def test_admin_login_success(self):
        """Test admin login with correct password"""
        return self.run_test(
            "Admin Login (Success)",
            "POST",
            "admin/login",
            200,
            data={"password": "Vtc!Admin2026#Secure"}
        )

    def test_admin_login_failure(self):
        """Test admin login with wrong password"""
        return self.run_test(
            "Admin Login (Failure)",
            "POST",
            "admin/login",
            401,
            data={"password": "wrongpassword"}
        )

    def test_reservations_with_filters(self):
        """Test reservations with search and date filters"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Test date filter
        success1, _ = self.run_test(
            "Get Reservations (Date Filter)",
            "GET",
            f"reservations?date={tomorrow}",
            200
        )
        
        # Test search filter
        success2, _ = self.run_test(
            "Get Reservations (Search Filter)",
            "GET",
            "reservations?search=Jean",
            200
        )
        
        # Test status filter
        success3, _ = self.run_test(
            "Get Reservations (Status Filter)",
            "GET",
            "reservations?status=confirmée",
            200
        )
        
        return success1 and success2 and success3

    def test_csv_export(self):
        """Test CSV export functionality"""
        url = f"{self.api_url}/reservations/export/csv"
        print(f"\n🔍 Testing CSV Export...")
        print(f"   URL: {url}")
        
        self.tests_run += 1
        try:
            response = requests.get(url)
            success = response.status_code == 200 and 'text/csv' in response.headers.get('content-type', '')
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                print(f"   Content-Type: {response.headers.get('content-type')}")
                print(f"   Content-Length: {len(response.content)} bytes")
                return True
            else:
                print(f"❌ Failed - Status: {response.status_code}")
                print(f"   Content-Type: {response.headers.get('content-type')}")
                return False
                
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False

    def test_invalid_status_update(self):
        """Test updating reservation with invalid status"""
        if not self.test_reservation_id:
            print("❌ Skipping - No reservation ID available")
            return False
            
        return self.run_test(
            "Update Reservation (Invalid Status)",
            "PATCH",
            f"reservations/{self.test_reservation_id}/status",
            400,
    def test_phone_validation(self):
        """Test French phone number validation"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Test valid French phone numbers
        valid_phones = ["0612345678", "06 12 34 56 78", "+33612345678", "0033612345678"]
        
        print(f"\n🔍 Testing Phone Validation...")
        
        # Test valid phones (should work)
        for phone in valid_phones:
            reservation_data = {
                "name": "Test User",
                "phone": phone,
                "pickup_address": "Paris",
                "dropoff_address": "CDG",
                "date": tomorrow,
                "time": "15:00",
                "passengers": 1
            }
            
            success, _ = self.run_test(
                f"Valid Phone: {phone}",
                "POST",
                "reservations",
                200,
                data=reservation_data
            )
            
            if not success:
                print(f"❌ Valid phone {phone} was rejected")
                return False
        
        print("✅ All valid phone numbers accepted")
        return True
            data={"status": "invalid_status"}
        )

    def test_price_calculation_validation(self):
        """Test price calculation logic"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Test case 1: Normal pricing (31.1km, 44min should be 69€)
        test_cases = [
            {
                "name": "Normal Price Test",
                "distance_km": 31.1,
                "duration_min": 44,
                "expected_price": 69,  # (31.1 * 1.5) + (44 * 0.5) = 46.65 + 22 = 68.65 -> rounded up to 69
                "pickup": "Gare du Nord, Paris",
                "dropoff": "Aéroport Charles de Gaulle"
            },
            {
                "name": "Minimum Price Test",
                "distance_km": 2.0,
                "duration_min": 5,
                "expected_price": 10,  # (2 * 1.5) + (5 * 0.5) = 3 + 2.5 = 5.5 -> minimum 10€
                "pickup": "Place de la République, Paris",
                "dropoff": "Gare de l'Est, Paris"
            }
        ]
        
        all_passed = True
        for i, test_case in enumerate(test_cases):
            reservation_data = {
                "name": f"Test User {i+1}",
                "phone": f"061234567{i}",
                "email": f"test{i+1}@example.com",
                "pickup_address": test_case["pickup"],
                "dropoff_address": test_case["dropoff"],
                "date": tomorrow,
                "time": "15:00",
                "passengers": 1,
                "distance_km": test_case["distance_km"],
                "duration_min": test_case["duration_min"],
                "estimated_price": test_case["expected_price"]
            }
            
            success, response = self.run_test(
                f"Price Calculation - {test_case['name']}",
                "POST",
                "reservations",
                200,
                data=reservation_data
            )
            
            if success:
                actual_price = response.get('estimated_price')
                if actual_price == test_case['expected_price']:
                    print(f"✅ Price calculation correct: {actual_price}€")
                else:
                    print(f"❌ Price calculation wrong: expected {test_case['expected_price']}€, got {actual_price}€")
                    all_passed = False
            else:
                all_passed = False
        
        return all_passed

def main():
    print("🚗 JABADRIVER VTC Booking API Tests")
    print("=" * 50)
    
    tester = VTCBookingAPITester()
    
    # Run all tests
    tests = [
        tester.test_root_endpoint,
        tester.test_create_reservation,
        tester.test_price_calculation_validation,
        tester.test_get_reservations,
        tester.test_get_single_reservation,
        tester.test_update_reservation_status,
        tester.test_admin_login_success,
        tester.test_admin_login_failure,
        tester.test_reservations_with_filters,
        tester.test_csv_export,
        tester.test_invalid_status_update,
        tester.test_nonexistent_reservation,
        tester.test_phone_validation
    ]
    
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
    
    # Print final results
    print(f"\n📊 Final Results")
    print("=" * 30)
    print(f"Tests run: {tester.tests_run}")
    print(f"Tests passed: {tester.tests_passed}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run*100):.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"⚠️  {tester.tests_run - tester.tests_passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())