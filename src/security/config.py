from api.config import settings


class _SecurityConfigMeta(type):
    @property
    def VIRUSTOTAL_API_KEY(cls):
        return settings.VIRUSTOTAL_API_KEY
    
    @property
    def JWT_SECRET_KEY(cls):
        return settings.JWT_SECRET_KEY
    
    @property
    def JWT_ALGORITHM(cls):
        return settings.JWT_ALGORITHM
    
    @property
    def ACCESS_TOKEN_EXPIRE_MINUTES(cls):
        return settings.ACCESS_TOKEN_EXPIRE_MINUTES
    
    @property
    def REFRESH_TOKEN_EXPIRE_DAYS(cls):
        return settings.REFRESH_TOKEN_EXPIRE_DAYS

    @property
    def RATE_LIMIT_ENABLED(cls):
        return settings.RATE_LIMIT_ENABLED

    @property
    def REDIS_POOL_SIZE(cls):
        return settings.REDIS_POOL_SIZE

    @property
    def LOGIN_RATE_LIMIT(cls):
        return settings.LOGIN_RATE_LIMIT

    @property
    def WORKER_LIMIT(cls):
        return settings.WORKER_LIMIT

    @property
    def TENANT_CREATE_LIMIT(cls):
        return settings.TENANT_CREATE_LIMIT

    @property
    def TENANT_REQUEST_LIMIT(cls):
        return settings.TENANT_REQUEST_LIMIT

    @property
    def API_KEY_LIMIT(cls):
        return settings.API_KEY_LIMIT

    @property
    def DEFAULT_RATE_LIMIT(cls):
        return settings.DEFAULT_RATE_LIMIT

    @property
    def BURST_LIMIT(cls):
        return settings.BURST_LIMIT

    @property
    def SUSTAINED_LIMIT(cls):
        return settings.SUSTAINED_LIMIT


class SecurityConfig(metaclass=_SecurityConfigMeta):
    @classmethod
    def validate_production_secrets(cls) -> None:
        settings.validate_production_secrets()
    
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
