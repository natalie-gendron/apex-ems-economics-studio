# Apex EMS Economics Studio

A standalone module of the **Apex Operations Finance Studio** — turning EMS
(electronics manufacturing services) contracts, supplier quotes, and operational
assumptions into a deterministic, auditable economic decision model.

The central lesson the model demonstrates: **the lowest-quote supplier is not the
lowest-total-economic-cost supplier** once logistics, duties, quality, working capital,
service, and risk are priced onto the same axis. The sample data models a fictional ATE
(automated test equipment) maker at industry scale — **$4.0B modeled revenue, $825M of
EMS spend plus $275M of OEM-consigned strategic silicon** — with $10K–$30K instrument
boards, golden-tester correlation in conversion cost, and $286M of supply exposure split
between OEM-owned and EMS-owned inventory.

- **Application code and full documentation:** [`apex_ems_economics/`](apex_ems_economics/README.md)
- **Original build specification:** [`initial_prompt.md`](initial_prompt.md)

## Quickstart

```bash
cd apex_ems_economics
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py             # run the app
pytest                           # 77 tests
```

## Highlights

- Deterministic quote → true-economic-cost engine (20 Streamlit pages, UI-free core)
- **Every assumption editable in the app** — 23 data tables plus a grouped Model
  Settings page; nothing that moves a dollar is buried in code
- Full per-system COGS: EMS ship-set + itemized purchased system material + labeled in-house
  conversion, with an EMS box-build make-vs-buy scenario
- **Cost per system shipped**: board economics roll up through QPA into ship-set cost,
  exposing $347K of hidden cost on every digital tester shipped
- Inventory **ownership modeled separately from physical location** (consignment economics)
- Contract economics: payment terms, advances, NCNR/liability windows, volume tiers
- Three-level should-cost with cautious variance interpretation
- Scenario builder + comparison (COGS, gross-margin, and cash-flow impacts kept distinct)
- Optional Monte Carlo over the full deterministic engine (seeded, reproducible)
- Rule-based recommendations, data-quality scoring, multi-tab Excel evidence package

All company, supplier, and cost data is **synthetic** — a fictional advanced
test-equipment manufacturer and three fictional EMS suppliers.

Related Apex modules: [Strategic Network Optimizer](https://github.com/natalie-gendron/apex-strategic-network-optimizer) ·
[SIOP Decision Engine](https://github.com/natalie-gendron/apex-siop-decision-engine)
