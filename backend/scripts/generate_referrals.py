"""Generate the validated referral catalog as a TypeScript module.

Usage: npm run generate-referrals (from frontend/).
"""

import json

from tenantfirstaid.referrals import REFERRALS


def generate_referrals_module() -> str:
    """Return the validated referral catalog as a typed TypeScript module."""
    referrals_json = json.dumps(
        [referral.model_dump(mode="json") for referral in REFERRALS], indent=2
    )
    return (
        "// This file is auto-generated. Do not edit it manually.\n"
        'import type { ReferralList } from "../types/models";\n\n'
        f"const referrals: ReferralList = {referrals_json};\n\n"
        "export default referrals;\n"
    )


if __name__ == "__main__":
    print(generate_referrals_module(), end="")
