"""Convert tenant_questions_facts_full.csv to LangSmith evaluation dataset.

This script uploads test scenarios from the manual evaluation CSV to LangSmith
for automated evaluation.
"""

import argparse
import ast
import os
from pathlib import Path
from typing import List, Dict

import polars as pd
from langsmith import Client

if Path("../.env").exists():
    from dotenv import load_dotenv

    load_dotenv(override=True)


def create_langsmith_dataset(
    input_csv: Path, limit_examples: int, dataset_name: str, overwrite_dataset=False
):
    """Upload test scenarios to LangSmith for automated evaluation."""
    client = Client(api_key=os.getenv("LANGSMITH_API_KEY"))

    # print(client.info)

    dataset_exists = client.has_dataset(dataset_name=dataset_name)
    if dataset_exists:
        if overwrite_dataset:
            print(f"-INFO- Dataset '{dataset_name}' already exists. Deleting for overwrite.")
            client.delete_dataset(dataset_name=dataset_name)
        else:
            raise RuntimeError(
                f"-ERROR- Dataset '{dataset_name}' already exists. Aborting to avoid duplicates."
            )

    # Create dataset in LangSmith.
    dataset = client.create_dataset(
        dataset_name=dataset_name,
        description="Test scenarios for Oregon tenant legal advice chatbot",
    )

    # Read existing test scenarios.
    csv_path = input_csv

    # Try UTF-8 first, fallback to cp1252 if needed
    try:
        df = pd.read_csv(csv_path, encoding="utf-8", n_rows=limit_examples)
    except UnicodeDecodeError:
        df = pd.read_csv(csv_path, encoding="cp1252", n_rows=limit_examples)

    # replace all empty "city" values with "null" string
    df["city"].fill_null("null")

    # Convert each row to LangSmith example.
    for idx, row in enumerate(df.rows(named=True)):

        facts = (
            ast.literal_eval(row["facts"])
            if isinstance(row["facts"], str)
            else row["facts"]
        )
        city = row["city"] # if not pd.is_null(row["city"]) else "null"

        reference_conversation: List[Dict[str, str]] = []
        if row.get("Original conversation") is not None:
            for line in row.get("Original conversation").splitlines():
                if line.startswith("You:"):
                    reference_conversation.append(
                        {"role": "user", "content": line.replace("You:", "").strip()}
                    )
                elif line.startswith("Bot:"):
                    reference_conversation.append(
                        {"role": "assistant", "content": line.replace("Bot:", "").strip()}
                    )
                else:
                    if line.strip() == "":
                        continue
                    reference_conversation[-1]["content"] += "\n" + line.strip()
                

        # Each example has inputs and expected metadata.
        client.create_example(
            dataset_id=dataset.id,
            inputs={
                "first_question": row["first_question"],
                "city": city,
                "state": row["state"],
                "facts": facts,
                # "message": reference_conversation
            },
            metadata={
                "scenario_id": idx,
                "city": city,
                "state": row["state"],
                # Tag scenarios for filtering.
                "tags": [f"city-{city}", f"state-{row['state']}"],
            },
            # Optionally include reference conversation for comparison.
            outputs={"reference_conversation": reference_conversation},
        )

    print(f"Created dataset '{dataset.name}' with {len(df)} scenarios")
    return dataset


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=Path(__file__).parent
        / "generate_conversation/tenant_questions_facts_full.csv",
        help="Path to input CSV file",
    )
    parser.add_argument(
        "--limit-examples",
        type=int,
        default=None,
        help="Limit number of examples to upload",
    )
    parser.add_argument(
        "--dataset-name",
        type=str,
        default="tenant-legal-qa-scenarios",
        help="LangSmith dataset name",
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing dataset"
    )
    args = parser.parse_args()

    create_langsmith_dataset(
        input_csv=args.input_csv,
        limit_examples=args.limit_examples,
        dataset_name=args.dataset_name,
        overwrite_dataset=args.overwrite,
    )
