import time
import json
import re
import os
from openai import OpenAI

from tenantfirstaid.chat import DEFAULT_INSTRUCTIONS

API_KEY = os.getenv("OPENAI_API_KEY", os.getenv("GITHUB_API_KEY"))
BASE_URL = os.getenv("MODEL_ENDPOINT", "https://api.openai.com/v1")
MODEL = os.getenv("MODEL_NAME", "o3")
MODEL_REASONING_EFFORT = os.getenv("MODEL_REASONING_EFFORT", "medium")

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
)


VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID")
openai_tools = []

if VECTOR_STORE_ID:
    openai_tools.append({"type": "file_search", "vector_store_ids": [VECTOR_STORE_ID]})

# 1. Load the dataset - updated to use path relative to this script
script_dir = os.path.dirname(os.path.abspath(__file__))
dataset_path = os.path.join(script_dir, "tenant_tests.jsonl")
with open(dataset_path, "r") as f:
    samples = [json.loads(line) for line in f]

# 3. Run the evaluation manually
results = []
scores = []
times = []

for i, sample in enumerate(samples):
    print(f"Processing sample {i + 1}/{len(samples)}...")

    # Format messages for the Responses API
    input_messages = []
    for msg in sample["messages"]:
        input_messages.append({"role": msg["role"], "content": msg["content"]})

    # get the start time for response time measurement
    start_time = time.time()

    # Use the Responses API with streaming
    response = client.responses.create(
        model=MODEL,
        input=input_messages,
        instructions=DEFAULT_INSTRUCTIONS,
        reasoning={"effort": MODEL_REASONING_EFFORT},
        tools=openai_tools,
    )

    end_time = time.time()
    duration = end_time - start_time
    times.append(duration)
    print(f"Response time: {duration:.2f} seconds")

    # Collect the full response

    # Join the complete response
    model_answer = response.output_text
    ideal_answer = sample["ideal"]

    # Use o3 as a judge to evaluate the model's response - asking only for numerical score
    judge_response = client.chat.completions.create(
        model="o3",
        messages=[
            {
                "role": "system",
                "content": "You are an impartial judge evaluating the quality of a response compared to an ideal answer. Provide ONLY a score from 0-10 with no explanation. Just the number.",
            },
            {
                "role": "user",
                "content": f"Conversation: {sample['messages']}\n\nModel answer: {model_answer}\n\nIdeal answer: {ideal_answer}\n\nScore (0-10):",
            },
        ],
    )

    judge_feedback = judge_response.choices[0].message.content

    # Extract just the numerical score
    score_match = re.search(r"\b([0-9]|10)\b", judge_feedback)
    if score_match:
        score = int(score_match.group(1))
    else:
        # Fallback if we can't extract a clear number
        print(f"Warning: Could not extract clear score from: {judge_feedback}")
        score = 0

    scores.append(score)
    print(f"Score: {score}/10")
    print("-" * 40)

    # Store results
    results.append(
        {
            "sample_index": i,
            "conversation": sample["messages"],
            "model_answer": model_answer,
            "ideal_answer": ideal_answer,
            "score": score,
            "response_time": duration,
        }
    )

# Calculate average score
average_score = sum(scores) / len(scores) if scores else 0

# Calculate average response time
average_time = sum(times) / len(times) if times else 0

# 4. Print summary
print("\n===== EVALUATION SUMMARY =====")
print(f"Model evaluated: {MODEL}")
print(f"Number of samples: {len(samples)}")
print(f"Average score: {average_score:.2f}/10")
print(f"Average response time: {average_time:.2f} seconds")

# Individual scores
print("\nIndividual scores:")
for i, score in enumerate(scores):
    print(f"Sample {i + 1}: {score}/10")

results_path = os.path.join(script_dir, "eval_results.json")
with open(results_path, "w") as f:
    json.dump(
        {
            "model": MODEL,
            "reasoning_effort": MODEL_REASONING_EFFORT,
            "average_score": average_score,
            "samples": results,
        },
        f,
        indent=2,
    )

print(f"\nDetailed results saved to {results_path}")
