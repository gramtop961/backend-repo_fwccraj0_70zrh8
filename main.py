import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Product

app = FastAPI(title="Marketplace API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Marketplace backend running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response

# Seed initial catalog if empty
@app.post("/seed")
def seed_products():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    count = db["product"].count_documents({})
    if count > 0:
        return {"message": "Catalog already seeded", "count": count}
    demo_products = [
        {
            "title": "Velvet Rose Eau de Parfum",
            "description": "A lush floral fragrance with notes of rose, amber, and musk.",
            "price": 79.0,
            "category": "women",
            "in_stock": True,
            "image_url": "https://images.unsplash.com/photo-1523292562811-8fa7962a78c8",
            "brand": "Aurelia",
            "rating": 4.7,
            "tags": ["fragrance", "perfume", "floral"],
            "featured": True,
        },
        {
            "title": "Gentleman Grooming Kit",
            "description": "Complete shaving and beard care kit with natural oils.",
            "price": 59.0,
            "category": "men",
            "in_stock": True,
            "image_url": "https://images.unsplash.com/photo-1600986603369-9d3d0f6f0f9b",
            "brand": "NordCraft",
            "rating": 4.5,
            "tags": ["grooming", "kit", "beard"],
            "featured": True,
        },
        {
            "title": "Ceramic Wave Vase",
            "description": "Minimal wave-pattern vase to elevate any interior.",
            "price": 39.0,
            "category": "home",
            "in_stock": True,
            "image_url": "https://images.unsplash.com/photo-1523419409543-a7cf3f4e8d8f",
            "brand": "Haven",
            "rating": 4.6,
            "tags": ["decor", "vase", "ceramic"],
            "featured": False,
        },
        {
            "title": "Lavender Silk Body Lotion",
            "description": "Ultra-hydrating lotion with calming lavender.",
            "price": 24.0,
            "category": "women",
            "in_stock": True,
            "image_url": "https://images.unsplash.com/photo-1585386959984-a41552231658",
            "brand": "Serene",
            "rating": 4.4,
            "tags": ["body", "lotion", "lavender"],
            "featured": False,
        },
        {
            "title": "Matte Stone Candle Holder",
            "description": "Sculptural holder with a soft matte finish.",
            "price": 29.0,
            "category": "home",
            "in_stock": True,
            "image_url": "https://images.unsplash.com/photo-1519710164239-da123dc03ef4",
            "brand": "Aura",
            "rating": 4.3,
            "tags": ["decor", "candle"],
            "featured": False,
        },
    ]
    for p in demo_products:
        create_document("product", p)
    return {"message": "Catalog seeded", "count": len(demo_products)}

class ProductFilters(BaseModel):
    category: Optional[str] = None  # women | men | home
    q: Optional[str] = None
    featured: Optional[bool] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None

@app.get("/products", response_model=List[Product])
def list_products(
    category: Optional[str] = Query(None, description="women | men | home"),
    q: Optional[str] = Query(None, description="search query"),
    featured: Optional[bool] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    filters = {}
    if category:
        filters["category"] = category
    if featured is not None:
        filters["featured"] = featured
    if min_price is not None or max_price is not None:
        price_filter = {}
        if min_price is not None:
            price_filter["$gte"] = float(min_price)
        if max_price is not None:
            price_filter["$lte"] = float(max_price)
        filters["price"] = price_filter
    if q:
        filters["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
            {"tags": {"$in": [q]}},
        ]

    docs = get_documents("product", filters)
    # Coerce to Pydantic Product by dict unpack
    products: List[Product] = []
    for d in docs:
        d.pop("_id", None)
        products.append(Product(**d))
    return products

@app.get("/products/featured", response_model=List[Product])
def featured_products():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    docs = get_documents("product", {"featured": True}, limit=6)
    items: List[Product] = []
    for d in docs:
        d.pop("_id", None)
        items.append(Product(**d))
    return items

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
