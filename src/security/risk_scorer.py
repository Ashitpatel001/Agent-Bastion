"""
risk_scorer.py — Dynamic Risk Scoring Engine
Adapted from CSA's Core Behavior Risk Assessment (CBRA) formula.

Risk = Impact × CapabilityScope × (1 + IntentMisalignment)

Thresholds:
  0-30:  Auto-approve (LOW)
  31-70: Log + enhanced monitoring (MEDIUM)
  71-100: Block + escalate to human (HIGH/CRITICAL)
"""

import re
import logging
from urllib.parse import urlparse
from .config import SecurityConfig

logger = logging.getLogger("security.risk_scorer")


# Impact scores by action type
ACTION_IMPACT = {
    "get_content": 10,
    "scroll": 10,
    "wait": 5,
    "screenshot": 15,
    "click_element": 30,
    "input_text": 50,
    "select_dropdown_option": 40,
    "open_tab": 50,
    "navigate": 50,
    "go_to_url": 50,
    "go_back": 20,
    "search_google": 25,
    "send_keys": 55,
    "extract_content": 15,
    "done": 0,
}

# Keywords that indicate sensitive page contexts
SENSITIVE_PAGE_KEYWORDS = [
    "login", "signin", "sign-in", "sign_in",
    "password", "checkout", "payment", "pay",
    "bank", "transfer", "credit", "card",
    "account", "billing", "confirm", "verify",
    "admin", "settings", "security",
]

# Known typosquatting patterns for popular domains
TYPOSQUAT_PATTERNS = {
    "google": ["g00gle", "googel", "gogle", "gooogle", "goolge"],
    "amazon": ["amaz0n", "amazn", "amaazon", "amazom"],
    "flipkart": ["fl1pkart", "flipkrt", "flipkar", "fllpkart"],
    "facebook": ["faceb00k", "faccbook", "faceboook"],
    "microsoft": ["micros0ft", "microsft", "mircosoft"],
    "paypal": ["paypa1", "paypall", "paypaI"],
    "apple": ["app1e", "appIe", "aple"],
}


class RiskScorer:
    """Dynamic risk scoring engine for agentic browser actions."""

    def __init__(self, user_task: str = ""):
        self.user_task = user_task.lower()
        self.action_history = []  # Track sequential actions for anomaly detection
        self.page_context_cache = {}  # domain -> context_score

    def calculate_risk(
        self,
        action_name: str,
        action_params: dict,
        current_url: str,
        security_state: str,
    ) -> dict:
        """
        Calculate a dynamic risk score for a proposed action.

        Returns:
            dict with keys: score, level, impact, capability_scope, 
                           intent_misalignment, breakdown, recommendation
        """
        # 1. Impact score based on action type
        impact = ACTION_IMPACT.get(action_name, 35)  # Default moderate

        # Boost impact for sensitive input actions
        if action_name == "input_text":
            text = action_params.get("text", "").lower()
            if any(kw in text for kw in ["password", "credit", "card", "ssn", "cvv"]):
                impact = min(impact + 30, 100)

        # 2. Capability Scope based on domain trust
        if security_state == "TRUSTED":
            capability_scope = 0.3
        elif security_state == "HOSTILE":
            capability_scope = 1.0
        elif security_state == "UNKNOWN":
            capability_scope = 0.4  # Neutral (e.g., about:blank)
        else:
            capability_scope = 0.7

        # DESTINATION-AWARE: If navigating TO a trusted domain, reduce scope
        if action_name in ["navigate", "go_to_url", "open_tab"]:
            dest_url = action_params.get("url", "")
            if dest_url:
                try:
                    dest_domain = urlparse(dest_url).netloc.lower().split(":")[0]
                    for trusted in SecurityConfig.TRUSTED_DOMAINS:
                        if dest_domain.endswith(trusted):
                            capability_scope = min(capability_scope, 0.3)
                            break
                except Exception:
                    pass

        # search_google is inherently safe (navigates to Google)
        if action_name == "search_google":
            capability_scope = min(capability_scope, 0.3)

        # Boost capability scope for sensitive page contexts
        url_lower = current_url.lower()
        if any(kw in url_lower for kw in SENSITIVE_PAGE_KEYWORDS):
            capability_scope = min(capability_scope + 0.2, 1.0)

        # 3. Intent Misalignment — does this action relate to the user's task?
        intent_misalignment = self._assess_intent_misalignment(
            action_name, action_params, current_url
        )

        # 4. Sequential anomaly bonus
        anomaly_bonus = self._check_sequential_anomaly(action_name, action_params)

        # 5. Typosquatting check
        typosquat_bonus = 0
        if action_name in ["navigate", "go_to_url", "open_tab"]:
            url = action_params.get("url", "")
            if self._check_typosquatting(url):
                typosquat_bonus = 25

        # Calculate final score
        raw_score = impact * capability_scope * (1 + intent_misalignment)
        raw_score += anomaly_bonus + typosquat_bonus
        score = int(min(max(raw_score, 0), 100))

        # Determine risk level
        if score <= 30:
            level = "LOW"
            recommendation = "AUTO_APPROVE"
        elif score <= 70:
            level = "MEDIUM"
            recommendation = "MONITOR"
        else:
            level = "HIGH"
            recommendation = "BLOCK_AND_ESCALATE"

        # Track action in history
        self.action_history.append({
            "action": action_name,
            "params": action_params,
            "url": current_url,
            "score": score,
        })

        # Keep history manageable
        if len(self.action_history) > 50:
            self.action_history = self.action_history[-30:]

        breakdown = {
            "impact": impact,
            "capability_scope": round(capability_scope, 2),
            "intent_misalignment": round(intent_misalignment, 2),
            "anomaly_bonus": anomaly_bonus,
            "typosquat_bonus": typosquat_bonus,
            "raw_score": round(raw_score, 1),
        }

        return {
            "score": score,
            "level": level,
            "recommendation": recommendation,
            "breakdown": breakdown,
        }

    def _assess_intent_misalignment(
        self, action_name: str, action_params: dict, current_url: str
    ) -> float:
        """
        Estimate how much the current action deviates from the user's original task.
        Returns 0.0 (aligned) to 1.0 (completely misaligned).
        """
        if not self.user_task:
            return 0.3  # Moderate uncertainty if no task context

        # Extract relevant text from action
        action_text = ""
        if action_name == "input_text":
            action_text = action_params.get("text", "").lower()
        elif action_name in ["navigate", "go_to_url", "open_tab"]:
            action_text = action_params.get("url", "").lower()

        # Check if any task keywords appear in the action
        task_words = set(re.findall(r'\w+', self.user_task))
        task_words -= {"the", "a", "an", "in", "on", "at", "to", "for", "from", "and", "or", "is", "it", "me", "find", "get", "show"}

        if not action_text:
            return 0.1  # Can't assess, assume roughly aligned

        action_words = set(re.findall(r'\w+', action_text))

        overlap = task_words & action_words
        if overlap:
            return 0.0  # Action seems related to task

        # Check if URL domain is plausibly related
        if current_url:
            domain = urlparse(current_url).netloc.lower()
            if any(word in domain for word in task_words if len(word) > 3):
                return 0.1

        # No obvious connection — moderate misalignment
        return 0.5

    def _check_sequential_anomaly(self, action_name: str, action_params: dict) -> float:
        """
        Check for suspicious patterns in the action sequence.
        Returns bonus risk score (0-20).
        """
        if len(self.action_history) < 3:
            return 0

        recent = self.action_history[-5:]

        # Pattern: rapid navigation to many different domains
        nav_actions = [a for a in recent if a["action"] in ["navigate", "go_to_url", "open_tab"]]
        if len(nav_actions) >= 3:
            domains = set()
            for a in nav_actions:
                url = a["params"].get("url", "")
                try:
                    domains.add(urlparse(url).netloc)
                except Exception:
                    pass
            if len(domains) >= 3:
                return 15  # Suspicious rapid domain-hopping

        # Pattern: repeated failed actions (loops)
        if len(recent) >= 3:
            last_actions = [a["action"] for a in recent[-3:]]
            if len(set(last_actions)) == 1:
                return 10  # Stuck in a loop

        return 0

    def _check_typosquatting(self, url: str) -> bool:
        """Check if a URL looks like a typosquatted version of a known domain."""
        try:
            domain = urlparse(url).netloc.lower().split(":")[0]
            for legit, typos in TYPOSQUAT_PATTERNS.items():
                for typo in typos:
                    if typo in domain and legit not in domain:
                        logger.warning(
                            f"⚠️ Potential typosquatting detected: {domain} "
                            f"(looks like {legit})"
                        )
                        return True
        except Exception:
            pass
        return False

    def get_risk_level_str(self, score: int) -> str:
        """Get human-readable risk level from score."""
        if score <= 30:
            return "LOW"
        elif score <= 70:
            return "MEDIUM"
        else:
            return "CRITICAL" if score > 85 else "HIGH"
