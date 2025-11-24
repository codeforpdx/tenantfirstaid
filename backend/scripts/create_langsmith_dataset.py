"""Convert tenant_questions_facts_full.csv to LangSmith evaluation dataset.

This script uploads test scenarios from the manual evaluation CSV to LangSmith
for automated evaluation.
"""

import ast
from pathlib import Path

import pandas as pd
from langsmith import Client


def create_langsmith_dataset():
    """Upload test scenarios to LangSmith for automated evaluation."""
    client = Client()

    # Read existing test scenarios.
    csv_path = Path(__file__).parent / "generate_conversation" / "tenant_questions_facts_full.csv"
    df = pd.read_csv(csv_path, encoding="cp1252")

    # Create dataset in LangSmith.
    dataset = client.create_dataset(
        dataset_name="tenant-legal-qa-scenarios",
        description="Test scenarios for Oregon tenant legal advice chatbot",
    )

    # Convert each row to LangSmith example.
    for idx, row in df.iterrows():
        facts = (
            ast.literal_eval(row["facts"])
            if isinstance(row["facts"], str)
            else row["facts"]
        )
        city = row["city"] if not pd.isna(row["city"]) else "null"

        # Each example has inputs and expected metadata.
        client.create_example(
            dataset_id=dataset.id,
            inputs={
                "first_question": row["first_question"],
                "city": city,
                "state": row["state"],
                "facts": facts,
            },
            metadata={
                "scenario_id": idx,
                "city": city,
                "state": row["state"],
                # Tag scenarios for filtering.
                "tags": ["tenant-rights", f"city-{city}", f"state-{row['state']}"],
            },
            # Optionally include reference conversation for comparison.
            outputs={
                "reference_conversation": row.get("Original conversation", None)
            },
        )

    print(f"Created dataset '{dataset.name}' with {len(df)} scenarios")
    return dataset


if __name__ == "__main__":
    create_langsmith_dataset()
