"""Pydantic models and schemas for PartPilot Backend Bundle v3."""

import re
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from decimal import Decimal


class WorkOrderState(str, Enum):
    draft = "draft"
    queued = "queued"
    processing = "processing"
    awaiting_clarification = "awaiting_clarification"
    identified = "identified"
    no_match = "no_match"
    knowledge_unavailable = "knowledge_unavailable"
    needs_review = "needs_review"
    failed = "failed"


class DraftCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: str
    machine_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[str] = "1"
    urgency: Optional[str] = "Medium"
    notes: Optional[str] = None
    input_kind: Optional[str] = "text"
    site_id: Optional[str] = None
    production_line_id: Optional[str] = None
    station_id: Optional[str] = None

    @field_validator("quantity", mode="before")
    @classmethod
    def validate_quantity(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("Quantity must be a string")
        if not re.match(r"^\d{1,6}(\.\d{1,3})?$", v):
            raise ValueError("Quantity must match pattern ^\\d{1,6}(\\.\\d{1,3})?$")
        try:
            val = float(v)
            if val < 0 or val > 999999.999:
                raise ValueError("Quantity must be nonnegative and <= 999999.999")
        except ValueError:
            raise
        return v

    @field_validator("urgency")
    @classmethod
    def validate_urgency(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("Low", "Medium", "High", "Critical"):
            raise ValueError("Urgency must be one of Low, Medium, High, Critical")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 8000:
            raise ValueError("Description length cannot exceed 8000 code points")
        return v

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 2000:
            raise ValueError("Notes length cannot exceed 2000 code points")
        return v

    @field_validator("input_kind")
    @classmethod
    def validate_input_kind(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("text", "confirmed_transcript"):
            raise ValueError("input_kind must be text or confirmed_transcript")
        return v


class DraftUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int
    machine_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[str] = "1"
    urgency: Optional[str] = "Medium"
    notes: Optional[str] = None
    input_kind: Optional[str] = "text"
    site_id: Optional[str] = None
    production_line_id: Optional[str] = None
    station_id: Optional[str] = None

    @field_validator("quantity", mode="before")
    @classmethod
    def validate_quantity(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("Quantity must be a string")
        if not re.match(r"^\d{1,6}(\.\d{1,3})?$", v):
            raise ValueError("Quantity must match pattern ^\\d{1,6}(\\.\\d{1,3})?$")
        try:
            val = float(v)
            if val < 0 or val > 999999.999:
                raise ValueError("Quantity must be nonnegative and <= 999999.999")
        except ValueError:
            raise
        return v

    @field_validator("urgency")
    @classmethod
    def validate_urgency(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("Low", "Medium", "High", "Critical"):
            raise ValueError("Urgency must be one of Low, Medium, High, Critical")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 8000:
            raise ValueError("Description length cannot exceed 8000 code points")
        return v

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 2000:
            raise ValueError("Notes length cannot exceed 2000 code points")
        return v

    @field_validator("input_kind")
    @classmethod
    def validate_input_kind(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("text", "confirmed_transcript"):
            raise ValueError("input_kind must be text or confirmed_transcript")
        return v


# Alias for compatibility with test assertions
WorkOrderCreate = DraftCreate


class VersionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_id: str
    answer: str

    @field_validator("answer")
    @classmethod
    def validate_answer(cls, v: str) -> str:
        if len(v) > 2000:
            raise ValueError("Answer length cannot exceed 2000 code points")
        return v


class AnswersInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int
    answers: List[Answer]


class Evidence(BaseModel):
    source_field: str
    raw_substring: str
    normalized_value: Optional[str] = None
    source_ref: Optional[str] = None


class Fact(BaseModel):
    key: str
    value: str
    source: str
    evidence: List[Evidence] = []


class Question(BaseModel):
    id: str
    key: str
    prompt: str
    options: Optional[List[str]] = None


class Candidate(BaseModel):
    item_code: str
    item_name: str
    brand: Optional[str] = None
    description: Optional[str] = None
    actual_qty: Optional[str] = None
    reserved_qty: Optional[str] = None
    available_qty: Optional[str] = None


class SafeError(BaseModel):
    code: str
    message: str
    retriable: bool = False
    details: Optional[Dict[str, Any]] = None


class ErrorEnvelope(BaseModel):
    error: SafeError
    request_id: str


class KnowledgeRef(BaseModel):
    path: str
    sha256: str
    source_status: str
    snapshot_version: str
    content_snapshot: Optional[str] = None


class ProductionAncestrySnapshot(BaseModel):
    company_id: str
    site_id: Optional[str] = None
    production_line_id: Optional[str] = None
    station_id: Optional[str] = None
    machine_id: Optional[str] = None


class ProductionAncestrySource(BaseModel):
    source: Optional[str] = None
    resolved_at: Optional[str] = None
    snapshot: Optional[ProductionAncestrySnapshot] = None


class Session(BaseModel):
    id: str
    session_id: Optional[str] = None
    api_version: str = "wo-text-v2"
    company_id: str
    site_id: Optional[str] = None
    production_line_id: Optional[str] = None
    station_id: Optional[str] = None
    machine_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    state: str
    version: int
    input_revision: int = 1
    clarification_round: int = 0
    explicit_retries: int = 0
    job_id: Optional[str] = None
    urgency: Optional[str] = "Medium"
    quantity: Optional[str] = "1"
    description: Optional[str] = None
    notes: Optional[str] = None
    input_kind: Optional[str] = "text"
    input: Optional[Dict[str, Any]] = None
    context_source: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    facts: List[Fact] = []
    conflicts: List[Dict[str, Any]] = []
    questions: List[Question] = []
    candidates: List[Candidate] = []
    truncated: bool = False
    identified_item_code: Optional[str] = None
    knowledge_refs: List[KnowledgeRef] = []
    error: Optional[SafeError] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if not self.session_id:
            self.session_id = self.id
        if self.result:
            if "facts" in self.result and not self.facts:
                self.facts = [Fact(**f) if isinstance(f, dict) else f for f in self.result.get("facts", [])]
            if "conflicts" in self.result and not self.conflicts:
                self.conflicts = self.result.get("conflicts", [])
            if "questions" in self.result and not self.questions:
                self.questions = [Question(**q) if isinstance(q, dict) else q for q in self.result.get("questions", [])]
            if "candidates" in self.result and not self.candidates:
                self.candidates = [Candidate(**c) if isinstance(c, dict) else c for c in self.result.get("candidates", [])]
            if "truncated" in self.result:
                self.truncated = bool(self.result.get("truncated", False))
            if "identified_candidate" in self.result and self.result["identified_candidate"]:
                cand = self.result["identified_candidate"]
                if isinstance(cand, dict) and "item_code" in cand:
                    self.identified_item_code = cand["item_code"]
            if "knowledge_refs" in self.result and not self.knowledge_refs:
                self.knowledge_refs = [KnowledgeRef(**r) if isinstance(r, dict) else r for r in self.result.get("knowledge_refs", [])]
            if "error" in self.result and not self.error:
                err = self.result.get("error")
                if isinstance(err, dict):
                    self.error = SafeError(**err)


class Company(BaseModel):
    id: str
    name: str


class CompanyPage(BaseModel):
    items: List[Company]
    next_cursor: Optional[str] = None


class Site(BaseModel):
    id: str
    name: str
    company_id: str


class SitePage(BaseModel):
    items: List[Site]
    next_cursor: Optional[str] = None


class ProductionLine(BaseModel):
    id: str
    name: str
    company_id: str
    site_id: str
    production_scope: str = "AC"


class ProductionLinePage(BaseModel):
    items: List[ProductionLine]
    next_cursor: Optional[str] = None


class Station(BaseModel):
    id: str
    name: str
    company_id: str
    site_id: str
    production_line_id: str


class StationPage(BaseModel):
    items: List[Station]
    next_cursor: Optional[str] = None


class Machine(BaseModel):
    id: str
    name: str
    company_id: str
    site_id: str
    production_line_id: str
    station_id: str
    suggested_warehouse_id: Optional[str] = None
    mapping_source: Optional[str] = None
    ancestry_source: str = "pp.machine_context"


class MachinePage(BaseModel):
    items: List[Machine]
    next_cursor: Optional[str] = None


class Warehouse(BaseModel):
    id: str
    name: str
    company_id: str


class WarehousePage(BaseModel):
    items: List[Warehouse]
    next_cursor: Optional[str] = None


class AvailabilityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    expected_version: int


class AvailabilityScope(BaseModel):
    warehouse_id: str
    status: str
    item_code: Optional[str] = None
    actual_qty: Optional[str] = None
    reserved_qty: Optional[str] = None
    available_qty: Optional[str] = None
    shortage_qty: Optional[str] = None
    quantity_unit: Optional[str] = None
    evidence: List[Dict[str, Any]] = []
    knowledge_refs: List[Dict[str, Any]] = []
    scoped_reason: Optional[str] = None


class AvailabilityResult(BaseModel):
    api_version: str = "backend-bundle-v3"
    session_id: str
    session_version: int
    snapshot_id: str
    as_of: str
    company_id: str
    category: str
    identity_evidence: List[Dict[str, Any]] = []
    requested_qty: str
    quantity_unit: str
    status: str
    origin: AvailabilityScope
    alternatives: List[AvailabilityScope] = []
    complete: bool
    truncated: bool
    reservation: bool = False


DECIMAL_STRING_PATTERN = re.compile(r"^-?\d{1,18}(\.\d{1,6})?$")


class EconomicDatum(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: Optional[str] = None
    unit: str
    source: str
    assumption_version: str

    @field_validator("value", mode="before")
    @classmethod
    def validate_decimal_string(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError(f"Numeric wire value must be a string, got {type(v).__name__}")
        if not DECIMAL_STRING_PATTERN.match(v):
            raise ValueError(f"Value '{v}' does not match wire decimal string pattern (max 18 digits integer, 6 fractional)")
        return v


class BundleContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    site_id: str
    production_line_id: str
    station_id: str
    machine_id: str


class ProductionEconomics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    output_unit: str
    currency: str
    currency_scale: int
    normal_output_per_hour: EconomicDatum
    disrupted_output_per_hour: EconomicDatum
    recoverable_fraction: EconomicDatum
    net_selling_price_per_unit: EconomicDatum
    avoidable_variable_cost_per_unit: EconomicDatum

    @model_validator(mode='after')
    def validate_economic_units(self):
        if self.currency_scale < 0 or self.currency_scale > 6:
            raise ValueError('currency_scale must be between zero and six')
        units={'normal_output_per_hour':f'{self.output_unit}/h',
               'disrupted_output_per_hour':f'{self.output_unit}/h',
               'recoverable_fraction':'fraction',
               'net_selling_price_per_unit':f'{self.currency}/{self.output_unit}',
               'avoidable_variable_cost_per_unit':f'{self.currency}/{self.output_unit}'}
        for key,unit in units.items():
            datum=getattr(self,key)
            if datum.unit!=unit:raise ValueError(f'incompatible unit for {key}')
            if datum.value is not None and Decimal(datum.value)<0:raise ValueError(f'negative {key}')
        if self.recoverable_fraction.value is not None and Decimal(self.recoverable_fraction.value)>1:
            raise ValueError('recoverable_fraction must be within zero and one')
        a,b=self.normal_output_per_hour.value,self.disrupted_output_per_hour.value
        if a is not None and b is not None and Decimal(b)>Decimal(a):raise ValueError('disrupted rate exceeds normal rate')
        return self


class RestoreStage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    kind: str
    start: str
    end: str
    depends_on: List[str] = []
    source: str
    assumption_version: str


class OperatingWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start: str
    end: str


class RestoreSchedule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    future_from: str
    horizon_end: str
    calendar_source: str
    parallel_assumption_version: str
    stages: List[RestoreStage]
    scheduled_impacted_windows: Optional[List[OperatingWindow]] = None


class EconomicCost(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cost_id: str
    cost_type: str
    amount: EconomicDatum
    evidence_ref: str
    description: str


class DonorCostDeclaration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    source: str
    assumption_version: str
    reason: Optional[str] = None


class EconomicOption(BaseModel):
    model_config = ConfigDict(extra="forbid")
    option_id: str
    availability_snapshot_id: Optional[str] = None
    costs_nonduplicated: bool
    donor_cost_status: DonorCostDeclaration
    schedule: RestoreSchedule
    sourcing_costs: List[EconomicCost] = []
    incremental_disruption_costs: List[EconomicCost] = []


class ScenarioInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    production: ProductionEconomics
    options: List[EconomicOption]


class DisruptionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    company_id: str
    context: BundleContext
    production: ProductionEconomics
    options: List[EconomicOption]
    scenarios: Optional[Dict[str, ScenarioInput]] = None


class EconomicOptionResult(BaseModel):
    option_id: str
    status: str
    missing_inputs: List[str] = []
    exclusions: List[str] = []
    flags: List[str] = []
    contribution_margin: Optional[str] = None
    contribution_margin_unrounded: Optional[str] = None
    effective_scheduled_impacted_hours: Optional[str] = None
    lost_output: Optional[str] = None
    unrecoverable_lost_contribution: Optional[str] = None
    unrecoverable_lost_contribution_unrounded: Optional[str] = None
    incremental_disruption_total: Optional[str] = None
    incremental_disruption_total_unrounded: Optional[str] = None
    sourcing_total: Optional[str] = None
    sourcing_total_unrounded: Optional[str] = None
    estimated_economic_disruption: Optional[str] = None
    estimated_economic_disruption_unrounded: Optional[str] = None
    future_relevant_option_total: Optional[str] = None
    future_relevant_option_total_unrounded: Optional[str] = None
    restore_at: Optional[str] = None
    elapsed_restore_hours: Optional[str] = None


class ScenarioResult(BaseModel):
    scenario_key: str
    options: List[EconomicOptionResult]


class DisruptionResult(BaseModel):
    api_version: str = "backend-bundle-v3"
    company_id: str
    context: BundleContext
    base_options: List[EconomicOptionResult]
    scenarios: Optional[Dict[str, List[EconomicOptionResult]]] = None
