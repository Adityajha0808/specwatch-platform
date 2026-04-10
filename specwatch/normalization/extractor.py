"""
OpenAPI Data Extractor

Extracts endpoints, parameters, and metadata from parsed OpenAPI specs.
Handles parameter extraction from multiple locations (path, query, header, body).
"""

from typing import List, Dict, Any

from specwatch.utils.logger import get_logger

logger = get_logger(__name__)


# Extract all endpoints from OpenAPI paths
def extract_endpoints(spec: dict) -> List[Dict[str, Any]]:

    logger.info("Extracting endpoints")
    
    endpoints = []
    paths = spec.get('paths', {})
    
    logger.info(f"Paths found {len(paths)}")
    
    for path, path_item in paths.items():
        logger.info(f"Processing path {path}")
        
        # Skip parameters and other non-method keys
        for method in ['get', 'post', 'put', 'delete', 'patch', 'head', 'options']:
            if method not in path_item:
                continue
            
            logger.info(f"Processing method {method.upper()} for {path}")
            
            operation = path_item[method]
            
            # Extract parameters
            parameters = extract_parameters(operation, path)

            # Unique endpoint ID
            endpoint_id = f"{method.upper()}:{path}"

            # Extract response status codes
            responses = operation.get('responses', {})
            response_codes = sorted(list(responses.keys()))
            
            # Build endpoint object
            endpoint = {
                'id': endpoint_id,
                'path': path,
                'method': method.upper(),
                'summary': operation.get('summary', ''),
                'deprecated': operation.get('deprecated', False),
                'parameters': parameters,
                'request_body_required': _is_request_body_required(operation),
                'auth_required': _is_auth_required(operation, spec),
                'responses': response_codes
            }
            
            logger.info(f"Endpoint extracted. ID: {endpoint_id} {method.upper()} {path} with {len(parameters)} params")
            
            endpoints.append(endpoint)
    
    logger.info(f"Endpoints extraction complete total {len(endpoints)}")

    # Sorting endpoints deterministically in tuple (first path then method) format
    endpoints_sorted = sorted(
        endpoints,
        key=lambda e: (e['path'], e['method'])
    )
    
    logger.info("Endpoints sorted")
    
    return endpoints_sorted


# Extract parameters from an OpenAPI operation
def extract_parameters(operation: dict, path: str) -> List[Dict[str, Any]]:

    logger.info(f"Extracting parameters for {path}")
    
    params = []
    
    # Extract path/query/header parameters
    operation_params = operation.get('parameters', [])
    logger.info(f"Operation parameters found {len(operation_params)} for {path}")
    
    for param in operation_params:
        param_obj = {
            'name': param.get('name', ''),
            'location': param.get('in', 'query'),
            'required': param.get('required', False),
            'type': _extract_param_type(param),
            'description': param.get('description', '')
        }
        
        logger.info(f"Parameter extracted {param_obj['name']} in {param_obj['location']}")
        
        params.append(param_obj)
    
    # Extract request body parameters (if JSON)
    request_body = operation.get('requestBody', {})
    if request_body:
        logger.info(f"Extracting body parameters for {path}")
        body_params = _extract_body_params(request_body)
        logger.info(f"Body parameters extracted {len(body_params)} for {path}")
        params.extend(body_params)
    
    logger.info(f"Parameters extraction complete total {len(params)} for {path}")
    
    params_sorted = sorted(
        params,
        key=lambda p: (p['location'], p['name'])
    )
    
    logger.debug(f"parameters sorted. Count={len(params_sorted)}. Path={path}")
    
    return params_sorted


# Extract parameter type from schema
def _extract_param_type(param: dict) -> str:

    schema = param.get('schema', {})
    param_type = schema.get('type', 'string')
    
    logger.info(f"Parameter type extracted {param.get('name', 'unknown')} type {param_type}")
    
    return param_type


# Extract parameters from request body schema
def _extract_body_params(request_body: dict) -> List[Dict[str, Any]]:

    logger.info("Extracting body parameters")
    
    params = []
    
    # Get JSON content schema
    content = request_body.get('content', {})
    logger.info(f"Content types found {list(content.keys())}")
    
    json_schema = content.get('application/json', {}).get('schema', {})
    
    if not json_schema:
        logger.info("No JSON schema found skipping body parameter extraction")
        return params
    
    # Extract properties
    properties = json_schema.get('properties', {})
    required_fields = json_schema.get('required', [])
    
    logger.info(f"Body schema found properties {len(properties)} required {len(required_fields)}")
    
    for prop_name, prop_schema in properties.items():
        param_obj = {
            'name': prop_name,
            'location': 'body',
            'required': prop_name in required_fields,
            'type': prop_schema.get('type', 'string'),
            'description': prop_schema.get('description', '')
        }
        
        logger.info(f"Body parameter extracted {prop_name}")
        
        params.append(param_obj)
    
    logger.info(f"Body parameters extraction complete total {len(params)}")
    return params


# Check if request body is required
def _is_request_body_required(operation: dict) -> bool:

    request_body = operation.get('requestBody', {})
    is_required = request_body.get('required', False)
    
    logger.info(f"Request body required {is_required}")
    
    return is_required


# Determine if authentication is required
def _is_auth_required(operation: dict, spec: dict) -> bool:

    security = operation.get('security', spec.get('security', []))
    
    logger.info(f"Authentication check security count {len(security)}")
    
    # If security is empty list [], it means no auth required
    if security == []:
        logger.info("Authentication not required empty security")
        return False
    
    # If security has entries, auth is required
    is_required = len(security) > 0
    logger.info(f"Authentication required {is_required}")
    
    return is_required
