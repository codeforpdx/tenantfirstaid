import textwrap
import pathlib
import json

# Build the two eval samples as Python dicts
samples = [
    {
        "messages": [
            {
                "role": "user",
                "content": "my landlord reported my missed rent checks to a consumer credit reporting agency - is this allowed?",
            },
            {
                "role": "assistant",
                "content": "Quick question first: Were the missed payments that your landlord reported from the period April 1, 2020 through June 30, 2021?",
            },
            {"role": "user", "content": "yes"},
        ],
        "ideal": textwrap.dedent("""\
            No. Under ORS 90.100 Note, Sec. 7, chapter 39, Oregon Laws 2021, “A landlord may not report to any consumer credit reporting agency a tenant’s non-payment of rent, charges or fees that accrued on or after April 1 2020 and before July 1 2021.”

            What to do next (keep a copy of everything you send):
            1. Send the landlord a dated, written demand that they immediately withdraw the report and give you written confirmation. Cite the statute above.
            2. Dispute the item with the credit bureau(s) in writing and attach a copy of the statute and your letter to the landlord.
            3. If the item isn’t deleted within 30 days, you can sue the landlord for any actual damages plus your attorney fees (ORS 90.255). Small-claims court is an option.

            If you need free legal help, call the Oregon Law Center: 1-800-673-0506.
            """),
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "i missed rent and live in a dorm. is my university allowed to evict me without notice?",
            }
        ],
        "ideal": textwrap.dedent("""\
            Campus dorms are not covered by Oregon’s Residential Landlord-Tenant Act (ORS 90.110 (1)), so the Act’s normal eviction-notice rules don’t apply. Instead, the university must follow the notice or disciplinary process laid out in your student housing contract and any campus policies.

            Have you checked your housing agreement to see what notice (if any) it requires before removing a student for missed rent?
            """),
    },
]

# Write to JSONL
path = pathlib.Path("tenant_tests.jsonl")
with path.open("w", encoding="utf-8") as f:
    for sample in samples:
        f.write(json.dumps(sample, ensure_ascii=False))
        f.write("\n")

path.as_posix()
