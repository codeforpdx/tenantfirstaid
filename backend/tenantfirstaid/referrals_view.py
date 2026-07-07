"""Flask view serving the validated referral catalog."""

from flask import Response, jsonify

from .referrals import REFERRALS


def get_referrals() -> Response:
    return jsonify([r.model_dump(mode="json") for r in REFERRALS])
