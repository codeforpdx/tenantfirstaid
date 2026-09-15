"""period_value must reject date-shaped input before any arithmetic runs."""

from datetime import date
from typing import Literal

import pytest
from pydantic import ValidationError

from tenantfirstaid.langchain_tools import NoticeDeadlineInputSchema


def build(
    period_value: int,
    period_unit: Literal["hours", "days"],
    service_date: date = date(2026, 1, 1),
) -> NoticeDeadlineInputSchema:
    return NoticeDeadlineInputSchema(
        service_date=service_date,
        service_time="10:00",
        period_value=period_value,
        period_unit=period_unit,
        service_method="personal_delivery",
        is_termination_notice=True,
    )


@pytest.mark.parametrize("period_unit", ["days", "hours"])
def test_date_shaped_period_value_is_a_validation_error(period_unit):
    with pytest.raises(ValidationError):
        build(20260101, period_unit)


@pytest.mark.parametrize(
    ("period_value", "period_unit"), [(365, "days"), (72, "hours")]
)
def test_longest_real_ors_90_periods_are_still_accepted(period_value, period_unit):
    assert build(period_value, period_unit).period_value == period_value


@pytest.mark.parametrize("period_unit", ["days", "hours"])
def test_far_future_service_date_is_a_validation_error(period_unit):
    with pytest.raises(ValidationError):
        build(30, period_unit, service_date=date(9999, 12, 31))


@pytest.mark.parametrize("period_unit", ["days", "hours"])
def test_far_past_service_date_is_a_validation_error(period_unit):
    with pytest.raises(ValidationError):
        build(30, period_unit, service_date=date(1900, 1, 1))


@pytest.mark.parametrize("service_date", [date(1973, 1, 1), date(2100, 1, 1)])
def test_service_date_bounds_are_inclusive(service_date):
    assert build(30, "days", service_date=service_date).service_date == service_date
