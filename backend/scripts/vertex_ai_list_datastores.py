"""Dump info on Vertex AI Search datastores for a GCP project.

To run:
  uv run python -m scripts.vertex_ai_list_datastores
"""

from google.cloud import discoveryengine

from tenantfirstaid.google_auth import discoveryengine_client_options

project_id = "tenantfirstaid"  # Replace with your GCP project ID
location = "global"  # Values: "global"


def list_data_stores(project_id: str, location: str) -> None:
    client = discoveryengine.DataStoreServiceClient(
        client_options=discoveryengine_client_options(location)
    )

    request = discoveryengine.ListDataStoresRequest(
        # The full resource name of the data store
        parent=client.collection_path(
            project_id, location, collection="default_collection"
        )
    )

    # Make the request
    response = client.list_data_stores(request=request)

    for data_store in response:
        print(data_store)
        print("----\n")


if __name__ == "__main__":
    list_data_stores(project_id=project_id, location=location)
