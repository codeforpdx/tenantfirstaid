"""Tests with LangSmith evaluators."""

from textwrap import dedent

import pytest
from langsmith import testing as t

from tenantfirstaid.location import OregonCity, UsaState

# set env var 'LANGSMITH_TRACING=true' in order to run these tests

@pytest.mark.skip("work-in-progress")
@pytest.mark.require_repo_secrets
@pytest.mark.langsmith(test_suite_name="general_evaluations")
def test_month_to_month() -> None:
    user_query: str = dedent(
        """I have a month to month tenancy and am trying to give 30 days
           notice but my landlord is saying that isn't enough warning"""
    )
    state = UsaState.from_maybe_str("or")
    city = OregonCity.from_maybe_str(None)
    t.log_inputs({"user_query": user_query, "state": state, "city": city})

    reference_output: str = dedent(
        """In Oregon a month-to-month renter may end the tenancy 'by
           giving the landlord notice in writing not less than 30 days
           prior to the date designated in the notice for the termination
           of the tenancy.' (ORS 90.427 (3)(a) or, for MH/floating-home
           spaces, ORS 90.620 (1).) Tips to avoid push-back:
           * Put the notice in writing and date it.
           * Specify your last day of possession.
           * Serve it by personal delivery or by first-class mail (add 
             three days if mailed) (ORS 90.155, 90.160).
           If you do those things, 30 days is all the statute requires;
           the landlord cannot insist on more."""
    )
    t.log_reference_outputs({"reference_outputs": reference_output})
