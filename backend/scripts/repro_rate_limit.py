"""Reproduction: /api/query has NO rate limit, while /api/feedback does.

Uses the real Flask app from tenantfirstaid.app with the LLM chat manager and
the email sender mocked out, so no external calls are made. We fire a burst of
requests at each endpoint and report the status codes.

Expected (buggy) behavior:
  - /api/query  : 20/20 requests return 200, ZERO 429s  -> unthrottled, cost risk
  - /api/feedback: first 3 return 200, the rest return 429 -> throttled
"""

from collections import Counter
from unittest.mock import patch

from tenantfirstaid.app import app, limiter


def fire_query(client, n):
    """Send n POSTs to /api/query with a mocked chat manager."""
    codes = []
    with patch("tenantfirstaid.chat.LangChainChatManager") as mock_cm:
        mock_cm.return_value.generate_streaming_response.return_value = iter(
            [{"type": "text", "text": "mocked legal advice"}]
        )
        for _ in range(n):
            resp = client.post(
                "/api/query",
                json={
                    "messages": [{"role": "human", "content": "hi"}],
                    "city": None,
                    "state": "or",
                },
            )
            # Drain the streaming body so the request fully completes.
            resp.get_data()
            codes.append(resp.status_code)
    return Counter(codes)


def fire_feedback(client, n):
    """Send n POSTs to /api/feedback with a mocked email sender."""
    codes = []
    with (
        patch("tenantfirstaid.feedback.EmailMessage"),
        patch.dict(
            "os.environ", {"SENDER_EMAIL": "s@t.com", "RECIPIENT_EMAIL": "r@t.com"}
        ),
    ):
        for _ in range(n):
            resp = client.post(
                "/api/feedback",
                data={"name": "Jane", "subject": "Bug", "feedback": "Broken"},
            )
            codes.append(resp.status_code)
    return Counter(codes)


def run_trial(trial_no, burst=20):
    app.testing = True
    limiter.reset()  # start each trial with a clean rate-limit window
    client = app.test_client()

    query_codes = fire_query(client, burst)
    limiter.reset()
    feedback_codes = fire_feedback(client, 5)

    print(f"\n===== TRIAL {trial_no} =====")
    print(f"/api/query    x{burst:<3} -> {dict(query_codes)}")
    print(
        f"  429s on /api/query: {query_codes.get(429, 0)}  "
        f"(0 == UNPROTECTED, bug reproduced)"
    )
    print(f"/api/feedback x5   -> {dict(feedback_codes)}")
    print(
        f"  429s on /api/feedback: {feedback_codes.get(429, 0)}  "
        f"(>0 == limiter works here)"
    )

    bug_present = query_codes.get(429, 0) == 0 and feedback_codes.get(429, 0) > 0
    print(f"  RESULT: bug {'REPRODUCED' if bug_present else 'NOT reproduced'}")
    return bug_present


if __name__ == "__main__":
    results = [run_trial(i) for i in (1, 2)]
    print("\n========================================")
    print(f"Bug reproduced in {sum(results)}/{len(results)} trials.")
