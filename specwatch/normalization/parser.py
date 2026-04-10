"""
OpenAPI Specification Parser

Handles loading and validation of OpenAPI specs from YAML/JSON files.
Supports OpenAPI 3.x format.
"""

import yaml
import json
from pathlib import Path
from typing import Dict, Any

from specwatch.utils.logger import get_logger

logger = get_logger(__name__)


# Raised when OpenAPI spec cannot be parsed
class OpenAPIParseError(Exception):
    pass


# Load OpenAPI spec from file (YAML or JSON)
def load_openapi_spec(filepath: str) -> Dict[str, Any]:

    logger.info(f"Loading OpenAPI spec from {filepath}")
    
    path = Path(filepath)
    
    if not path.exists():
        logger.error(f"File not found {filepath}")
        raise OpenAPIParseError(f"File not found: {filepath}")
    
    logger.info(f"Reading file {filepath} size {path.stat().st_size}")
    content = path.read_text()
    
    # Try JSON first
    if path.suffix.lower() in ['.json']:
        logger.info(f"Parsing as JSON {filepath}")
        try:
            spec = json.loads(content)
            logger.info(f"JSON parsed successfully {filepath} keys {list(spec.keys())}")
            return spec
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse failed {filepath} error {str(e)} line {e.lineno}")
            raise OpenAPIParseError(f"Invalid JSON: {e}")
    
    # Try YAML
    elif path.suffix.lower() in ['.yaml', '.yml']:
        logger.info(f"Parsing as YAML {filepath}")
        try:
            spec = yaml.safe_load(content)
            logger.info(f"YAML parsed successfully {filepath} keys {list(spec.keys())}")
            return spec
        except yaml.YAMLError as e:
            logger.error(f"YAML parse failed {filepath} error {str(e)}")
            raise OpenAPIParseError(f"Invalid YAML: {e}")
    
    else:
        logger.error(f"Unsupported file type {filepath} suffix {path.suffix}")
        raise OpenAPIParseError(f"Unsupported file type: {path.suffix}")


# Extract and validate OpenAPI version from spec
def validate_openapi_version(spec: dict) -> str:

    logger.info(f"Validating OpenAPI version with keys {list(spec.keys())}")
    
    version = spec.get('openapi') or spec.get('swagger')
    
    if not version:
        logger.error(f"Version field missing available keys {list(spec.keys())}")
        raise OpenAPIParseError("Missing 'openapi' or 'swagger' field")
    
    logger.info(f"Version found {version}")
    
    # Support OpenAPI 3.x (most common)
    if not version.startswith('3.'):
        logger.warning(f"Unsupported version {version} supported 3.x")
        raise OpenAPIParseError(f"Unsupported OpenAPI version: {version}")
    
    logger.info(f"OpenAPI version validated {version}")
    return version


# Extract base URL from OpenAPI servers field
def get_base_url(spec: dict) -> str:

    logger.info("Extracting base URL")
    
    # OpenAPI 3.x: servers[0].url
    servers = spec.get('servers', [])
    logger.info(f"Servers found {len(servers)}")
    
    if servers and isinstance(servers, list) and len(servers) > 0:
        base_url = servers[0].get('url', '')
        logger.info(f"Base URL extracted {base_url} from {len(servers)} servers")
        return base_url
    
    logger.warning("No base URL found servers field missing or empty")
    return ''
