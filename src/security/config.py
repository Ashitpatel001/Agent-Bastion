import os
from dotenv import load_dotenv

load_dotenv()

class SecurityConfig:
    # VirusTotal API Key (Load from env)
    VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY", "")
    
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
