from fastapi import FastAPI, APIRouter, HTTPException, Depends
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
import random

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

# ============ MODELS ============

class Address(BaseModel):
    label: str
    address: str
    landmark: Optional[str] = ""
    isDefault: bool = False

class User(BaseModel):
    id: Optional[str] = None
    name: str
    phone: str
    addresses: List[Address] = []
    role: str = "customer"  # customer or admin
    createdAt: datetime = Field(default_factory=datetime.utcnow)

class SendOTPRequest(BaseModel):
    phone: str

class VerifyOTPRequest(BaseModel):
    phone: str
    otp: str
    name: Optional[str] = None

class AdminLoginRequest(BaseModel):
    username: str
    password: str

class Category(BaseModel):
    id: Optional[str] = None
    name: str
    nameTE: str  # Telugu name
    icon: str = "🏪"
    isActive: bool = True

class Product(BaseModel):
    id: Optional[str] = None
    name: str
    nameTE: str
    categoryId: str
    price: float
    unit: str  # kg, litre, piece
    stock: int
    image: str  # base64 or URL
    description: str = ""
    descriptionTE: str = ""
    isAvailable: bool = True

class CartItem(BaseModel):
    productId: str
    quantity: int

class Cart(BaseModel):
    id: Optional[str] = None
    userId: str
    items: List[CartItem] = []

class OrderItem(BaseModel):
    productId: str
    productName: str
    productNameTE: str
    quantity: int
    price: float

class Order(BaseModel):
    id: Optional[str] = None
    userId: Optional[str] = None
    guestName: Optional[str] = None
    guestPhone: Optional[str] = None
    items: List[OrderItem]
    totalAmount: float
    deliveryType: str  # delivery or pickup
    deliveryCharge: float = 0
    deliveryAddress: Optional[dict] = None
    status: str = "pending"  # pending, accepted, preparing, out_for_delivery, delivered, cancelled
    paymentMethod: str = "COD"
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

# ============ HELPER FUNCTIONS ============

def serialize_doc(doc):
    if doc and "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    return doc

# ============ AUTH APIs ============

@api_router.post("/auth/send-otp")
async def send_otp(request: SendOTPRequest):
    # For MVP, we'll use a dummy OTP system
    # In production, integrate with SMS service like Twilio
    otp = "1234"  # Dummy OTP
    return {"success": True, "message": "OTP sent successfully", "otp": otp}

@api_router.post("/auth/verify-otp")
async def verify_otp(request: VerifyOTPRequest):
    # For MVP, accept "1234" as valid OTP
    if request.otp != "1234":
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    # Check if user exists
    user_doc = await db.users.find_one({"phone": request.phone})
    
    if not user_doc:
        # Create new user
        if not request.name:
            raise HTTPException(status_code=400, detail="Name is required for new users")
        
        user = User(name=request.name, phone=request.phone)
        result = await db.users.insert_one(user.dict(exclude={"id"}))
        user.id = str(result.inserted_id)
    else:
        user = User(**serialize_doc(user_doc))
    
    return {"success": True, "user": user.dict(), "token": f"token_{user.id}"}

@api_router.post("/auth/guest")
async def guest_login():
    return {"success": True, "guestId": str(uuid.uuid4())}

@api_router.post("/auth/admin-login")
async def admin_login(request: AdminLoginRequest):
    # For MVP, use simple credentials
    # In production, use proper password hashing
    if request.username == "admin" and request.password == "admin123":
        # Check if admin user exists
        admin_doc = await db.users.find_one({"phone": "admin", "role": "admin"})
        if not admin_doc:
            # Create admin user
            admin = User(name="Admin", phone="admin", role="admin")
            result = await db.users.insert_one(admin.dict(exclude={"id"}))
            admin.id = str(result.inserted_id)
        else:
            admin = User(**serialize_doc(admin_doc))
        
        return {"success": True, "user": admin.dict(), "token": f"token_{admin.id}"}
    
    raise HTTPException(status_code=401, detail="Invalid credentials")

# ============ CATEGORY APIs ============

@api_router.get("/categories")
async def get_categories():
    categories = await db.categories.find({"isActive": True}).to_list(100)
    return [serialize_doc(cat) for cat in categories]

@api_router.post("/admin/categories")
async def create_category(category: Category):
    result = await db.categories.insert_one(category.dict(exclude={"id"}))
    category.id = str(result.inserted_id)
    return category

@api_router.put("/admin/categories/{category_id}")
async def update_category(category_id: str, category: Category):
    await db.categories.update_one(
        {"_id": ObjectId(category_id)},
        {"$set": category.dict(exclude={"id"})}
    )
    return {"success": True}

@api_router.delete("/admin/categories/{category_id}")
async def delete_category(category_id: str):
    await db.categories.delete_one({"_id": ObjectId(category_id)})
    return {"success": True}

# ============ PRODUCT APIs ============

@api_router.get("/products")
async def get_products(categoryId: Optional[str] = None, search: Optional[str] = None):
    query = {"isAvailable": True}
    if categoryId:
        query["categoryId"] = categoryId
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"nameTE": {"$regex": search, "$options": "i"}}
        ]
    
    products = await db.products.find(query).to_list(1000)
    return [serialize_doc(prod) for prod in products]

@api_router.get("/products/{product_id}")
async def get_product(product_id: str):
    product = await db.products.find_one({"_id": ObjectId(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return serialize_doc(product)

@api_router.post("/admin/products")
async def create_product(product: Product):
    result = await db.products.insert_one(product.dict(exclude={"id"}))
    product.id = str(result.inserted_id)
    return product

@api_router.put("/admin/products/{product_id}")
async def update_product(product_id: str, product: Product):
    await db.products.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": product.dict(exclude={"id"})}
    )
    return {"success": True}

@api_router.delete("/admin/products/{product_id}")
async def delete_product(product_id: str):
    await db.products.delete_one({"_id": ObjectId(product_id)})
    return {"success": True}

# ============ CART APIs ============

@api_router.get("/cart/{user_id}")
async def get_cart(user_id: str):
    cart = await db.carts.find_one({"userId": user_id})
    if not cart:
        return {"items": []}
    
    # Get product details for each item
    items_with_details = []
    for item in cart.get("items", []):
        product = await db.products.find_one({"_id": ObjectId(item["productId"])})
        if product:
            items_with_details.append({
                "product": serialize_doc(product),
                "quantity": item["quantity"]
            })
    
    return {"items": items_with_details}

@api_router.post("/cart/add")
async def add_to_cart(user_id: str, product_id: str, quantity: int = 1):
    cart = await db.carts.find_one({"userId": user_id})
    
    if not cart:
        # Create new cart
        cart = {"userId": user_id, "items": [{"productId": product_id, "quantity": quantity}]}
        await db.carts.insert_one(cart)
    else:
        # Update existing cart
        items = cart.get("items", [])
        found = False
        for item in items:
            if item["productId"] == product_id:
                item["quantity"] += quantity
                found = True
                break
        
        if not found:
            items.append({"productId": product_id, "quantity": quantity})
        
        await db.carts.update_one(
            {"userId": user_id},
            {"$set": {"items": items}}
        )
    
    return {"success": True}

@api_router.put("/cart/update")
async def update_cart_item(user_id: str, product_id: str, quantity: int):
    cart = await db.carts.find_one({"userId": user_id})
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    items = cart.get("items", [])
    for item in items:
        if item["productId"] == product_id:
            if quantity <= 0:
                items.remove(item)
            else:
                item["quantity"] = quantity
            break
    
    await db.carts.update_one(
        {"userId": user_id},
        {"$set": {"items": items}}
    )
    
    return {"success": True}

@api_router.delete("/cart/remove/{user_id}/{product_id}")
async def remove_from_cart(user_id: str, product_id: str):
    cart = await db.carts.find_one({"userId": user_id})
    if not cart:
        return {"success": True}
    
    items = [item for item in cart.get("items", []) if item["productId"] != product_id]
    
    await db.carts.update_one(
        {"userId": user_id},
        {"$set": {"items": items}}
    )
    
    return {"success": True}

@api_router.delete("/cart/clear/{user_id}")
async def clear_cart(user_id: str):
    await db.carts.delete_one({"userId": user_id})
    return {"success": True}

# ============ ORDER APIs ============

@api_router.post("/orders")
async def create_order(order: Order):
    result = await db.orders.insert_one(order.dict(exclude={"id"}))
    order.id = str(result.inserted_id)
    
    # Clear cart if user is logged in
    if order.userId:
        await db.carts.delete_one({"userId": order.userId})
    
    return order

@api_router.get("/orders/my/{user_id}")
async def get_my_orders(user_id: str):
    orders = await db.orders.find({"userId": user_id}).sort("createdAt", -1).to_list(100)
    return [serialize_doc(order) for order in orders]

@api_router.get("/orders/{order_id}")
async def get_order(order_id: str):
    order = await db.orders.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return serialize_doc(order)

@api_router.get("/admin/orders")
async def get_all_orders(status: Optional[str] = None):
    query = {}
    if status:
        query["status"] = status
    
    orders = await db.orders.find(query).sort("createdAt", -1).to_list(1000)
    return [serialize_doc(order) for order in orders]

@api_router.put("/admin/orders/{order_id}/status")
async def update_order_status(order_id: str, status: str):
    await db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"status": status, "updatedAt": datetime.utcnow()}}
    )
    return {"success": True}

# ============ USER APIs ============

@api_router.get("/users/{user_id}")
async def get_user(user_id: str):
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return serialize_doc(user)

@api_router.put("/users/{user_id}")
async def update_user(user_id: str, user: User):
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": user.dict(exclude={"id"})}
    )
    return {"success": True}

@api_router.post("/users/{user_id}/address")
async def add_address(user_id: str, address: Address):
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    addresses = user.get("addresses", [])
    addresses.append(address.dict())
    
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"addresses": addresses}}
    )
    
    return {"success": True}

# ============ ANALYTICS APIs ============

@api_router.get("/admin/analytics/dashboard")
async def get_dashboard_stats():
    # Get today's orders
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_orders = await db.orders.count_documents({"createdAt": {"$gte": today}})
    
    # Get pending orders
    pending_orders = await db.orders.count_documents({"status": "pending"})
    
    # Get today's revenue
    pipeline = [
        {"$match": {"createdAt": {"$gte": today}, "status": {"$ne": "cancelled"}}},
        {"$group": {"_id": None, "total": {"$sum": "$totalAmount"}}}
    ]
    revenue_result = await db.orders.aggregate(pipeline).to_list(1)
    today_revenue = revenue_result[0]["total"] if revenue_result else 0
    
    # Get total customers
    total_customers = await db.users.count_documents({"role": "customer"})
    
    return {
        "todayOrders": today_orders,
        "pendingOrders": pending_orders,
        "todayRevenue": today_revenue,
        "totalCustomers": total_customers
    }

# ============ SEED DATA (for testing) ============

@api_router.post("/admin/seed-data")
async def seed_data():
    # Check if data already exists
    existing_categories = await db.categories.count_documents({})
    if existing_categories > 0:
        return {"message": "Data already seeded"}
    
    # Seed categories
    categories = [
        {"name": "Rice & Grains", "nameTE": "అన్నం & ధాన్యాలు", "icon": "🌾", "isActive": True},
        {"name": "Oil & Ghee", "nameTE": "నూనె & నేయి", "icon": "🛢️", "isActive": True},
        {"name": "Dairy Products", "nameTE": "పాల ఉత్పత్తులు", "icon": "🥛", "isActive": True},
        {"name": "Snacks", "nameTE": "స్నాక్స్", "icon": "🍪", "isActive": True},
        {"name": "Beverages", "nameTE": "పానీయాలు", "icon": "🥤", "isActive": True},
        {"name": "Vegetables", "nameTE": "కూరగాయలు", "icon": "🥬", "isActive": True},
    ]
    
    category_results = await db.categories.insert_many(categories)
    category_ids = [str(id) for id in category_results.inserted_ids]
    
    # Seed products
    products = [
        # Rice & Grains
        {"name": "Basmati Rice", "nameTE": "బాస్మతి బియ్యం", "categoryId": category_ids[0], "price": 120, "unit": "kg", "stock": 100, "image": "https://via.placeholder.com/200?text=Rice", "isAvailable": True},
        {"name": "Sona Masoori Rice", "nameTE": "సోనా మసూరి బియ్యం", "categoryId": category_ids[0], "price": 80, "unit": "kg", "stock": 150, "image": "https://via.placeholder.com/200?text=Rice", "isAvailable": True},
        
        # Oil & Ghee
        {"name": "Sunflower Oil", "nameTE": "పొద్దుతిరుగుడు నూనె", "categoryId": category_ids[1], "price": 180, "unit": "litre", "stock": 50, "image": "https://via.placeholder.com/200?text=Oil", "isAvailable": True},
        {"name": "Pure Ghee", "nameTE": "స్వచ్ఛమైన నేయి", "categoryId": category_ids[1], "price": 500, "unit": "kg", "stock": 30, "image": "https://via.placeholder.com/200?text=Ghee", "isAvailable": True},
        
        # Dairy
        {"name": "Milk", "nameTE": "పాలు", "categoryId": category_ids[2], "price": 60, "unit": "litre", "stock": 200, "image": "https://via.placeholder.com/200?text=Milk", "isAvailable": True},
        {"name": "Curd", "nameTE": "పెరుగు", "categoryId": category_ids[2], "price": 50, "unit": "kg", "stock": 100, "image": "https://via.placeholder.com/200?text=Curd", "isAvailable": True},
        
        # Snacks
        {"name": "Biscuits", "nameTE": "బిస్కెట్లు", "categoryId": category_ids[3], "price": 30, "unit": "piece", "stock": 150, "image": "https://via.placeholder.com/200?text=Biscuits", "isAvailable": True},
        {"name": "Chips", "nameTE": "చిప్స్", "categoryId": category_ids[3], "price": 20, "unit": "piece", "stock": 200, "image": "https://via.placeholder.com/200?text=Chips", "isAvailable": True},
        
        # Beverages
        {"name": "Tea Powder", "nameTE": "టీ పౌడర్", "categoryId": category_ids[4], "price": 400, "unit": "kg", "stock": 80, "image": "https://via.placeholder.com/200?text=Tea", "isAvailable": True},
        {"name": "Coffee Powder", "nameTE": "కాఫీ పౌడర్", "categoryId": category_ids[4], "price": 600, "unit": "kg", "stock": 60, "image": "https://via.placeholder.com/200?text=Coffee", "isAvailable": True},
        
        # Vegetables
        {"name": "Tomato", "nameTE": "టమోటా", "categoryId": category_ids[5], "price": 40, "unit": "kg", "stock": 50, "image": "https://via.placeholder.com/200?text=Tomato", "isAvailable": True},
        {"name": "Onion", "nameTE": "ఉల్లిపాయ", "categoryId": category_ids[5], "price": 35, "unit": "kg", "stock": 60, "image": "https://via.placeholder.com/200?text=Onion", "isAvailable": True},
    ]
    
    await db.products.insert_many(products)
    
    return {"success": True, "message": "Data seeded successfully"}

# ============ ROOT ROUTE ============

@api_router.get("/")
async def root():
    return {"message": "Kirana Shop API", "version": "1.0"}

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
