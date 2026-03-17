from specwatch.utils.logger import get_logger

logger = get_logger(__name__)


def validate_configs(vendors, registry, queries):

    logger.info("Validating configuration files")

    if not vendors:
        raise ValueError("vendors.json contains no vendors")

    if not queries:
        raise ValueError("discovery_queries.json contains no queries")

    for vendor in vendors:

        name = vendor.get("name")
        display = vendor.get("display_name")

        if not name or not display:
            raise ValueError(
                f"Invalid vendor entry: {vendor}"
            )

        if name not in registry:
            raise ValueError(
                f"Vendor '{name}' missing in vendor_registry.json"
            )

        trusted_domains = registry[name].get("trusted_domains")

        if not trusted_domains:
            raise ValueError(
                f"Vendor '{name}' has no trusted_domains"
            )

        if not isinstance(trusted_domains, list):
            raise ValueError(
                f"trusted_domains must be a list for {name}"
            )

        for domain in trusted_domains:

            if "." not in domain:
                raise ValueError(
                    f"Invalid domain '{domain}' for vendor '{name}'"
                )

    logger.info("Configuration validation successful")
