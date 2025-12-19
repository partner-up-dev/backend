#!/usr/bin/env python3
"""Generate OpenAPI JSON documentation.

This script creates a FastAPI application instance solely for extracting
the OpenAPI schema. No server is started and no database connections are made,
so it works safely in CI environments without configuration.
"""

import json
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from run import create_app


def generate_openapi_json():
    """Generate OpenAPI JSON documentation from the FastAPI app."""
    # Create the FastAPI application (no server started, no DB connections)
    app = create_app()
    
    # Get the OpenAPI schema
    openapi_schema = app.openapi()
    
    # Define the output path
    output_path = project_root / "docs" / "openapi.json"
    
    # Ensure the docs directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write the OpenAPI schema to file
    with open(output_path, "w") as f:
        json.dump(openapi_schema, f, indent=2)
    
    print(f"✓ OpenAPI documentation generated successfully at: {output_path}")
    print(f"  Title: {openapi_schema.get('info', {}).get('title', 'N/A')}")
    print(f"  Version: {openapi_schema.get('info', {}).get('version', 'N/A')}")
    print(f"  Paths: {len(openapi_schema.get('paths', {}))}")


if __name__ == "__main__":
    generate_openapi_json()
