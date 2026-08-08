# Apex EMS Economics Studio

A standalone module of the **Apex Operations Finance Studio** — an executive decision
platform for Operations Finance organizations supporting complex global manufacturing.

The EMS Economics Studio turns EMS (electronics manufacturing services) contracts, supplier
quotes, operational assumptions, cost structures, inventory terms, quality performance, and
service-level commitments into a **deterministic, auditable economic decision model**.

## The business problem

Outsourced manufacturing decisions are usually made on quoted unit price. But a supplier
quote excludes freight, duties, quality fallout, working capital, service performance,
risk, and switching costs — and contract terms (inventory ownership, payment terms,
liability windows) move millions of dollars of cash without ever appearing in a piece-price
comparison. Finance typically reports these costs after the fact.

This studio inverts that: **Finance builds a transparent decision system that connects
contracts, operations, supply chain, quality, inventory, risk, and economics so leadership
can make better decisions before outcomes are locked in.**

Questions it answers:

- What is the *true total cost* of producing each product at each EMS supplier?
- How does the quoted price compare to an internal should-cost?
- Which supplier is economically preferable after quality, logistics, working capital,
  service, risk, and switching costs?
- What is the financial impact of consignment vs EMS-owned inventory, payment terms,
  NCNR windows, and minimum commitments?
- What happens under volume, mix, tariff, freight, yield, or FX changes?
- Which assumptions are known vs estimated vs missing — and where should the team focus next?

## Intended users

| Function | Role in the model |
|---|---|
| **Operations Finance** | Owns the framework, economic logic, scenarios, governance, COGS/GM/WC linkage |
| **Procurement** | Quotes, contract terms, price data, negotiation levers |
| **Supply Chain** | Lead times, inventory policy, variability, liability windows, logistics |
| **Manufacturing/Operations** | Capacity, throughput, labor, utilization, transfer readiness |
| **Quality** | Yields, defect/rework/scrap rates, warranty exposure |
| **Engineering** | BOM structure, routing, test requirements, alternates, transfer requirements |
| **Executives** | Scenario comparison, recommendations, risks, evidence package |

## Core economic concepts

1. **Quote vs economic cost.** The supplier quote contains material + conversion (and
   sometimes freight/duties). The model adds only *incremental* OEM costs — never
   double counting:

   ```
   Total economic cost =
       Quoted purchase cost                (tier-adjusted price × volume)
     + Consigned material cost             (OEM-purchased material excluded from the quote)
     + Logistics                           (freight, insurance, brokerage, packaging, handling, warehousing)
     + Duties & tariffs
     + OEM-borne cost of poor quality      (scrap, rework, returns, warranty, downtime, expected recall)
     + Working-capital cost                (carrying cost on OEM-owned inventory, advances, payment-terms effect)
     + Service cost                        (safety/buffer stock, expedites, expected stockouts, penalties)
     + Expected risk cost                  (Σ probability × impact — decision measure)
     + One-time & transition costs
   Economic cost per unit = total ÷ good units      (good units = volume × final yield)
   ```

2. **Ownership vs location.** Inventory ownership (OEM / EMS / supplier) and physical
   location (OEM site / EMS site / in transit) are modeled as separate dimensions —
   OEM-owned consigned material at an EMS site is on the OEM balance sheet; EMS-owned
   material backing OEM demand is off-balance-sheet supply exposure.

3. **Cost vs cash.** Payment terms, deposits, and ownership conversions change cash without
   changing COGS. Scenario comparison reports COGS impact, gross-margin impact, and
   cash-flow impact separately.

4. **Booked vs expected cost.** Expected risk, recall, and stockout costs are
   probability-weighted *decision-analysis measures*, labeled as such, never booked.

5. **Known vs estimated.** Every quote, BOM line, contract term, and assumption carries a
   status (Confirmed / Estimated / Benchmarked / Inferred / Missing / Stale) and a
   confidence level; a composite data-quality score qualifies every recommendation.

## Installation

```bash
cd apex_ems_economics
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Running

```bash
streamlit run app.py
```

Run tests:

```bash
pytest
```

## Project structure

```
apex_ems_economics/
├── app.py                        # Home page: model health + data confidence
├── pages/                        # 19 Streamlit pages (UI only, no business logic)
│   ├── 01_Executive_Overview.py
│   ├── 04_Tester_Platform_Rollup.py
│   ├── ...
│   └── 19_Executive_Evidence_Package.py
├── core/                         # Deterministic engines (UI-independent, importable)
│   ├── economics_engine.py       #   quote → true economic cost; bridges; scenario deltas
│   ├── platform_engine.py        #   board economics → cost per system shipped (QPA ship-sets)
│   ├── scenario_engine.py        #   baseline + overrides (absolute/multiplier/delta)
│   ├── inventory_engine.py       #   ownership×location, carrying cost, WC cost
│   ├── quality_engine.py         #   COPQ with contractual responsibility shares
│   ├── logistics_engine.py       #   landed cost, duties, tariffs
│   ├── service_engine.py         #   safety stock, expedites, expected stockouts
│   ├── risk_engine.py            #   expected risk cost + allocation
│   ├── capacity_engine.py        #   headroom, feasibility, volume shifts
│   ├── should_cost_engine.py     #   3-level should-cost, variance interpretation
│   ├── scoring_engine.py         #   weighted supplier score (weights sum to 100%)
│   ├── recommendation_engine.py  #   rule-based recommendations (auditable)
│   ├── validation_engine.py      #   errors/warnings/DQ issues + data-quality score
│   ├── monte_carlo_engine.py     #   optional simulation over the deterministic engine
│   ├── integration_outputs.py    #   standardized frames for future Apex modules
│   └── config.py                 #   global settings access
├── models/schemas.py             # Pydantic schemas for every entity
├── repositories/csv_repository.py# Storage layer (CSV now, DB-swappable later)
├── services/
│   ├── export_service.py         #   CSV + multi-tab Excel exports
│   ├── contract_parser_service.py#   contract text → draft terms (no API key needed)
│   └── ai_insight_service.py     #   anomalies, narratives, assumption challenge
├── components/                   # Streamlit widgets, charts, formatting
├── data/sample/                  # Fictional sample dataset (23 CSV entities)
├── data/templates/               # Blank headers for starting a fresh model
└── tests/                        # 49 tests incl. end-to-end, interaction, and smoke tests
```

**Architecture rules:** business logic lives only in `core/`; the engines take a plain
`dict[str, DataFrame]` and are callable without Streamlit (see `tests/`); the repository
is the only layer touching storage.

## Sample data and scenarios

Fictional ATE (automated test equipment) manufacturer **Novatron Test Systems** with
three fictional EMS suppliers (no real supplier or customer data), scaled to the size of
a major ATE player:

| Figure | Sample dataset |
|---|---|
| Modeled portfolio revenue | **$4.0B** |
| EMS quoted spend (EMS scope) | **$825M** |
| OEM-consigned strategic silicon | **$275M** |
| **Total modeled spend** | **$1.10B** — of which ~75% ($830M) is material, ~25% conversion |
| Purchased system material (chassis, backplane, harnesses, cooling, controller, licenses) | **$261M** |
| In-house assembly & system test (labeled labor+OH assumption) | $140M |
| **Full system COGS** | **$1.54B** on $4.0B revenue → **61% gross margin** |
| True economic cost (EMS decision scope) | $1.27B |
| OEM-owned inventory / total supply exposure | $176M / $286M |

### What the company ships vs what the EMS builds

Novatron **ships test systems**; the EMS partners **build the boards** that go into them.
Final assembly, system integration, calibration, correlation, and system test are done
**in-house** and are outside the EMS scope (they appear only as a labeled per-system
assumption so margin closes). Board demand bridges the two through QPA — quantity per
assembly:

```
annual board demand = systems shipped × QPA
ship-set cost       = Σ over boards of (QPA × board cost per good unit)
```

| Platform | Systems shipped/yr | Ship-set (QPA) | ASP | Quoted ship-set | True EMS content | Hidden cost/system | GM% |
|---|---|---|---|---|---|---|---|
| Nova-D9000 digital tester | 900 | 30 channel cards + 60 power supplies | $3.02M | $580K | **$927K** | **+$347K** | 59% |
| Nova-RF7000 mmWave tester | 850 | 8 mmWave modules | $944K | $101K | **$248K** | **+$147K** | 64% |
| Device interface products | 18,000 boards | 1 per device program | $26.5K | $7.8K | $9.3K | +$1.5K | 55% |

The **hidden cost per system** — what the quoted ship-set misses once logistics, duties,
quality, working capital, service, and expected risk are counted — is the number this
studio exists to expose: $347K on every digital tester shipped.

Boards are ATE-class: a 256-channel pin-electronics channel card (~$18.7K all-in), a
mmWave source & measure module (~$31K), a device power supply, a 36-layer device
interface board, plus two subassemblies. Consigned strategic ASIC/mmWave silicon and
golden-tester correlation time dominate the economics. Products represent **family
aggregates**, not single part numbers. Subassemblies are modeled as their own supplier
flows but excluded from ship-sets, since their cost already sits inside the parent
board's BOM.

| Supplier | Profile |
|---|---|
| **Atlas Manufacturing Services** (Guadalajara, Austin) | Mid quote, best quality/service, near-shore, partial open-book |
| **Meridian Electronics** (Penang) | Lowest quotes, bundled pricing, weak OTD/yield, aggressive liability terms, elevated risk |
| **Pacific Integrated Systems** (Kaohsiung) | Best working-capital terms (net 75, EMS-owned material), strong high-mix, disaster exposure |

Quote convention: **supplier quotes cover the EMS scope only** — OEM-consigned material
is excluded from the quote and added separately by the engine (never double counted).

Four scenarios:

1. **Current State** (baseline)
2. **Shift 25% of P-100 to Meridian** — the $950/board quote saving is destroyed by
   tariffs, quality, working capital, service, risk, *and* the loss of Atlas tier-2
   pricing when volume splits (≈ **+$31.7M/yr**, ≈ −$45.8M cash in year 1)
3. **Renegotiate Atlas inventory & payment terms** — ≈ **−$4.9M/yr** cost and ≈ **+$76M
   cash freed** for a 0.6% price concession
4. **Dual-Source the mmWave module** — a running-cost premium plus $11M one-time buys a
   ≈ **−$8.0M/yr expected-risk reduction** on the single-sourced RF tester line
5. **EMS Box Build** — Atlas takes over system integration and system-material procurement:
   ≈ **−$1.6M/yr** COGS against **$4.3M one-time** (≈2.7-year payback) and *higher* supplier
   dependency risk. Close to a wash on P&L — which is exactly why most ATE makers keep final
   integration in-house, and why the model is worth having before the debate starts.

On the flagship channel card, Meridian quotes $950/board below Atlas yet lands
**~$2,970/board worse** in true economic cost — the studio's central lesson.

## Assumption treatment

- Missing data never stops the model: missing quotes fall back to standard cost (flagged),
  missing lanes/quality/service contribute zero with a `*_missing` flag.
- Assumptions carry min / most-likely / max ranges that feed the Monte Carlo drivers.
- The assumption-challenge view ranks validation priorities by low confidence × high impact.

## Monte Carlo (optional)

Enabled from the Scenario Comparison page. Each iteration perturbs a copy of the inputs
(demand, material prices, freight, expedite frequency, yield, tariff shock) and re-runs the
full deterministic engine — no response-surface shortcuts. Fixed seed = reproducible.
Outputs (mean/median/P10/P50/P90, P(A cheaper than B), P(savings > target), driver
sensitivities) are always labeled as simulated.

## AI architecture

The deterministic engine never depends on AI. `services/ai_insight_service.py` and
`services/contract_parser_service.py` provide deterministic template/regex fallbacks that
run with **no API key**; the same interfaces can later be backed by an LLM. AI output is
advisory (draft terms, anomaly flags, narratives, questions) and always requires human
validation — extracted contract terms are created as *Inferred / Low confidence*.

## Exports

- CSV downloads on every major table (comparison, cost detail, tradeoffs, MC summary).
- Multi-tab Excel **Executive Evidence Package**: Executive Summary, Scenario Comparison,
  Supplier Economics, Product Economics, Cost Detail, Inventory, Quality, Contract Terms,
  Risks, Assumptions, Actions.
- Future-integration output tables (product cost, inventory, margin, supply) for the
  Executive SIOP Decision Engine, Manufacturing Economics Studio, Margin Intelligence,
  Working Capital Optimizer, and Strategic Network Optimizer.

## Testing

`pytest` runs 49 tests: unit tests for material/conversion/tier-pricing/quality/working
capital/risk/should-cost math, double-counting guards, yield-adjusted good units, platform
ship-set and box-build reconciliation, scenario overrides (including inventory-ownership
conversion), Monte Carlo reproducibility, an end-to-end test asserting the sample-data
economics story, interaction tests proving key controls actually drive the numbers, and a
smoke test that renders all 20 Streamlit pages headlessly. The suite is run against both
pandas 2.x and 3.x, since Streamlit Cloud resolves the newer major version.

## Known limitations (v1)

- Single currency (USD): FX terms are registered but conversion is not applied; FX enters
  only as a Monte Carlo driver.
- Monthly granularity is approximated (annual ÷ 12); no seasonality.
- Working capital for shifted allocations uses baseline per-supplier inventory-days
  intensity; a supplier never used before falls back to zero OEM-days plus transit —
  refine with explicit pipeline modeling when data exists.
- Expected-value risk model is single-period, independent events; no correlation between
  risks.
- Subassembly costs are not rolled up into parent-product economics (each is modeled as
  its own flow); consigned-subassembly linkage (SA-210 → P-200) is represented through
  BOM consignment, and subassemblies are excluded from platform ship-sets to prevent
  double counting.
- In-house final assembly, integration, and system test labor/overhead is a single labeled
  percent-of-revenue assumption (`inhouse_conversion_pct_of_revenue`), not a modeled cost
  centre — purchased system material IS itemized in `system_components`. The boundary is
  deliberate: the studio models what the OEM **buys**, not what it **builds**.
- Volume-tier pricing evaluates annual volume at the allocated supplier, using
  product-level annual volume for tier qualification.
- PDF export deferred (Excel package is the v1 artifact).

## Roadmap

1. FX and multi-currency handling; indexed/commodity pass-through pricing mechanics.
2. Monthly time-phased volumes, ramp curves, and inventory projections.
3. Subassembly-to-parent cost rollup and multi-level BOM costing.
4. LLM-backed contract extraction and narrative generation behind the existing interfaces.
5. Database repository (same interface as `CsvRepository`) and multi-user persistence.
6. Optimization layer (allocation optimizer under capacity/risk constraints).
7. Direct feeds into the Apex Executive SIOP Decision Engine via `integration_outputs`.
