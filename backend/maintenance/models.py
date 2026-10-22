from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AssessmentInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    symptoms: str = Field(min_length=5, max_length=4000)
    observed_part_code: str | None = Field(default=None, max_length=80)
    quantity: str | None = None
    company_id: str | None = Field(default=None, max_length=140)
    warehouse_id: str | None = Field(default=None, max_length=140)
    machine_id: str | None = Field(default=None, max_length=140)
    site_id: str | None = Field(default=None, max_length=140)
    production_line_id: str | None = Field(default=None, max_length=140)
    station_id: str | None = Field(default=None, max_length=140)

    @field_validator('quantity')
    @classmethod
    def quantity_is_user_input(cls, value):
        if value is None:
            return None
        try:
            number = Decimal(value)
            if not number.is_finite() or number <= 0 or number > Decimal('999999.999') or number.as_tuple().exponent < -3:
                raise ValueError('Quantity must be positive with at most three decimal places')
        except InvalidOperation:
            raise ValueError('Invalid quantity') from None
        return value


class Hypothesis(BaseModel):
    model_config = ConfigDict(extra='forbid')
    cause: str = Field(min_length=1, max_length=500)
    verification: str = Field(min_length=1, max_length=700)
    evidence_ids: list[str] = Field(min_length=1, max_length=8)


class RecommendedAction(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: str = Field(min_length=1, max_length=700)
    evidence_ids: list[str] = Field(min_length=1, max_length=8)


class AgentAssessment(BaseModel):
    model_config = ConfigDict(extra='forbid')
    assessment_summary: str = Field(min_length=1, max_length=1500)
    hypotheses: list[Hypothesis] = Field(min_length=1, max_length=5)
    recommended_actions: list[RecommendedAction] = Field(min_length=1, max_length=6)
    requested_part_sku: Literal['PSF20CR'] | None
    alternative_part_sku: Literal['PSF20/LP99'] | None
    missing_information: list[str] = Field(max_length=12)
    follow_up: list[str] = Field(min_length=1, max_length=6)
    evidence_ids: list[str] = Field(min_length=1, max_length=12)

    @field_validator('missing_information', 'follow_up')
    @classmethod
    def bounded_text(cls, values):
        if any(not value.strip() or len(value) > 700 for value in values):
            raise ValueError('Empty or oversized list entry')
        return values
