"""Generate a JSON Schema for all Pydantic models exported to the frontend.

Usage: npm run generate-types (from frontend/) or make generate-types (from backend/).
"""

import json

from pydantic import RootModel
from pydantic.json_schema import models_json_schema

from tenantfirstaid.location import Location
from tenantfirstaid.schema import ResponseChunk as ResponseChunkType


class ResponseChunk(RootModel[ResponseChunkType]):
    """Union of all possible streaming response chunk types.

    New chunk variants added to schema.py are picked up automatically through ResponseChunkType.
    """


_, schema = models_json_schema(
    [
        (Location, "serialization"),
        (ResponseChunk, "serialization"),
    ],
    title="TenantFirstAid Models",
)

print(json.dumps(schema, indent=2))
