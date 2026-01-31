"""
Dump out info on project datastores in Google Workspace

Note: does not require credentials or authentication(?)

To run:
  % uv run simple_langchain_example.py
"""

from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine

project_id = "tenantfirstaid"  # Replace with your GCP project ID
location = "global"  # Values: "global"


def list_data_stores(
    project_id: str,
    location: str,
):  # -> discoveryengine.ListDataStoresResponse:
    #  For more information, refer to:
    # https://cloud.google.com/generative-ai-app-builder/docs/locations#specify_a_multi-region_for_your_data_store
    client_options = (
        ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
        if location != "global"
        else None
    )

    # Create a client
    client = discoveryengine.DataStoreServiceClient(client_options=client_options)

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
