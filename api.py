"""
FastAPI Application
Status pages, webhooks, and health checks
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
import os

from config import settings
from infrastructure import get_db, init_db
from application import MonitorService

app = FastAPI(
    title="SRE Bot API",
    description="Enterprise Monitoring Platform API",
    version=settings.APP_VERSION
)


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": settings.APP_VERSION}


@app.get("/status/{slug}", response_class=HTMLResponse)
async def public_status_page(slug: str, db: AsyncSession = Depends(get_db)):
    """Public status page"""
    # Simplified status page - expand in production
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Status Page - {slug}</title>
        <style>
            body {{ font-family: -apple-system, sans-serif; background: #0f0f0f; color: #fff; padding: 40px; }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            .status {{ padding: 20px; border-radius: 12px; background: #1a1a1a; margin: 20px 0; }}
            .operational {{ color: #10b981; }}
            .down {{ color: #ef4444; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 System Status</h1>
            <div class="status">
                <p>Powered by SRE Bot</p>
                <p class="operational">✅ All Systems Operational</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html


@app.get("/")
async def root():
    return {"message": "SRE Bot API", "version": settings.APP_VERSION}

