import os
from pathlib import Path
from openai import OpenAI


if Path(".env").exists():
    from dotenv import load_dotenv

    load_dotenv(override=True)

API_KEY = os.getenv("OPENAI_API_KEY", os.getenv("GITHUB_API_KEY"))

client = OpenAI(api_key=API_KEY)

# Note: we exit if the vector store already exists because
# OpenAI does not return the filenames of files in a vector store,
# meaning we cannot check if the files we want to upload
# already exist in the vector store.
# If you want to update the vector store, delete it first
# and then run this script again.
vector_stores = client.vector_stores.list()
if any(store.name == "Oregon Housing Law" for store in vector_stores):
    vector_store = next(
        store for store in vector_stores if store.name == "Oregon Housing Law"
    )
    print(
        f"Vector store 'Oregon Housing Law' already exists.\n"
        f"Add the following to your .env file to use this vector store:\n"
        f"VECTOR_STORE_ID={vector_store.id}\n"
    )
    exit(1)

else:
    print("Creating vector store 'Oregon Housing Law'.")

    # Create a new vector store
    vector_store = client.vector_stores.create(name="Oregon Housing Law")

    # Get all the files in ./documents
    documents_path = Path("./scripts/documents")
    file_paths = [
        f
        for f in os.listdir(documents_path)
        if os.path.isfile(os.path.join(documents_path, f))
    ]

    if not file_paths:
        print("No text files found in the documents directory.")
        exit(1)

    print("Uploading files to vector store...")
    file_streams = [
        open(os.path.join(documents_path, path), "rb") for path in file_paths
    ]
    # Add the files to the vector store
    file_batch = client.vector_stores.file_batches.upload_and_poll(
        vector_store_id=vector_store.id, files=file_streams
    )

    print(f"Uploaded files to vector store '{vector_store.name}'.")
    print(
        f"Add the following to your .env file to use this vector store:\n"
        f"VECTOR_STORE_ID={vector_store.id}\n"
    )
