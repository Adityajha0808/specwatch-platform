#!/usr/bin/env python3
"""
OpenAPI URL resolver.
Resolves various GitHub/docs URLs to actual spec URLs.
"""

import requests
from urllib.parse import urlparse
from specwatch.utils.logger import get_logger
from specwatch.utils.http_client import url_exists
from specwatch.config.vendor_specs_loader import load_vendor_specs

logger = get_logger(__name__)

COMMON_SPEC_PATHS = [
    "openapi.yaml",
    "openapi.yml",
    "swagger.yaml",
    "swagger.yml",
    "openapi/spec3.yaml",
    "spec/openapi.yaml",
    "openapi/openapi.yaml"
]


GITHUB_API = "https://api.github.com/repos"

# To recursively scan directory upto level 3
MAX_SCAN_DEPTH = 3

VENDOR_SPECS = load_vendor_specs()


# DIfferent strategies to convert direct specs into actual spec URLs
class OpenAPIResolver:


    def resolve(self, vendor, source_url: str):

        vendor = vendor.lower()
    
        # Known vendor specs
        if vendor in VENDOR_SPECS:

            spec_url = VENDOR_SPECS[vendor]
        
            if url_exists(spec_url):
                logger.info(f"Using configured OpenAPI spec for {vendor}: {spec_url}")
                return spec_url
    
        # Direct spec URL
        if self._is_direct_spec(source_url):
            logger.info(f"Direct spec URL detected: {source_url}")
            return source_url
    
        # Stainless hosted specs
        if "stainless.com" in source_url:
            logger.info(f"Stainless spec detected: {source_url}")
            return source_url
    
        # GitHub repo resolver
        if "github.com" in source_url:
            spec = self._resolve_github_repo(source_url)
            if spec:
                return spec
    
        # Fallback brute force
        return self._brute_force_resolve(source_url)


    def _is_direct_spec(self, url: str):
        return url.endswith((".yaml", ".yml", ".json"))


    def _resolve_github_repo(self, repo_url: str):

        parts = urlparse(repo_url)
        path = parts.path.strip("/").split("/")

        if len(path) < 2:
            return None

        owner = path[0]
        repo = path[1]

        api_url = f"{GITHUB_API}/{owner}/{repo}/contents"

        try:
            response = requests.get(api_url, headers={"User-Agent": "specwatch"})
            response.raise_for_status()

            files = response.json()

            for file in files:

                if file["type"] == "file":
                    name = file["name"].lower()

                    if name.endswith((".yaml", ".yml")) and (
                        "openapi" in name or "swagger" in name
                    ):
                        logger.info(f"OpenAPI spec found in repo root: {file['download_url']}")
                        return file["download_url"]

                if file["type"] == "dir":

                    if file["name"].lower() not in ["spec", "openapi", "api", "docs"]:
                        continue

                    spec = self._scan_directory(owner, repo, file["path"], depth=1)
                    
                    if spec:
                        return spec

        except Exception as e:
            logger.warning(f"GitHub API scan failed: {e}")

        return None


    def _scan_directory(self, owner, repo, directory, depth):

        if depth > MAX_SCAN_DEPTH:
            logger.debug(f"Max depth reached at {directory}")
            return None
    
        api_url = f"{GITHUB_API}/{owner}/{repo}/contents/{directory}"
    
        try:
            response = requests.get(api_url, headers={"User-Agent": "specwatch"}, timeout=10)
            response.raise_for_status()
    
            files = response.json()
    
            for file in files:
    
                # Checking files first
                if file["type"] == "file":
                    name = file["name"].lower()
    
                    if name.endswith((".yaml", ".yml", ".json")) and (
                        "openapi" in name or "swagger" in name
                    ):
                        logger.info(f"OpenAPI spec found: {file['download_url']}")
                        return file["download_url"]
    
            # Recursing later into directories
            for file in files:
    
                if file["type"] == "dir":

                    if file["name"].lower() not in ["spec", "openapi", "api", "docs"]:
                        continue
                    
                    spec = self._scan_directory(
                        owner,
                        repo,
                        file["path"],
                        depth=depth + 1
                    )
    
                    if spec:
                        return spec
    
        except Exception as e:
            logger.warning(f"Directory scan failed: {directory} ({e})")
    
        return None


    def _brute_force_resolve(self, source_url: str):

        branches = ["main", "master"]
    
        for branch in branches:
            for path in COMMON_SPEC_PATHS:
    
                raw_url = source_url.rstrip("/").replace(
                    "github.com",
                    "raw.githubusercontent.com"
                )
    
                raw_url = f"{raw_url}/{branch}/{path}"
    
                if url_exists(raw_url):
    
                    logger.info(f"Resolved OpenAPI spec: {raw_url}")
                    return raw_url
    
        logger.error("Unable to resolve OpenAPI spec")
    
        return None
