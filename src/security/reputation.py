import logging
from urllib.parse import urlparse
from .config import SecurityConfig
import requests
import json

logger = logging.getLogger("security.reputation")

class ReputationManager:
    def __init__(self):
        self.cache = {} # Simple in-memory cache {domain: is_safe}
        self.api_key = SecurityConfig.VIRUSTOTAL_API_KEY

    def get_domain(self, url: str) -> str:
        try:
            parsed = urlparse(url)
            # Remove port if present and get domain
            return parsed.netloc.split(':')[0] 
        except:
            return ""

    def is_cloud_provider(self, domain: str) -> bool:
        for provider in SecurityConfig.CLOUD_PROVIDERS:
            # Check if domain is exactly the provider or a subdomain
            if domain == provider or domain.endswith(f".{provider}"):
                return True
        return False

    def check_reputation(self, url: str) -> bool:
        """
        Returns True if SAFE, False if HOSTILE.
        """
        domain = self.get_domain(url)
        if not domain:
            return False # Safest default

        # 1. Check Explicit Untrusted (Localhost)
        if domain in SecurityConfig.UNTRUSTED_HOSTS:
            logger.warning(f"SECURITY ALERT: Localhost detected ({domain}). Treating as HOSTILE.")
            return False

        # 2. Check Cloud Providers
        # Even if AWS is trusted, random-app.aws.amazon.com should not be automatically trusted 
        # unless specifically added.
        if self.is_cloud_provider(domain):
            logger.info(f"Cloud Provider detected ({domain}). Treating as Untrusted/Hostile.")
            return False

        # 3. Check Trusted Whitelist
        # Simple check for root domains
        parts = domain.split('.')
        if len(parts) >= 2:
            root_domain = f"{parts[-2]}.{parts[-1]}"
            if root_domain in SecurityConfig.TRUSTED_DOMAINS:
                 # Check if it is a subdomain of a trusted domain
                return True
            if domain in SecurityConfig.TRUSTED_DOMAINS:
                return True
        
        # 4. Check Cache
        if domain in self.cache:
            return self.cache[domain]

        # 5. Check VirusTotal
        if self.api_key:
            is_safe = self._query_virustotal(domain)
            self.cache[domain] = is_safe
            return is_safe
        
        # Default: If we don't know it, and it's not whitelisted, treat as HOSTILE.
        # This implementation assumes Zero Trust.
        logger.info(f"Unknown domain ({domain}). Treating as HOSTILE.")
        return False

    def _query_virustotal(self, domain: str) -> bool:
        try:
            url = f"https://www.virustotal.com/api/v3/domains/{domain}"
            headers = {
                "accept": "application/json",
                "x-apikey": self.api_key
            }
            logger.info(f"Querying VirusTotal for {domain}...")
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                stats = data.get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
                malicious = stats.get("malicious", 0)
                suspicious = stats.get("suspicious", 0)
                
                # If ANY engine flags it, we treat it as hostile for this secure browser
                if malicious > SecurityConfig.VIRUSTOTAL_THRESHOLD or suspicious > SecurityConfig.VIRUSTOTAL_THRESHOLD:
                    logger.warning(f"VirusTotal flagged {domain}: {malicious} malicious, {suspicious} suspicious.")
                    return False
                
                logger.info(f"VirusTotal checks passed for {domain}.")
                return True
            else:
                logger.error(f"VirusTotal API Error: {response.status_code}")
                # Fail open or closed? For high security, fail closed (False).
                return False
        except Exception as e:
            logger.error(f"Error querying VirusTotal: {e}")
            return False
