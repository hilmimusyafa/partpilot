from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, AfterValidator, model_validator
from backend.wo.models import ProductionEconomics, RestoreSchedule, EconomicCost, DonorCostDeclaration

def decimal_wire(v: str) -> str:
    import re
    if not re.fullmatch(r'\d{1,18}(?:\.\d{1,6})?',v):
        raise ValueError('expected nonnegative decimal string')
    return v
Amount=Annotated[str,AfterValidator(decimal_wire)]

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid')

class Identity(Strict):
    brand: str=Field(min_length=1,max_length=30)
    base: str=Field(pattern=r'^6\d{3}$')
    suffix: Literal['LLU','LLB','LLF','LLH','ZZ','2RS','DDU','OPEN']

class Quote(Strict):
    quote_id: str
    revision: int=Field(ge=1)
    identity: Identity
    qty_available: Amount
    quantity_unit: Literal['Nos']='Nos'
    unit_price: Amount | None
    currency: Literal['IDR']='IDR'
    tax_amount: Amount | None
    shipping_amount: Amount | None
    processing_hours: Amount | None
    delivered_eta: datetime | None
    destination_warehouse_id: str
    valid_until: datetime
    source: str='synthetic:vendor-simulator'
    assumption_version: str='bearing-mvp-v1'

    @model_validator(mode='after')
    def aware_dates(self):
        if self.valid_until.utcoffset() is None or (self.delivered_eta and self.delivered_eta.utcoffset() is None):
            raise ValueError('timezone-aware timestamps required')
        return self

class VendorResponse(Strict):
    event_id: str
    run_id: str
    vendor_id: str
    outcome: Literal['quoted','revised_quote','negotiation_refused','no_response','no_stock','malformed']
    quote: Quote | None=None

class StartInput(Strict):
    session_id: str
    expected_version: int=Field(ge=1)

class EmptyInput(Strict):
    pass

class OptionAssumptions(Strict):
    source_id: str
    schedule: RestoreSchedule
    incremental_disruption_costs: list[EconomicCost]=Field(default_factory=list)
    donor_cost_status: DonorCostDeclaration
    donor_costs: list[EconomicCost]=Field(default_factory=list)
    costs_nonduplicated: Literal[True]

class CompareInput(Strict):
    expected_version: int=Field(ge=1)
    production: ProductionEconomics
    options: list[OptionAssumptions]=Field(max_length=10)

    @model_validator(mode='after')
    def unique_sources(self):
        if len({o.source_id for o in self.options})!=len(self.options):raise ValueError('duplicate source_id')
        return self

class DecisionInput(Strict):
    expected_version: int=Field(ge=1)
    option_id: str
    acknowledgment: Literal['demo_only']
