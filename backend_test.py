
import requests
import sys
import time
import json
from datetime import datetime

class TrafficManagementAPITester:
    def __init__(self, base_url):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def run_test(self, name, method, endpoint, expected_status, data=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            
            result = {
                "test_name": name,
                "endpoint": url,
                "method": method,
                "expected_status": expected_status,
                "actual_status": response.status_code,
                "success": success
            }
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                if response.status_code != 204:  # No content
                    result["response"] = response.json()
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    result["error"] = response.json()
                except:
                    result["error"] = response.text

            self.test_results.append(result)
            return success, response.json() if success and response.status_code != 204 else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.test_results.append({
                "test_name": name,
                "endpoint": url,
                "method": method,
                "success": False,
                "error": str(e)
            })
            return False, {}

    def test_get_intersections(self):
        """Test getting all intersections"""
        success, response = self.run_test(
            "Get All Intersections",
            "GET",
            "api/intersections",
            200
        )
        return success, response

    def test_get_emergency_vehicles(self):
        """Test getting all emergency vehicles"""
        success, response = self.run_test(
            "Get Emergency Vehicles",
            "GET",
            "api/emergency-vehicles",
            200
        )
        return success, response

    def test_get_traffic_status(self):
        """Test getting traffic status"""
        success, response = self.run_test(
            "Get Traffic Status",
            "GET",
            "api/traffic-status",
            200
        )
        return success, response

    def test_create_emergency_vehicle(self):
        """Test creating a new emergency vehicle"""
        vehicle_data = {
            "id": f"test_vehicle_{int(time.time())}",  # Generate a unique ID
            "type": "ambulance",
            "latitude": 40.7575,
            "longitude": -73.9840,
            "destination_lat": 40.7600,
            "destination_lon": -73.9870,
            "speed": 45.0,
            "route": ["int_001", "int_002"],
            "priority_level": 9
        }
        
        success, response = self.run_test(
            "Create Emergency Vehicle",
            "POST",
            "api/emergency-vehicles",
            200,
            data=vehicle_data
        )
        return success, response

    def test_priority_override(self, intersection_id, vehicle_id):
        """Test priority override for an intersection"""
        priority_data = {
            "vehicle_id": vehicle_id,
            "intersection_id": intersection_id,
            "priority_level": 9,
            "duration": 60
        }
        
        success, response = self.run_test(
            "Priority Override",
            "POST",
            f"api/priority-override/{intersection_id}",
            200,
            data=priority_data
        )
        return success, response

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*50)
        print(f"📊 TEST SUMMARY: {self.tests_passed}/{self.tests_run} tests passed")
        print("="*50)
        
        if self.tests_passed < self.tests_run:
            print("\nFailed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"- {result['test_name']} ({result['method']} {result['endpoint']})")
                    if "error" in result:
                        print(f"  Error: {result['error']}")
        
        return self.tests_passed == self.tests_run

def main():
    # Get backend URL from environment variable or use default
    backend_url = "https://9339b180-8b09-41ca-8ff3-8b0776882a27.preview.emergentagent.com"
    
    print(f"Testing Smart Traffic Management System API at: {backend_url}")
    print("="*50)
    
    tester = TrafficManagementAPITester(backend_url)
    
    # Test 1: Get all intersections
    intersections_success, intersections = tester.test_get_intersections()
    
    # Test 2: Get all emergency vehicles
    vehicles_success, vehicles = tester.test_get_emergency_vehicles()
    
    # Test 3: Get traffic status
    status_success, status = tester.test_get_traffic_status()
    
    # Test 4: Create a new emergency vehicle
    create_success, new_vehicle = tester.test_create_emergency_vehicle()
    
    # Test 5: Test priority override (if previous tests succeeded)
    if intersections_success and create_success and len(intersections) > 0:
        intersection_id = intersections[0]["id"]
        vehicle_id = new_vehicle["id"]
        tester.test_priority_override(intersection_id, vehicle_id)
    
    # Print summary
    all_passed = tester.print_summary()
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
