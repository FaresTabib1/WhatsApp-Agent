from fastapi import FastAPI
from app.api.routes import auth, businesses, health, products

app = FastAPI(
    title="WhatsApp Agent API",
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(businesses.router)   
app.include_router(products.router)