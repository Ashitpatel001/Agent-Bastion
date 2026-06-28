import random
import string
from urllib.parse import urlparse
import logging

logger = logging.getLogger("security.deception")

class DeceptionEngine:
    """
    Generates dynamic honeytokens and fake credentials on the fly.
    Instead of just blocking an attack, we feed the attacker fake data
    and observe their behavior.
    """

    def __init__(self):
        self.deployed_honeytokens = {}  # token -> context

    def generate_fake_data(self, original_text: str, context: str = "") -> str:
        """
        Takes the original (blocked) input and generates a contextually
        appropriate fake string to feed back to the attacker.
        """
        original_lower = original_text.lower()
        fake_data = ""

        # Identify Data Type
        if "password" in original_lower or "secret" in original_lower:
            fake_data = self._generate_password()
        elif "card" in original_lower or "cvv" in original_lower or "credit" in original_lower:
            fake_data = self._generate_credit_card()
            if "cvv" in original_lower:
                fake_data = str(random.randint(100, 999))
        elif "ssn" in original_lower:
            fake_data = f"{random.randint(100,999)}-{random.randint(10,99)}-{random.randint(1000,9999)}"
        elif "@" in original_text:
            fake_data = self._generate_email()
        else:
            # Fallback a generic token
            fake_data = f"honeytoken_{self._generate_random_string(8)}"

        # Track the deployed honeytoken so we can alert if we see it exit the network layer later
        self.deployed_honeytokens[fake_data] = context

        logger.info(f"🕷️ Deception Engine: Generated honeytoken '{fake_data}' for context '{context}'")
        return fake_data

    def is_honeytoken(self, text: str) -> bool:
        """Check if a string contains any active honeytokens."""
        # Simple substring check for any tracked honeytoken
        for token in self.deployed_honeytokens.keys():
            if token in text:
                return True
        return False

    def _generate_credit_card(self) -> str:
        # A valid looking (but fake) visa prefix
        prefixes = ["4", "51", "52", "53", "54", "55", "37"]
        prefix = random.choice(prefixes)
        length = 16 if prefix.startswith("4") or prefix.startswith("5") else 15
        
        number = prefix
        for _ in range(length - len(prefix)):
            number += str(random.randint(0, 9))
            
        return f"{number[:4]}-{number[4:8]}-{number[8:12]}-{number[12:]}"

    def _generate_password(self) -> str:
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(random.choice(chars) for _ in range(12))

    def _generate_email(self) -> str:
        names = ["adam", "sarah", "john", "admin", "test", "root"]
        domains = ["test.com", "example.org", "mailinator.com"]
        return f"{random.choice(names)}.{random.randint(100,999)}@{random.choice(domains)}"
    
    def _generate_random_string(self, length: int) -> str:
        return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))
