import pytest
import os
import sys

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.config import Settings
from security.config import SecurityConfig


def test_dev_mode_startup_allows_fallback():
    """Verify development mode allows development fallback values without failing."""
    s = Settings(ENV="development", JWT_SECRET_KEY="super-secret-key-replace-in-production-1234567890")
    assert s.ENV == "development"
    assert s.JWT_SECRET_KEY == "super-secret-key-replace-in-production-1234567890"
    # Calling explicit check should also pass without raising
    s.validate_production_secrets()


def test_testing_mode_startup_allows_fallback():
    """Verify testing mode allows development/testing fallback values without failing."""
    s = Settings(ENV="testing", JWT_SECRET_KEY="test-secret")
    assert s.ENV == "testing"
    assert s.JWT_SECRET_KEY == "test-secret"
    s.validate_production_secrets()


def test_prod_startup_with_secure_secret():
    """Verify production mode succeeds cleanly with a secure, random secret >= 32 characters."""
    secure_secret = "c9d6f3b0185671a92e47852c03b1e948a3d75618f0923e4d8a21fbc6573e0921"
    s = Settings(ENV="production", JWT_SECRET_KEY=secure_secret)
    assert s.ENV == "production"
    assert s.JWT_SECRET_KEY == secure_secret
    s.validate_production_secrets()


def test_prod_startup_fails_missing_jwt_secret():
    """Verify production mode fails fast when JWT_SECRET_KEY is missing or empty string."""
    with pytest.raises(RuntimeError, match="FATAL SECURITY MISCONFIGURATION: JWT_SECRET_KEY is missing or empty"):
        Settings(ENV="production", JWT_SECRET_KEY="")


def test_prod_startup_fails_insecure_default_secret():
    """Verify production mode fails fast when using default fallback JWT_SECRET_KEY."""
    with pytest.raises(RuntimeError, match="cannot use development fallback or default values"):
        Settings(ENV="production", JWT_SECRET_KEY="super-secret-key-replace-in-production-1234567890")

    with pytest.raises(RuntimeError, match="cannot use development fallback or default values"):
        Settings(ENV="production", JWT_SECRET_KEY="changeme")


def test_prod_startup_fails_short_secret():
    """Verify production mode fails fast when JWT_SECRET_KEY is shorter than 32 characters."""
    with pytest.raises(RuntimeError, match="must be at least 32 characters long"):
        Settings(ENV="production", JWT_SECRET_KEY="MySecretIsOnly24Chars123!")


def test_security_config_metaclass_and_validation(monkeypatch):
    """Verify SecurityConfig delegates dynamically and reflects validation errors immediately."""
    from api.config import settings
    # Set settings to dev mode initially
    monkeypatch.setattr(settings, "ENV", "development")
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "dev-secret")
    assert SecurityConfig.JWT_SECRET_KEY == "dev-secret"

    # Now mutate settings to production with insecure default and verify SecurityConfig raises
    monkeypatch.setattr(settings, "ENV", "production")
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "super-secret-key-replace-in-production-1234567890")
    with pytest.raises(RuntimeError, match="cannot use development fallback or default values"):
        SecurityConfig.validate_production_secrets()
