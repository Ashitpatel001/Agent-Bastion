import logging
import json
import traceback
import contextvars
from datetime import datetime, timezone

# Thread-safe context variables for the current request
request_context = contextvars.ContextVar("request_context", default={})

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Inject context from contextvars
        context = request_context.get()
        if context:
            log_obj.update(context)
            
        # Also allow record-level overrides
        context_keys = [
            "request_id", "trace_id", "tenant_id", "user_id", "agent_id", 
            "execution_time_ms", "status_code", "ip", "user_agent", "correlation_id",
            "event_type", "action", "risk_score"
        ]
                        
        for key in context_keys:
            if hasattr(record, key):
                log_obj[key] = getattr(record, key)
                
        if record.exc_info:
            log_obj["exception"] = "".join(traceback.format_exception(*record.exc_info))
            
        return json.dumps(log_obj)

def setup_json_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    
    return logger
