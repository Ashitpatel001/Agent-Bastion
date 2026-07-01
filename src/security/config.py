import os
from dotenv import load_dotenv

load_dotenv()

class SecurityConfig:
    # VirusTotal API Key (Load from env)
    VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY", "")
    
    # JWT & Authentication
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-key-replace-in-production-1234567890")
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    # Safe domains (Always trusted)
    TRUSTED_DOMAINS = [
        "google.com",
        "google.co.in",
        "youtube.com",
        "stackoverflow.com",
        "github.com",
        "python.org",
        "pypi.org",
        "microsoft.com",
        "bing.com",
        "wikipedia.org",
        # E-commerce (India)
        "amazon.in",
        "amazon.com",
        "flipkart.com",
        "croma.com",
        "reliance.com",
        "jiomart.com",
        "myntra.com",
        "snapdeal.com",
        "tatacliq.com",
        "meesho.com",
        # E-commerce (Global)
        "ebay.com",
        "walmart.com",
        "bestbuy.com",
        "target.com",
        "meta.com",
    ]
    
    # Cloud providers (Never fully trust root)
    CLOUD_PROVIDERS = [
        "amazonaws.com",
        "googleapis.com",
        "vercel.app",
        "herokuapp.com",
        "azurewebsites.net",
        "blob.core.windows.net",
        "github.io"
    ]
    
    # Localhost (Treat as UNTRUSTED for testing)
    UNTRUSTED_HOSTS = [
        "localhost",
        "127.0.0.1",
        "0.0.0.0"
    ]
    
    # Security Thresholds
    VIRUSTOTAL_THRESHOLD = 0

    # Risk Score Thresholds
    RISK_AUTO_APPROVE = 30
    RISK_MONITOR = 70
    RISK_BLOCK = 71
