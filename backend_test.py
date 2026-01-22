#!/usr/bin/env python3
"""
Kirana Shop Backend API Testing Script
Tests all backend APIs as specified in the review request
"""

import requests
import json
import sys
from datetime import datetime

# Backend URL from frontend .env
BASE_URL = "https://quick-kirana-6.preview.emergentagent.com/api"

class KiranaAPITester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.user_id = None
        self.admin_token = None
        self.guest_id = None
        self.category_id = None
        self.product_id = None
        self.order_id = None
        self.test_results = []
        
    def log_test(self, test_name, success, message, response_data=None):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "response_data": response_data
        })
        
        if not success:
            print(f"   Response: {response_data}")
    
    def test_seed_data(self):
        """Seed initial data for testing"""
        print("\n🌱 SEEDING DATA...")
        try:
            response = self.session.post(f"{self.base_url}/admin/seed-data")
            if response.status_code in [200, 201]:
                self.log_test("Seed Data", True, "Data seeded successfully")
                return True
            else:
                self.log_test("Seed Data", False, f"Status: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Seed Data", False, f"Exception: {str(e)}")
            return False
    
    def test_auth_apis(self):
        """Test all authentication APIs"""
        print("\n🔐 TESTING AUTHENTICATION APIs...")
        
        # 1. Test send OTP
        try:
            payload = {"phone": "9999999999"}
            response = self.session.post(f"{self.base_url}/auth/send-otp", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("otp") == "1234":
                    self.log_test("Send OTP", True, "OTP sent successfully")
                else:
                    self.log_test("Send OTP", False, "Invalid response format", data)
            else:
                self.log_test("Send OTP", False, f"Status: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Send OTP", False, f"Exception: {str(e)}")
        
        # 2. Test verify OTP
        try:
            payload = {"phone": "9999999999", "otp": "1234", "name": "Ravi Kumar"}
            response = self.session.post(f"{self.base_url}/auth/verify-otp", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("user"):
                    self.user_id = data["user"]["id"]
                    self.log_test("Verify OTP", True, f"User authenticated, ID: {self.user_id}")
                else:
                    self.log_test("Verify OTP", False, "Invalid response format", data)
            else:
                self.log_test("Verify OTP", False, f"Status: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Verify OTP", False, f"Exception: {str(e)}")
        
        # 3. Test admin login
        try:
            payload = {"username": "admin", "password": "admin123"}
            response = self.session.post(f"{self.base_url}/auth/admin-login", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("user"):
                    self.admin_token = data.get("token")
                    self.log_test("Admin Login", True, "Admin authenticated successfully")
                else:
                    self.log_test("Admin Login", False, "Invalid response format", data)
            else:
                self.log_test("Admin Login", False, f"Status: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Admin Login", False, f"Exception: {str(e)}")
        
        # 4. Test guest login
        try:
            response = self.session.post(f"{self.base_url}/auth/guest")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("guestId"):
                    self.guest_id = data["guestId"]
                    self.log_test("Guest Login", True, f"Guest ID: {self.guest_id}")
                else:
                    self.log_test("Guest Login", False, "Invalid response format", data)
            else:
                self.log_test("Guest Login", False, f"Status: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Guest Login", False, f"Exception: {str(e)}")
    
    def test_category_apis(self):
        """Test category APIs"""
        print("\n📂 TESTING CATEGORY APIs...")
        
        try:
            response = self.session.get(f"{self.base_url}/categories")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) >= 6:
                    # Check for Telugu names
                    has_telugu = any("nameTE" in cat for cat in data)
                    if has_telugu:
                        self.category_id = data[0]["id"]  # Store first category ID
                        self.log_test("Get Categories", True, f"Found {len(data)} categories with Telugu names")
                    else:
                        self.log_test("Get Categories", False, "Categories missing Telugu names", data)
                else:
                    self.log_test("Get Categories", False, f"Expected 6+ categories, got {len(data) if isinstance(data, list) else 'invalid'}", data)
            else:
                self.log_test("Get Categories", False, f"Status: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Get Categories", False, f"Exception: {str(e)}")
    
    def test_product_apis(self):
        """Test product APIs"""
        print("\n🛍️ TESTING PRODUCT APIs...")
        
        # 1. Get all products
        try:
            response = self.session.get(f"{self.base_url}/products")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    self.product_id = data[0]["id"]  # Store first product ID
                    self.log_test("Get All Products", True, f"Found {len(data)} products")
                else:
                    self.log_test("Get All Products", False, "No products found", data)
            else:
                self.log_test("Get All Products", False, f"Status: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Get All Products", False, f"Exception: {str(e)}")
        
        # 2. Get products by category
        if self.category_id:
            try:
                response = self.session.get(f"{self.base_url}/products?categoryId={self.category_id}")
                
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        self.log_test("Get Products by Category", True, f"Found {len(data)} products in category")
                    else:
                        self.log_test("Get Products by Category", False, "Invalid response format", data)
                else:
                    self.log_test("Get Products by Category", False, f"Status: {response.status_code}", response.text)
            except Exception as e:
                self.log_test("Get Products by Category", False, f"Exception: {str(e)}")
        
        # 3. Get single product
        if self.product_id:
            try:
                response = self.session.get(f"{self.base_url}/products/{self.product_id}")
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("id") == self.product_id:
                        self.log_test("Get Single Product", True, f"Product details retrieved")
                    else:
                        self.log_test("Get Single Product", False, "Product ID mismatch", data)
                else:
                    self.log_test("Get Single Product", False, f"Status: {response.status_code}", response.text)
            except Exception as e:
                self.log_test("Get Single Product", False, f"Exception: {str(e)}")
    
    def test_cart_apis(self):
        """Test cart APIs for logged in user"""
        print("\n🛒 TESTING CART APIs...")
        
        if not self.user_id or not self.product_id:
            self.log_test("Cart APIs", False, "Missing user_id or product_id for cart testing")
            return
        
        # 1. Add to cart
        try:
            response = self.session.post(f"{self.base_url}/cart/add?user_id={self.user_id}&product_id={self.product_id}&quantity=2")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_test("Add to Cart", True, "Product added to cart")
                else:
                    self.log_test("Add to Cart", False, "Success flag not set", data)
            else:
                self.log_test("Add to Cart", False, f"Status: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Add to Cart", False, f"Exception: {str(e)}")
        
        # 2. Get cart
        try:
            response = self.session.get(f"{self.base_url}/cart/{self.user_id}")
            
            if response.status_code == 200:
                data = response.json()
                if "items" in data and len(data["items"]) > 0:
                    self.log_test("Get Cart", True, f"Cart has {len(data['items'])} items")
                else:
                    self.log_test("Get Cart", False, "Cart is empty or invalid format", data)
            else:
                self.log_test("Get Cart", False, f"Status: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Get Cart", False, f"Exception: {str(e)}")
        
        # 3. Update cart item
        try:
            response = self.session.put(f"{self.base_url}/cart/update?user_id={self.user_id}&product_id={self.product_id}&quantity=3")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_test("Update Cart Item", True, "Cart item quantity updated")
                else:
                    self.log_test("Update Cart Item", False, "Success flag not set", data)
            else:
                self.log_test("Update Cart Item", False, f"Status: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Update Cart Item", False, f"Exception: {str(e)}")
        
        # 4. Remove from cart
        try:
            response = self.session.delete(f"{self.base_url}/cart/remove/{self.user_id}/{self.product_id}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_test("Remove from Cart", True, "Product removed from cart")
                else:
                    self.log_test("Remove from Cart", False, "Success flag not set", data)
            else:
                self.log_test("Remove from Cart", False, f"Status: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Remove from Cart", False, f"Exception: {str(e)}")
    
    def test_order_apis(self):
        """Test order APIs"""
        print("\n📦 TESTING ORDER APIs...")
        
        if not self.product_id:
            self.log_test("Order APIs", False, "Missing product_id for order testing")
            return
        
        # 1. Create order (with logged in user)
        if self.user_id:
            try:
                order_data = {
                    "userId": self.user_id,
                    "items": [
                        {
                            "productId": self.product_id,
                            "productName": "Test Product",
                            "productNameTE": "టెస్ట్ ప్రొడక్ట్",
                            "quantity": 2,
                            "price": 100.0
                        }
                    ],
                    "totalAmount": 200.0,
                    "deliveryType": "delivery",
                    "deliveryCharge": 30.0,
                    "deliveryAddress": {
                        "label": "Home",
                        "address": "123 Test Street, Hyderabad",
                        "landmark": "Near Test Mall"
                    },
                    "paymentMethod": "COD"
                }
                
                response = self.session.post(f"{self.base_url}/orders", json=order_data)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("id"):
                        self.order_id = data["id"]
                        self.log_test("Create Order (User)", True, f"Order created with ID: {self.order_id}")
                    else:
                        self.log_test("Create Order (User)", False, "Order ID not returned", data)
                else:
                    self.log_test("Create Order (User)", False, f"Status: {response.status_code}", response.text)
            except Exception as e:
                self.log_test("Create Order (User)", False, f"Exception: {str(e)}")
        
        # 2. Create guest order
        if self.guest_id:
            try:
                guest_order_data = {
                    "guestName": "Priya Sharma",
                    "guestPhone": "8888888888",
                    "items": [
                        {
                            "productId": self.product_id,
                            "productName": "Test Product",
                            "productNameTE": "టెస్ట్ ప్రొడక్ట్",
                            "quantity": 1,
                            "price": 100.0
                        }
                    ],
                    "totalAmount": 130.0,
                    "deliveryType": "delivery",
                    "deliveryCharge": 30.0,
                    "deliveryAddress": {
                        "label": "Office",
                        "address": "456 Guest Street, Hyderabad",
                        "landmark": "Near Guest Mall"
                    },
                    "paymentMethod": "COD"
                }
                
                response = self.session.post(f"{self.base_url}/orders", json=guest_order_data)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("id"):
                        self.log_test("Create Order (Guest)", True, f"Guest order created")
                    else:
                        self.log_test("Create Order (Guest)", False, "Order ID not returned", data)
                else:
                    self.log_test("Create Order (Guest)", False, f"Status: {response.status_code}", response.text)
            except Exception as e:
                self.log_test("Create Order (Guest)", False, f"Exception: {str(e)}")
        
        # 3. Get my orders
        if self.user_id:
            try:
                response = self.session.get(f"{self.base_url}/orders/my/{self.user_id}")
                
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        self.log_test("Get My Orders", True, f"Found {len(data)} orders for user")
                    else:
                        self.log_test("Get My Orders", False, "Invalid response format", data)
                else:
                    self.log_test("Get My Orders", False, f"Status: {response.status_code}", response.text)
            except Exception as e:
                self.log_test("Get My Orders", False, f"Exception: {str(e)}")
        
        # 4. Get single order
        if self.order_id:
            try:
                response = self.session.get(f"{self.base_url}/orders/{self.order_id}")
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("id") == self.order_id:
                        self.log_test("Get Single Order", True, "Order details retrieved")
                    else:
                        self.log_test("Get Single Order", False, "Order ID mismatch", data)
                else:
                    self.log_test("Get Single Order", False, f"Status: {response.status_code}", response.text)
            except Exception as e:
                self.log_test("Get Single Order", False, f"Exception: {str(e)}")
    
    def test_admin_apis(self):
        """Test admin APIs"""
        print("\n👨‍💼 TESTING ADMIN APIs...")
        
        # 1. Get all orders
        try:
            response = self.session.get(f"{self.base_url}/admin/orders")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("Get All Orders (Admin)", True, f"Found {len(data)} total orders")
                else:
                    self.log_test("Get All Orders (Admin)", False, "Invalid response format", data)
            else:
                self.log_test("Get All Orders (Admin)", False, f"Status: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Get All Orders (Admin)", False, f"Exception: {str(e)}")
        
        # 2. Get orders by status
        try:
            response = self.session.get(f"{self.base_url}/admin/orders?status=pending")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("Get Orders by Status", True, f"Found {len(data)} pending orders")
                else:
                    self.log_test("Get Orders by Status", False, "Invalid response format", data)
            else:
                self.log_test("Get Orders by Status", False, f"Status: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Get Orders by Status", False, f"Exception: {str(e)}")
        
        # 3. Update order status
        if self.order_id:
            try:
                response = self.session.put(f"{self.base_url}/admin/orders/{self.order_id}/status?status=accepted")
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        self.log_test("Update Order Status", True, "Order status updated to accepted")
                    else:
                        self.log_test("Update Order Status", False, "Success flag not set", data)
                else:
                    self.log_test("Update Order Status", False, f"Status: {response.status_code}", response.text)
            except Exception as e:
                self.log_test("Update Order Status", False, f"Exception: {str(e)}")
        
        # 4. Get dashboard analytics
        try:
            response = self.session.get(f"{self.base_url}/admin/analytics/dashboard")
            
            if response.status_code == 200:
                data = response.json()
                expected_keys = ["todayOrders", "pendingOrders", "todayRevenue", "totalCustomers"]
                if all(key in data for key in expected_keys):
                    self.log_test("Dashboard Analytics", True, f"Analytics: {data}")
                else:
                    self.log_test("Dashboard Analytics", False, f"Missing analytics keys", data)
            else:
                self.log_test("Dashboard Analytics", False, f"Status: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Dashboard Analytics", False, f"Exception: {str(e)}")
    
    def run_all_tests(self):
        """Run all test suites"""
        print(f"🚀 STARTING KIRANA SHOP BACKEND API TESTS")
        print(f"📍 Base URL: {self.base_url}")
        print("=" * 60)
        
        # Run tests in sequence
        self.test_seed_data()
        self.test_auth_apis()
        self.test_category_apis()
        self.test_product_apis()
        self.test_cart_apis()
        self.test_order_apis()
        self.test_admin_apis()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n🔍 FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   ❌ {result['test']}: {result['message']}")
        
        print("\n" + "=" * 60)
        return failed_tests == 0

if __name__ == "__main__":
    tester = KiranaAPITester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)