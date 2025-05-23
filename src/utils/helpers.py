"""
Utility helper functions for the DevOps Sentinel Multi-Agent System.
Provides common functionality used across different components.
"""

import json
import re
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path
import asyncio
import logging
from decimal import Decimal, ROUND_HALF_UP

# Setup module logger
logger = logging.getLogger(__name__)


def get_current_timestamp() -> str:
    """Get the current timestamp in ISO format."""
    return datetime.now().isoformat()


def get_timestamp_with_offset(hours: int = 0, minutes: int = 0) -> str:
    """Get timestamp with specified offset from current time."""
    target_time = datetime.now() + timedelta(hours=hours, minutes=minutes)
    return target_time.isoformat()


def format_report(data: Dict[str, Any], format_type: str = "simple") -> str:
    """
    Format the report data into a readable string.
    
    Args:
        data: Dictionary containing report data
        format_type: Type of formatting ('simple', 'detailed', 'json')
    """
    if format_type == "json":
        return json.dumps(data, indent=2, default=str)
    elif format_type == "detailed":
        lines = []
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{key}:")
                for sub_key, sub_value in value.items():
                    lines.append(f"  {sub_key}: {sub_value}")
            elif isinstance(value, list):
                lines.append(f"{key}: {len(value)} items")
                for i, item in enumerate(value[:3]):  # Show first 3 items
                    lines.append(f"  {i+1}. {item}")
                if len(value) > 3:
                    lines.append(f"  ... and {len(value) - 3} more")
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)
    else:  # simple format
        return "\n".join([f"{key}: {value}" for key, value in data.items()])


def validate_configuration(config: Dict[str, Any], required_keys: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate that the configuration contains all required keys.
    
    Returns:
        Tuple of (is_valid, missing_keys)
    """
    missing_keys = [key for key in required_keys if key not in config]
    return len(missing_keys) == 0, missing_keys


def validate_azure_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate Azure-specific configuration."""
    required_keys = [
        "subscription_id",
        "resource_group",
        "tenant_id"
    ]
    return validate_configuration(config, required_keys)


def validate_kubernetes_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate Kubernetes-specific configuration."""
    required_keys = [
        "cluster_name",
        "namespace"
    ]
    return validate_configuration(config, required_keys)


def sanitize_string(input_string: str, allow_special_chars: bool = False) -> str:
    """
    Sanitize input string for safe usage.
    
    Args:
        input_string: String to sanitize
        allow_special_chars: Whether to allow special characters
    """
    if not allow_special_chars:
        # Remove all non-alphanumeric characters except spaces, hyphens, and underscores
        return re.sub(r'[^a-zA-Z0-9\s\-_]', '', input_string)
    else:
        # Remove only potentially dangerous characters
        return re.sub(r'[<>"\';()&+]', '', input_string)


def generate_correlation_id() -> str:
    """Generate a unique correlation ID for tracking requests."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_part = base64.urlsafe_b64encode(
        hashlib.md5(str(datetime.now().timestamp()).encode()).digest()[:6]
    ).decode().rstrip('=')
    return f"{timestamp}-{random_part}"


def calculate_hash(data: Union[str, bytes, Dict[str, Any]]) -> str:
    """Calculate SHA256 hash of data."""
    if isinstance(data, dict):
        data = json.dumps(data, sort_keys=True)
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def format_bytes(bytes_value: int) -> str:
    """Format bytes into human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024
    return f"{bytes_value:.2f} PB"


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable format."""
    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.2f}m"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.2f}h"
    else:
        days = seconds / 86400
        return f"{days:.2f}d"


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format currency amount."""
    decimal_amount = Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return f"{decimal_amount:.2f} {currency}"


def parse_resource_name(resource_name: str) -> Dict[str, str]:
    """
    Parse Azure resource name to extract components.
    
    Expected format: /subscriptions/{sub_id}/resourceGroups/{rg_name}/providers/{provider}/{resource_type}/{name}
    """
    parts = resource_name.strip('/').split('/')
    if len(parts) >= 8:
        return {
            'subscription_id': parts[1],
            'resource_group': parts[3],
            'provider': parts[5],
            'resource_type': parts[6],
            'name': parts[7]
        }
    return {}


def chunk_list(input_list: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split a list into chunks of specified size."""
    return [input_list[i:i + chunk_size] for i in range(0, len(input_list), chunk_size)]


def flatten_dict(nested_dict: Dict[str, Any], separator: str = '.') -> Dict[str, Any]:
    """Flatten a nested dictionary."""
    def _flatten(obj: Any, parent_key: str = '') -> Dict[str, Any]:
        items = []
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_key = f"{parent_key}{separator}{key}" if parent_key else key
                items.extend(_flatten(value, new_key).items())
        else:
            return {parent_key: obj}
        return dict(items)
    
    return _flatten(nested_dict)


def deep_merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries."""
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


async def retry_async(
    func,
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple = (Exception,)
) -> Any:
    """
    Retry an async function with exponential backoff.
    
    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries
        backoff_factor: Factor by which delay increases each retry
        exceptions: Tuple of exceptions to catch and retry on
    """
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except exceptions as e:
            if attempt == max_retries:
                logger.error(f"Function {func.__name__} failed after {max_retries} retries: {e}")
                raise
            
            wait_time = delay * (backoff_factor ** attempt)
            logger.warning(f"Function {func.__name__} failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
            await asyncio.sleep(wait_time)


def get_nested_value(data: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """
    Get nested value from dictionary using dot notation.
    
    Example: get_nested_value(data, 'azure.openai.api_key', 'default_key')
    """
    keys = key_path.split('.')
    current = data
    
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    
    return current


def set_nested_value(data: Dict[str, Any], key_path: str, value: Any) -> None:
    """
    Set nested value in dictionary using dot notation.
    
    Example: set_nested_value(data, 'azure.openai.api_key', 'new_key')
    """
    keys = key_path.split('.')
    current = data
    
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    current[keys[-1]] = value


def validate_email(email: str) -> bool:
    """Validate email address format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_url(url: str) -> bool:
    """Validate URL format."""
    pattern = r'^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$'
    return re.match(pattern, url) is not None


def safe_json_loads(json_string: str, default: Any = None) -> Any:
    """Safely load JSON string with default fallback."""
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError):
        logger.warning(f"Failed to parse JSON: {json_string[:100]}...")
        return default


def create_directory_if_not_exists(directory_path: Union[str, Path]) -> Path:
    """Create directory if it doesn't exist."""
    path = Path(directory_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_file_size(file_path: Union[str, Path]) -> int:
    """Get file size in bytes."""
    return Path(file_path).stat().st_size


def is_file_older_than(file_path: Union[str, Path], hours: int) -> bool:
    """Check if file is older than specified hours."""
    file_time = datetime.fromtimestamp(Path(file_path).stat().st_mtime)
    return datetime.now() - file_time > timedelta(hours=hours)


class Timer:
    """Context manager for timing operations."""
    
    def __init__(self, operation_name: str = "Operation"):
        self.operation_name = operation_name
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        logger.info(f"{self.operation_name} completed in {format_duration(duration)}")
    
    @property
    def duration(self) -> Optional[float]:
        """Get duration in seconds if timing is complete."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


# Commonly used validation patterns
PATTERNS = {
    'azure_subscription_id': r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    'kubernetes_name': r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$',
    'semver': r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'
}


def validate_pattern(value: str, pattern_name: str) -> bool:
    """Validate value against predefined patterns."""
    if pattern_name not in PATTERNS:
        raise ValueError(f"Unknown pattern: {pattern_name}")
    
    return re.match(PATTERNS[pattern_name], value) is not None