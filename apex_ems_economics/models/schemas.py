"""Pydantic schemas for the Apex EMS Economics Studio entities.

These models document and validate the structure of every entity stored in
the CSV repository. The calculation engines operate on pandas DataFrames for
performance, but each DataFrame's columns correspond 1:1 to a schema here, so
the repository layer can validate rows and future database backends can reuse
the same contracts.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class OwnershipModel(str, Enum):
    OEM_INTERNAL = "OEM-owned stored internally"
    OEM_CONSIGNED = "OEM-owned consigned to EMS"
    EMS_UNTIL_CONSUMPTION = "EMS-owned until consumption"
    EMS_UNTIL_FG_TRANSFER = "EMS-owned until finished-goods transfer"
    SUPPLIER_VMI = "Supplier-owned vendor-managed inventory"
    HYBRID = "Hybrid"
    UNKNOWN = "Unknown"


class PurchaseResponsibility(str, Enum):
    OEM = "OEM procurement"
    EMS = "EMS procurement"
    DIRECT = "Component supplier direct"
    HYBRID = "Hybrid"
    UNKNOWN = "Unknown"


class TermStatus(str, Enum):
    CONFIRMED = "Confirmed"
    ESTIMATED = "Estimated"
    INFERRED = "Inferred"
    MISSING = "Missing"
    NOT_APPLICABLE = "Not applicable"


class AssumptionStatus(str, Enum):
    CONFIRMED = "Confirmed"
    ESTIMATED = "Estimated"
    BENCHMARKED = "Benchmarked"
    INFERRED = "Inferred"
    MISSING = "Missing"
    STALE = "Stale"
    UNDER_REVIEW = "Under review"


class Confidence(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class InventoryStage(str, Enum):
    RAW_MATERIAL = "Raw material"
    WIP = "Work in process"
    FINISHED_GOODS = "Finished goods"
    IN_TRANSIT = "In transit"
    SAFETY_STOCK = "Safety stock"
    STRATEGIC_BUFFER = "Strategic buffer"
    EXCESS = "Excess"
    OBSOLETE = "Obsolete"
    NCNR = "Noncancelable/nonreturnable"
    LAST_TIME_BUY = "Last-time-buy"


class Ownership(str, Enum):
    OEM = "OEM"
    EMS = "EMS"
    SUPPLIER = "Supplier"
    UNKNOWN = "Unknown"


class PhysicalLocation(str, Enum):
    OEM_SITE = "OEM site"
    EMS_SITE = "EMS site"
    IN_TRANSIT = "In transit"
    THIRD_PARTY = "Third-party warehouse"
    UNKNOWN = "Unknown"


class Severity(str, Enum):
    ERROR = "Error"
    WARNING = "Warning"
    INFO = "Information"
    DATA_QUALITY = "Data-quality issue"


class ResponsibleParty(str, Enum):
    OEM = "OEM"
    EMS = "EMS"
    SHARED = "Shared"
    UNKNOWN = "Unknown"


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------

class Supplier(BaseModel):
    supplier_id: str
    supplier_name: str
    status: str = "Approved"
    strategic_importance: str = "Medium"
    financial_health: int = Field(3, ge=1, le=5)
    capacity_rating: int = Field(3, ge=1, le=5)
    quality_rating: int = Field(3, ge=1, le=5)
    delivery_rating: int = Field(3, ge=1, le=5)
    responsiveness_rating: int = Field(3, ge=1, le=5)
    single_source_risk: str = "Medium"
    alternate_source_availability: str = "Unknown"
    transition_lead_time_weeks: float = 16
    data_transparency: str = "Unknown"
    strategic_fit: str = "Medium"
    notes: str = ""
    created_date: str = ""
    updated_date: str = ""


class Site(BaseModel):
    site_id: str
    supplier_id: str
    site_name: str
    country: str
    region: str
    currency: str = "USD"
    contract_start: str = ""
    contract_end: str = ""
    geographic_risk: str = "Medium"
    political_risk: str = "Medium"
    natural_disaster_risk: str = "Medium"
    notes: str = ""


class Product(BaseModel):
    product_id: str
    product_family: str
    product_name: str
    product_type: str = "Product"  # Product | Subassembly
    parent_product_id: str = ""
    internal_pn: str = ""
    annual_volume: float = 0
    forecast_growth_pct: float = 0
    unit_selling_price: float = 0
    current_standard_cost: float = 0
    current_supplier_id: str = ""
    alternate_supplier_ids: str = ""  # semicolon separated
    lifecycle_stage: str = "Mature"
    technical_complexity: str = "Medium"
    certifications: str = ""
    test_requirements: str = ""
    target_gross_margin_pct: float = 0
    target_service_level_pct: float = 95
    demand_variability: str = "Medium"
    product_priority: str = "Standard"
    transfer_complexity: str = "Medium"
    material_model: str = "EMS turnkey"
    notes: str = ""


class Scenario(BaseModel):
    scenario_id: str
    scenario_name: str
    description: str = ""
    is_baseline: bool = False
    demand_multiplier: float = 1.0
    one_time_cost: float = 0
    transition_cost: float = 0
    status: str = "Draft"
    created_date: str = ""
    notes: str = ""


class Allocation(BaseModel):
    scenario_id: str
    product_id: str
    supplier_id: str
    site_id: str
    allocation_pct: float = Field(ge=0, le=100)


class SupplierQuote(BaseModel):
    quote_id: str
    supplier_id: str
    product_id: str
    base_unit_price: float
    currency: str = "USD"
    price_effective_date: str = ""
    tier2_min_qty: Optional[float] = None
    tier2_unit_price: Optional[float] = None
    tier3_min_qty: Optional[float] = None
    tier3_unit_price: Optional[float] = None
    quoted_material_content: Optional[float] = None
    quoted_conversion_content: Optional[float] = None
    includes_freight: bool = False
    includes_duties: bool = False
    annual_price_reduction_pct: float = 0
    quote_source: str = ""
    status: str = TermStatus.ESTIMATED.value
    confidence: str = Confidence.MEDIUM.value
    valid_until: str = ""
    notes: str = ""


class ContractTerm(BaseModel):
    term_id: str
    supplier_id: str
    category: str
    term_name: str
    value: str = ""
    unit: str = ""
    status: str = TermStatus.MISSING.value
    source_reference: str = ""
    confidence: str = Confidence.LOW.value
    notes: str = ""


class BomItem(BaseModel):
    bom_id: str
    product_id: str
    component: str
    category: str = ""
    qty_per: float = 1
    unit_price: float = 0
    currency: str = "USD"
    price_source: str = ""
    component_supplier: str = ""
    commodity_index: str = ""
    lead_time_days: float = 0
    moq: float = 0
    order_multiple: float = 1
    scrap_pct: float = 0
    yield_pct: float = 100
    freight_pct: float = 0
    duty_pct: float = 0
    ownership_model: str = OwnershipModel.UNKNOWN.value
    physical_location: str = PhysicalLocation.UNKNOWN.value
    purchase_responsibility: str = PurchaseResponsibility.UNKNOWN.value
    price_valid_until: str = ""
    confidence: str = Confidence.MEDIUM.value
    notes: str = ""


class ConversionCost(BaseModel):
    conv_id: str
    product_id: str
    supplier_id: str
    labor_hours_per_unit: float = 0
    labor_rate: float = 0
    labor_burden_pct: float = 0
    machine_hours_per_unit: float = 0
    machine_rate: float = 0
    setup_hours: float = 0
    batch_size: float = 1
    test_hours: float = 0
    test_rate: float = 0
    inspection_cost_per_unit: float = 0
    packaging_cost_per_unit: float = 0
    indirect_labor_pct: float = 0
    factory_overhead_pct: float = 0
    program_mgmt_fee_pct: float = 0
    procurement_fee_pct: float = 0
    material_handling_fee_pct: float = 0
    supplier_margin_pct: float = 0
    utilization_pct: float = 85
    confidence: str = Confidence.MEDIUM.value
    notes: str = ""


class InventoryRecord(BaseModel):
    inv_id: str
    supplier_id: str = ""
    site_id: str = ""
    product_id: str = ""
    material_desc: str = ""
    stage: str = InventoryStage.RAW_MATERIAL.value
    ownership: str = Ownership.UNKNOWN.value
    physical_location: str = PhysicalLocation.UNKNOWN.value
    accounting_entity: str = ""
    quantity: float = 0
    unit_cost: float = 0
    days_of_supply: float = 0
    aging_days: float = 0
    excess_flag: bool = False
    obsolescence_risk: str = "Low"
    liability_status: str = ""
    notes: str = ""


class QualityMetrics(BaseModel):
    supplier_id: str
    product_id: str
    incoming_defect_ppm: float = 0
    first_pass_yield_pct: float = 100
    final_yield_pct: float = 100
    scrap_rate_pct: float = 0
    rework_rate_pct: float = 0
    rework_hours_per_unit: float = 0
    rework_labor_rate: float = 0
    retest_cost_per_unit: float = 0
    return_rate_pct: float = 0
    warranty_rate_pct: float = 0
    field_failure_rate_pct: float = 0
    downtime_hours_per_year: float = 0
    downtime_cost_per_hour: float = 0
    premium_freight_events_per_year: float = 0
    premium_freight_cost_per_event: float = 0
    recall_probability_pct: float = 0
    recall_impact_usd: float = 0
    scrap_responsibility: str = ResponsibleParty.UNKNOWN.value
    rework_responsibility: str = ResponsibleParty.UNKNOWN.value
    warranty_responsibility: str = ResponsibleParty.UNKNOWN.value
    confidence: str = Confidence.MEDIUM.value


class LogisticsLane(BaseModel):
    lane_id: str
    supplier_id: str
    site_id: str
    origin: str = ""
    destination: str = ""
    incoterms: str = ""
    freight_mode: str = ""
    freight_cost_per_unit: float = 0
    expedite_freight_cost_per_unit: float = 0
    expedite_frequency_pct: float = 0
    insurance_pct: float = 0
    brokerage_per_shipment: float = 0
    shipments_per_month: float = 0
    units_per_shipment: float = 0
    duty_rate_pct: float = 0
    tariff_rate_pct: float = 0
    packaging_cost_per_unit: float = 0
    handling_cost_per_unit: float = 0
    warehousing_cost_per_unit: float = 0
    transit_days: float = 0
    freight_paid_by: str = "OEM"
    confidence: str = Confidence.MEDIUM.value
    notes: str = ""


class ServiceLevel(BaseModel):
    supplier_id: str
    target_otd_pct: float = 95
    actual_otd_pct: float = 95
    target_lead_time_days: float = 30
    actual_lead_time_days: float = 30
    upside_flex_pct: float = 0
    downside_flex_pct: float = 0
    recovery_time_weeks: float = 4
    expedite_rate_pct: float = 0
    stockout_probability_pct: float = 0
    revenue_at_risk_pct: float = 0
    customer_penalty_annual: float = 0
    safety_stock_days: float = 0
    buffer_stock_days: float = 0
    confidence: str = Confidence.MEDIUM.value
    notes: str = ""


class CapacityRecord(BaseModel):
    site_id: str
    supplier_id: str
    available_capacity_units: float = 0
    committed_capacity_units: float = 0
    utilization_pct: float = 0
    max_utilization_pct: float = 90
    overtime_capacity_units: float = 0
    expansion_capacity_units: float = 0
    expansion_lead_time_months: float = 0
    reserved_capacity_units: float = 0
    reservation_fee_annual: float = 0
    min_economic_volume: float = 0
    max_feasible_volume: float = 0
    ramp_rate_units_per_month: float = 0
    transfer_lead_time_weeks: float = 0
    qualification_lead_time_weeks: float = 0
    constraint_notes: str = ""


class Risk(BaseModel):
    risk_id: str
    supplier_id: str = ""
    product_id: str = ""
    category: str
    description: str = ""
    probability_pct: float = Field(0, ge=0, le=100)
    financial_impact_usd: float = 0
    operational_impact: str = "Medium"
    time_to_recover_weeks: float = 0
    mitigation_status: str = "Open"
    confidence: str = Confidence.MEDIUM.value
    notes: str = ""


class Assumption(BaseModel):
    assumption_id: str
    name: str
    category: str = ""
    supplier_id: str = ""
    product_id: str = ""
    scenario_id: str = ""
    value: float = 0
    unit: str = ""
    source: str = ""
    source_date: str = ""
    owner: str = ""
    status: str = AssumptionStatus.ESTIMATED.value
    confidence: str = Confidence.MEDIUM.value
    min_value: Optional[float] = None
    most_likely_value: Optional[float] = None
    max_value: Optional[float] = None
    distribution: str = ""  # Normal | Triangular | Uniform | Lognormal | Bernoulli | Discrete
    financial_impact_rank: str = "Medium"
    last_updated: str = ""
    review_date: str = ""
    notes: str = ""


class NegotiationLever(BaseModel):
    lever_id: str
    supplier_id: str
    lever: str
    current_state: str = ""
    proposed_change: str = ""
    annual_savings: float = 0
    working_capital_impact: float = 0
    risk_impact: str = "Neutral"
    implementation_difficulty: str = "Medium"
    negotiation_difficulty: str = "Medium"
    confidence: str = Confidence.MEDIUM.value
    owner: str = ""
    next_action: str = ""
    notes: str = ""


class ScenarioOverride(BaseModel):
    override_id: str
    scenario_id: str
    entity: str  # product | quote | contract_term | inventory | risk | quality | logistics | service
    entity_id: str
    field: str
    change_type: str  # absolute | multiplier | delta
    value: float
    notes: str = ""


class DecisionRecord(BaseModel):
    decision_id: str
    decision_statement: str
    recommended_scenario_id: str = ""
    decision_owner: str = ""
    decision_date: str = ""
    status: str = "Draft"
    rationale: str = ""
    conditions: str = ""
    notes: str = ""
