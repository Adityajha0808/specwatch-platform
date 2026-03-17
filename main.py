from pipelines.discovery_pipeline import run_discovery
from pipelines.ingestion_pipeline import run_ingestion

# Entry point
if __name__ == "__main__":
    run_discovery() # Run discovery layer
    run_ingestion() # Run ingestion layer
