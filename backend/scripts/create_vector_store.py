import os
from pathlib import Path
from openai import OpenAI

dotenv_path = Path(__file__).parent.parent / ".env"
if dotenv_path.exists():
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=dotenv_path, override=True)

API_KEY = os.getenv("OPENAI_API_KEY", os.getenv("GITHUB_API_KEY"))

client = OpenAI(api_key=API_KEY)

# TODO: Would be nice to have a better way to check for the vector store than just the name.
vector_stores = client.vector_stores.list()
if any(store.name == "Oregon Housing Law" for store in vector_stores):
    vector_store = next(
        store for store in vector_stores if store.name == "Oregon Housing Law"
    )
    # Delete all files in the vector store
    vector_store_files = client.vector_stores.files.list(
        vector_store_id=vector_store.id
    )
    for file in vector_store_files:
        print(f"Deleting file {file.id} from vector store '{vector_store.name}'.")
        client.vector_stores.files.delete(
            vector_store_id=vector_store.id, file_id=file.id
        )
        client.files.delete(file_id=file.id)

else:
    print("Creating vector store 'Oregon Housing Law'.")

    # Create a new vector store
    vector_store = client.vector_stores.create(name="Oregon Housing Law")

# Get list of all directories in ./scripts/documents
documents_path = Path(__file__).parent / "documents"
for dirpath, dirnames, filenames in os.walk(documents_path):
    subdir = dirpath.replace(str(documents_path), "").strip(os.sep)
    if len(filenames) > 0:
        subdirs = (
            subdir.split(os.sep) + [None] * 2
        )  # Ensure we have at least two subdirs

        # some type coercion to match OpenAI's expectations
        attributes: dict[str, bool | float | str] = {}
        # Openai doesn't allow querying by empty attributes, so we set them to "null"
        if subdirs[1]:
            attributes["city"] = str(subdirs[1])
        else:
            attributes["city"] = "null"
        if subdirs[0]:
            attributes["state"] = str(subdirs[0])

        file_ids = []
        for filename in filenames:
            file_path = Path(dirpath) / filename

            # Ensure the file is UTF-8 encoded
            # OpenAI rejects the file if not
            path = Path(file_path)
            path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

            print(f"Uploading {file_path} to vector store '{vector_store.name}'.")
            file_obj = client.files.create(
                file=open(file_path, "rb"),
                purpose="assistants",
            )
            file_ids.append(file_obj.id)

        # Add files to the vector store
        batch_upload = client.vector_stores.file_batches.create(
            vector_store_id=vector_store.id,
            file_ids=file_ids,
            attributes=attributes,  # Only take the first two subdirs
        )

print(f"Uploaded files to vector store '{vector_store.name}'.")
print(
    f"Add the following to your .env file to use this vector store:\n"
    f"VECTOR_STORE_ID={vector_store.id}\n"
)
