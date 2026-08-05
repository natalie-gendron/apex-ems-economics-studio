You are a senior product architect, operations finance leader, cost engineer, supply chain economist, and Python application developer.

Build a functional first-pass application called:

# Apex EMS Economics Studio

This application is a standalone module within a broader platform called Apex Operations Finance Studio.

Apex Operations Finance Studio is an executive decision platform for Operations Finance organizations supporting complex global manufacturing businesses. It combines deterministic financial modeling, scenario analysis, Monte Carlo simulation, mathematical optimization, explainable AI, and executive decision support.

The EMS Economics Studio should help Operations Finance, Procurement, Supply Chain, Engineering, and Operations understand the true economics of outsourced manufacturing relationships and make better decisions about EMS suppliers, contracts, product allocation, sourcing, inventory ownership, service levels, quality, working capital, and cost structure.

The initial application should be standalone. It should not require integration with the Apex Executive SIOP Decision Engine in this first version. However, it must be architected so that its outputs can later feed:

- Product and standard cost
    
- Cost of goods sold
    
- Gross margin
    
- Inventory projections
    
- Working capital
    
- Supply scenarios
    
- Capacity scenarios
    
- Executive SIOP decisions
    
- Strategic network optimization
    
- Manufacturing economics analysis
    

Build the application in Python using Streamlit.

The application must be functional, modular, transparent, explainable, and easy to extend. Do not create a shallow dashboard with hardcoded charts. Build an actual deterministic economic model with editable assumptions, scenario comparison, validations, calculations, outputs, and recommendations.

## 1. Primary business purpose

The application should turn EMS contracts, supplier pricing, operational assumptions, cost structures, inventory terms, quality performance, and service-level commitments into an economic decision model.

The model should answer questions such as:

1. What is the true total cost of producing a product or subassembly at each EMS supplier?
    
2. How does the quoted EMS price compare with an internally estimated should-cost?
    
3. Which supplier is economically preferable after considering not only purchase price, but also freight, duties, inventory ownership, working capital, quality, rework, scrap, expedite costs, lead time, service risk, capacity, and switching costs?
    
4. How do contract terms affect total economics?
    
5. What happens if production volume increases or decreases?
    
6. What happens if product mix changes?
    
7. What happens if demand is more volatile than expected?
    
8. What is the financial impact of customer-owned inventory versus EMS-owned inventory?
    
9. What inventory is owned by the OEM but physically held at an EMS location?
    
10. What is the impact of minimum purchase commitments, noncancelable orders, liability windows, excess inventory provisions, and material authorization terms?
    
11. What is the impact of supplier yield, first-pass yield, defect rates, rework, scrap, warranty exposure, and line fallout?
    
12. What is the cost of maintaining a higher service level?
    
13. What are the financial and operational consequences of shifting volume from one EMS supplier to another?
    
14. What are the savings opportunities from contract renegotiation?
    
15. Which assumptions are known, estimated, benchmarked, inferred, or missing?
    
16. Where should Finance, Procurement, Engineering, or Operations focus next to improve the quality of the decision?
    

## 2. Intended users

Design the tool for the following users:

### Operations Finance

Operations Finance owns the model framework, economic logic, financial outputs, scenario modeling, governance, and connection to COGS, gross margin, working capital, and executive decisions.

### Procurement and Commodity Management

Procurement provides supplier quotes, contract terms, purchase price data, component market intelligence, negotiation assumptions, sourcing constraints, and supplier commercial information.

### Supply Chain

Supply Chain provides lead times, inventory policies, demand variability, safety-stock expectations, material liability windows, logistics assumptions, and supply continuity risks.

### Manufacturing and Operations

Operations provides capacity, throughput, cycle time, labor assumptions, manufacturing constraints, line utilization, transfer readiness, and operational performance.

### Quality

Quality provides first-pass yield, defect rates, rework rates, scrap rates, supplier corrective actions, warranty exposure, and quality-risk assumptions.

### Engineering

Engineering provides BOM structure, test requirements, process routing, technical constraints, alternate component options, subassembly specifications, and product transfer requirements.

### Executive leadership

Executives consume the scenario comparison, financial outcomes, decision recommendations, risks, tradeoffs, and evidence package.

## 3. Core design principles

The application must follow these principles:

1. Finance owns the economic framework, but inputs come from cross-functional partners.
    
2. The model should distinguish quoted cost from true economic cost.
    
3. The model should distinguish accounting cost from decision-relevant cost.
    
4. The model must explicitly model inventory ownership and physical location separately.
    
5. The model must distinguish known facts from assumptions and estimates.
    
6. Every important output should be traceable to source inputs and formulas.
    
7. The model should support incomplete information.
    
8. Missing information should not prevent the model from running.
    
9. When information is missing, the model should use clearly labeled assumptions, benchmarks, or ranges.
    
10. The model should never present an estimate as a known fact.
    
11. The tool should support progressive refinement. A user should be able to start with a rough model and improve it over time.
    
12. AI may assist with interpretation, triangulation, anomaly detection, contract extraction, and recommendations, but the financial calculations must remain deterministic and auditable.
    
13. The application should be modular enough that future modules can call the economic engine without relying on the Streamlit interface.
    

## 4. Initial scope

Build a first-pass application that supports:

- Multiple EMS suppliers
    
- Multiple products or subassemblies
    
- Multiple manufacturing sites
    
- Multiple scenarios
    
- Supplier quotes
    
- Contract economics
    
- Inventory ownership
    
- Inventory location
    
- BOM cost
    
- Bundled or partially transparent supplier pricing
    
- Should-cost estimates
    
- Labor and conversion cost
    
- Overhead and supplier margin
    
- Freight and logistics
    
- Duties and tariffs
    
- Quality economics
    
- Service-level economics
    
- Capacity and utilization
    
- Lead time
    
- Working capital
    
- Material liability
    
- Volume tiers
    
- Minimum commitments
    
- One-time costs
    
- Transition and switching costs
    
- Risk-adjusted cost
    
- Scenario comparison
    
- Executive recommendations
    
- Assumption confidence and data quality
    

Do not attempt to build a full ERP, contract lifecycle system, procurement suite, or complete network optimizer.

## 5. Application pages

Create the following Streamlit pages.

### Page 1: Executive Overview

Show:

- Selected scenario
    
- Total annual EMS spend
    
- Total modeled economic cost
    
- Quoted cost versus economic cost
    
- Quoted cost versus should-cost
    
- Estimated savings opportunity
    
- Gross margin impact
    
- Working-capital impact
    
- Inventory owned by the company at EMS sites
    
- Inventory owned by EMS suppliers
    
- Quality cost
    
- Logistics cost
    
- Risk-adjusted cost
    
- Top five economic drivers
    
- Top five risks
    
- Top five actions
    
- Supplier economic ranking
    
- Product allocation summary
    
- Data confidence score
    
- Scenario comparison summary
    

Include clear executive callouts such as:

- Lowest quoted supplier
    
- Lowest true economic-cost supplier
    
- Lowest risk-adjusted supplier
    
- Best quality-adjusted supplier
    
- Best working-capital supplier
    
- Most important contract renegotiation opportunity
    
- Largest unknown or data gap
    

### Page 2: Supplier and Site Profiles

Allow the user to create and edit supplier and site records.

Include fields such as:

- Supplier name
    
- Site name
    
- Country
    
- Region
    
- Currency
    
- Contract start date
    
- Contract end date
    
- Supplier status
    
- Approved products
    
- Strategic importance
    
- Financial health rating
    
- Capacity rating
    
- Quality rating
    
- Delivery rating
    
- Responsiveness rating
    
- Geographic risk
    
- Political risk
    
- Natural-disaster risk
    
- Single-source risk
    
- Alternate-source availability
    
- Transition lead time
    
- Notes
    

### Page 3: Product and Subassembly Setup

Allow users to define:

- Product family
    
- Product
    
- Subassembly
    
- Internal product number
    
- Annual volume
    
- Monthly volume
    
- Forecast growth
    
- Unit selling price
    
- Current standard cost
    
- Current EMS supplier
    
- Alternate EMS suppliers
    
- Product lifecycle stage
    
- Technical complexity
    
- Required certifications
    
- Test requirements
    
- Target gross margin
    
- Target service level
    
- Demand variability
    
- Product priority
    
- Transfer complexity
    
- Notes
    

Support products that are:

- Fully assembled by the EMS
    
- Partially assembled by the EMS
    
- Built from customer-consigned materials
    
- Built from EMS-procured materials
    
- Built using a hybrid material-ownership model
    

### Page 4: BOM and Material Economics

Support BOM-level modeling where data is available.

The user should be able to enter:

- Product
    
- Component or material
    
- Component category
    
- Quantity per assembly
    
- Unit price
    
- Currency
    
- Price source
    
- Supplier
    
- Commodity index
    
- Lead time
    
- Minimum order quantity
    
- Order multiple
    
- Scrap factor
    
- Yield factor
    
- Freight factor
    
- Duty rate
    
- Ownership model
    
- Physical location
    
- Purchase responsibility
    
- Price validity date
    
- Confidence rating
    
- Notes
    

Ownership model values should include:

- OEM-owned and stored internally
    
- OEM-owned and consigned to EMS
    
- EMS-owned until consumption
    
- EMS-owned until finished-goods transfer
    
- Supplier-owned vendor-managed inventory
    
- Hybrid
    
- Unknown
    

Purchase responsibility values should include:

- OEM procurement
    
- EMS procurement
    
- Component supplier direct
    
- Hybrid
    
- Unknown
    

Support bundled material costs when detailed BOM data is not available.

For bundled costs, allow:

- Supplier quoted material bundle
    
- Estimated component content
    
- Benchmark material cost
    
- Internal engineering estimate
    
- Comparable product estimate
    
- Historical price estimate
    
- Market-index estimate
    
- Confidence range
    
- Unexplained residual
    

The model should calculate an unexplained cost or price residual:

Unexplained residual =  
Supplier quoted material or subassembly price  
minus identified material cost  
minus estimated conversion cost  
minus logistics  
minus duties  
minus estimated supplier overhead  
minus estimated supplier margin

Clearly label this as an analytical estimate, not proof of supplier overcharging.

### Page 5: Contract Economics

Build a structured contract-term input screen.

Include:

#### Pricing terms

- Base unit price
    
- Currency
    
- Price effective date
    
- Volume tiers
    
- Annual price reduction
    
- Productivity commitment
    
- Cost-plus pricing
    
- Fixed-price pricing
    
- Indexed pricing
    
- Commodity pass-through
    
- FX adjustment mechanism
    
- Inflation adjustment
    
- Labor-rate adjustment
    
- Freight adjustment
    
- Expedited freight treatment
    
- Supplier margin or markup
    
- Open-book or closed-book pricing
    
- Quote validity period
    

#### Volume terms

- Minimum annual volume
    
- Minimum monthly volume
    
- Take-or-pay commitment
    
- Capacity reservation
    
- Forecast commitment
    
- Firm-order window
    
- Flexibility window
    
- Upside flexibility
    
- Downside flexibility
    
- Volume-tier reset rules
    

#### Inventory and material-liability terms

- Who owns raw material
    
- Who owns WIP
    
- Who owns finished goods
    
- Transfer-of-title point
    
- Material authorization window
    
- Noncancelable/nonreturnable liability
    
- Excess-material liability
    
- Obsolescence liability
    
- Safety-stock ownership
    
- Buffer-stock ownership
    
- Vendor-managed inventory terms
    
- Customer deposits
    
- Advance payments
    
- Payment terms
    
- Inventory financing fee
    
- Carrying-cost charge
    
- Inventory buyback provisions
    
- End-of-life liability
    
- Last-time-buy responsibility
    

#### Service terms

- Required on-time delivery
    
- Required lead time
    
- Required response time
    
- Upside response expectation
    
- Expedite commitment
    
- Recovery time
    
- Business continuity requirements
    
- Penalties
    
- Service credits
    
- Premium freight responsibility
    

#### Quality terms

- Yield commitment
    
- Defect-rate commitment
    
- First-pass-yield commitment
    
- Rework responsibility
    
- Scrap responsibility
    
- Warranty responsibility
    
- Field-failure responsibility
    
- Return-material authorization responsibility
    
- Corrective-action expectations
    
- Quality penalties
    
- Cost recovery provisions
    

#### Cost transparency

- Full open-book
    
- Partial open-book
    
- Bundled pricing
    
- No cost transparency
    
- Audit rights
    
- Quote support requirements
    
- BOM visibility
    
- Labor visibility
    
- Overhead visibility
    
- Supplier-margin visibility
    
- Commodity-index visibility
    

#### Contract risk

- Termination notice
    
- Termination fees
    
- Tooling ownership
    
- Equipment ownership
    
- Intellectual-property constraints
    
- Transfer assistance
    
- Data ownership
    
- Supplier change restrictions
    
- Sub-tier supplier approval requirements
    

Allow users to record each term as:

- Confirmed
    
- Estimated
    
- Inferred
    
- Missing
    
- Not applicable
    

Include a source-reference field and confidence score.

### Page 6: Conversion and Manufacturing Cost

Model EMS conversion economics.

Inputs should include:

- Direct labor hours per unit
    
- Direct labor rate
    
- Labor burden
    
- Machine hours per unit
    
- Machine rate
    
- Setup time
    
- Batch size
    
- Changeover time
    
- Test time
    
- Test-equipment rate
    
- Inspection time
    
- Packaging time
    
- Indirect labor
    
- Factory overhead
    
- Site overhead
    
- Corporate allocation
    
- Utilities
    
- Consumables
    
- Floor-space allocation
    
- Depreciation
    
- Maintenance
    
- Engineering support
    
- Program-management fee
    
- Procurement fee
    
- Material-handling fee
    
- Profit margin
    
- Markup method
    
- Utilization
    
- Yield
    
- Rework
    
- Scrap
    
- Learning curve
    
- Volume tier
    

Calculate:

- Direct labor cost
    
- Burdened labor cost
    
- Equipment cost
    
- Test cost
    
- Setup allocation
    
- Indirect cost
    
- Factory-overhead cost
    
- Program-management cost
    
- Procurement cost
    
- Material-handling cost
    
- Supplier profit
    
- Total conversion cost per unit
    

### Page 7: Should-Cost Model

Build a should-cost capability that can operate at multiple levels of detail.

#### Level 1: High-level benchmark

Use:

- Material percentage
    
- Labor percentage
    
- Conversion percentage
    
- Overhead percentage
    
- Supplier-margin percentage
    
- Freight
    
- Duties
    
- Quality
    
- Working capital
    

#### Level 2: Process-based estimate

Use:

- BOM cost
    
- Labor hours
    
- Machine hours
    
- Test time
    
- Yield
    
- Scrap
    
- Overhead
    
- Logistics
    
- Supplier margin
    

#### Level 3: Detailed bottom-up estimate

Use component-level BOM and detailed process routing.

Allow the user to select the should-cost method and confidence rating.

Compare:

- Supplier quote
    
- Internal should-cost
    
- Historical actual cost
    
- Current standard cost
    
- Comparable supplier quote
    
- Comparable product cost
    

Calculate:

- Dollar variance
    
- Percentage variance
    
- Variance by cost bucket
    
- Potential negotiation opportunity
    
- Potential model error
    
- Confidence-adjusted opportunity
    

Do not automatically label all positive variance as supplier overpricing. The output should distinguish:

- Likely commercial opportunity
    
- Possible specification difference
    
- Possible volume difference
    
- Possible quality or service premium
    
- Possible logistics difference
    
- Possible overhead difference
    
- Possible missing data
    
- Unexplained variance
    

### Page 8: Inventory and Working Capital

This is a critical page.

Model physical location and financial ownership separately.

Track inventory by:

- Supplier
    
- Site
    
- Product
    
- Material
    
- Inventory stage
    
- Ownership
    
- Physical location
    
- Accounting entity
    
- Quantity
    
- Unit cost
    
- Total value
    
- Days of supply
    
- Aging
    
- Demand coverage
    
- Excess status
    
- Obsolescence risk
    
- Liability status
    

Inventory stages should include:

- Raw material
    
- Work in process
    
- Finished goods
    
- In transit
    
- Safety stock
    
- Strategic buffer
    
- Excess
    
- Obsolete
    
- Noncancelable/nonreturnable
    
- Last-time-buy
    

Calculate:

- OEM-owned inventory at OEM sites
    
- OEM-owned inventory at EMS sites
    
- EMS-owned inventory at EMS sites
    
- Supplier-owned inventory
    
- Inventory in transit
    
- Total economic inventory exposure
    
- Balance-sheet inventory
    
- Off-balance-sheet supply exposure
    
- Inventory carrying cost
    
- Financing cost
    
- Insurance cost
    
- Storage cost
    
- Obsolescence cost
    
- Excess risk
    
- Cash conversion impact
    
- Days inventory outstanding
    
- Working-capital impact
    

Use a configurable annual inventory carrying-cost percentage.

Working-capital cost should include:

Inventory carrying cost =  
Average inventory value × annual carrying-cost percentage

Allow the carrying-cost percentage to be decomposed into:

- Cost of capital
    
- Storage
    
- Insurance
    
- Shrinkage
    
- Handling
    
- Obsolescence
    
- Administrative cost
    

### Page 9: Quality Economics

Model the cost of quality by supplier, product, and scenario.

Inputs:

- Incoming defect rate
    
- First-pass yield
    
- Final yield
    
- Scrap rate
    
- Rework rate
    
- Rework hours
    
- Rework labor cost
    
- Reinspection cost
    
- Retest cost
    
- Material loss
    
- Line downtime
    
- Premium freight
    
- Return rate
    
- Warranty rate
    
- Field-failure rate
    
- Customer penalty
    
- Engineering investigation cost
    
- Corrective-action cost
    
- Containment cost
    
- Recall probability
    
- Recall impact
    
- Reputation-risk score
    

Calculate:

- Scrap cost
    
- Rework cost
    
- Retest cost
    
- Inspection cost
    
- Downtime cost
    
- Return cost
    
- Warranty cost
    
- Field-failure cost
    
- Quality-related freight
    
- Expected recall cost
    
- Total cost of poor quality
    
- Cost of quality per unit
    
- Quality-adjusted unit cost
    

Expected recall cost =  
Recall probability × estimated recall financial impact

Clearly distinguish expected-value calculations from booked accounting costs.

### Page 10: Logistics, Duties, and Landed Cost

Inputs:

- Shipping origin
    
- Shipping destination
    
- Incoterms
    
- Freight mode
    
- Standard freight rate
    
- Premium freight rate
    
- Average shipment size
    
- Shipments per month
    
- Transit time
    
- Insurance
    
- Brokerage
    
- Duties
    
- Tariffs
    
- Taxes
    
- Packaging
    
- Handling
    
- Warehousing
    
- Port cost
    
- Customs cost
    
- Expected expedite frequency
    
- Expedite responsibility
    
- Carbon or sustainability cost, optional
    

Calculate:

- Freight cost per unit
    
- Premium freight per unit
    
- Duties per unit
    
- Tariffs per unit
    
- Warehousing per unit
    
- Logistics cost per unit
    
- Total landed cost
    

### Page 11: Service-Level Economics

Model the cost and value of service.

Inputs:

- Target on-time delivery
    
- Actual on-time delivery
    
- Target lead time
    
- Actual lead time
    
- Demand variability
    
- Supply variability
    
- Upside flexibility
    
- Downside flexibility
    
- Recovery time
    
- Expedite rate
    
- Stockout probability
    
- Lost-sales risk
    
- Revenue-at-risk
    
- Customer penalty
    
- Required safety stock
    
- Required buffer stock
    

Calculate:

- Service-level cost
    
- Safety-stock cost
    
- Buffer-stock cost
    
- Expedite cost
    
- Stockout expected cost
    
- Revenue-at-risk
    
- Margin-at-risk
    
- Service-adjusted cost
    

The model should recognize that a supplier with a higher unit price may still be economically superior because of better service, quality, flexibility, or working-capital performance.

### Page 12: Capacity and Flexibility

Inputs:

- Available capacity
    
- Committed capacity
    
- Utilization
    
- Maximum utilization
    
- Overtime capacity
    
- Expansion capacity
    
- Expansion lead time
    
- Reserved capacity
    
- Capacity reservation fee
    
- Minimum economic volume
    
- Maximum feasible volume
    
- Ramp rate
    
- Transfer lead time
    
- Qualification lead time
    
- Tooling lead time
    
- Equipment constraint
    
- Labor constraint
    
- Test constraint
    
- Component constraint
    

Calculate:

- Capacity headroom
    
- Volume feasibility
    
- Capacity cost
    
- Overtime cost
    
- Reservation cost
    
- Ramp risk
    
- Allocation constraints
    
- Volume-shift feasibility
    

### Page 13: Risk-Adjusted Economics

Allow users to define risks by supplier and product.

Risk categories:

- Supplier financial risk
    
- Country risk
    
- Natural-disaster risk
    
- Geopolitical risk
    
- Cyber risk
    
- Quality risk
    
- Delivery risk
    
- Capacity risk
    
- Labor risk
    
- Component concentration
    
- Single-source risk
    
- Sub-tier supplier risk
    
- Intellectual-property risk
    
- Transition risk
    
- Contract risk
    
- Data transparency risk
    

For each risk, capture:

- Probability
    
- Financial impact
    
- Operational impact
    
- Time to recover
    
- Mitigation status
    
- Confidence
    
- Notes
    

Calculate:

Expected risk cost =  
Probability × estimated financial impact

Calculate:

Risk-adjusted cost =  
Base economic cost + expected risk cost

Do not imply that expected risk cost is an accounting expense. Label it as a decision-analysis measure.

### Page 14: Scenario Builder

Allow users to create, save, duplicate, edit, and compare scenarios.

Example scenarios:

- Current state
    
- Renegotiated contract
    
- Shift 20 percent of volume to Supplier B
    
- Shift all new-product volume to Supplier C
    
- EMS owns all standard components
    
- OEM consigns all critical components
    
- Demand decreases 20 percent
    
- Demand increases 30 percent
    
- Quality improves
    
- Quality deteriorates
    
- Freight disruption
    
- Tariff increase
    
- FX movement
    
- Supplier price increase
    
- Volume-tier improvement
    
- Lower safety stock
    
- Higher service-level requirement
    
- Dual-source strategy
    
- Supplier exit
    
- Product transfer
    
- End-of-life exposure
    
- Cost-reduction negotiation
    

Scenario inputs should support both absolute values and changes from the baseline.

### Page 15: Scenario Comparison

Compare up to five scenarios.

Show:

- Annual volume
    
- Quoted purchase cost
    
- Material cost
    
- Conversion cost
    
- Logistics
    
- Duties
    
- Quality cost
    
- Working-capital cost
    
- Service cost
    
- Risk-adjusted cost
    
- One-time cost
    
- Transition cost
    
- Total annual economic cost
    
- Economic cost per unit
    
- Standard-cost impact
    
- COGS impact
    
- Gross-margin impact
    
- Cash-flow impact
    
- Inventory impact
    
- Capacity feasibility
    
- Service performance
    
- Quality performance
    
- Data confidence
    
- Key risks
    
- Key assumptions
    

Include:

- Waterfall chart
    
- Cost bridge
    
- Supplier comparison
    
- Scenario ranking
    
- Sensitivity chart
    
- Recommendation summary
    
- Tradeoff matrix
    

### Page 16: Contract Opportunity Analysis

Identify potential negotiation levers.

Examples:

- Volume-tier reset
    
- Annual productivity reduction
    
- Open-book pricing
    
- Material markup reduction
    
- Labor-rate adjustment
    
- Overhead reduction
    
- Supplier-margin reduction
    
- Freight responsibility
    
- Inventory ownership
    
- Payment terms
    
- Material liability
    
- Excess and obsolescence terms
    
- Yield commitment
    
- Quality recovery
    
- Service penalties
    
- Capacity reservation
    
- Minimum-volume commitment
    
- Commodity-index mechanism
    
- FX mechanism
    
- Cost audit rights
    
- Transfer assistance
    
- End-of-life liability
    

For each lever, calculate where possible:

- Current economic impact
    
- Proposed change
    
- Annual savings
    
- Working-capital impact
    
- Risk impact
    
- Implementation difficulty
    
- Negotiation difficulty
    
- Confidence
    
- Recommended owner
    
- Recommended next action
    

### Page 17: Data Quality and Assumption Register

Build a centralized assumption register.

Every major assumption should include:

- Assumption name
    
- Category
    
- Supplier
    
- Product
    
- Scenario
    
- Value
    
- Unit
    
- Source
    
- Source date
    
- Owner
    
- Status
    
- Confidence
    
- Minimum value
    
- Most likely value
    
- Maximum value
    
- Last updated
    
- Review date
    
- Notes
    

Statuses:

- Confirmed
    
- Estimated
    
- Benchmarked
    
- Inferred
    
- Missing
    
- Stale
    
- Under review
    

Create a data-quality score based on:

- Completeness
    
- Recency
    
- Source reliability
    
- Confidence
    
- Coverage of high-value cost drivers
    

Show:

- High-impact assumptions
    
- Low-confidence assumptions
    
- Stale assumptions
    
- Missing contract terms
    
- Largest model sensitivities
    
- Recommended data-collection priorities
    

### Page 18: Executive Evidence Package

Create a downloadable executive summary containing:

- Decision statement
    
- Current-state economics
    
- Scenario alternatives
    
- Recommended scenario
    
- Financial impact
    
- Gross-margin impact
    
- Working-capital impact
    
- Quality impact
    
- Service impact
    
- Risk impact
    
- One-time costs
    
- Key assumptions
    
- Data-confidence score
    
- Sensitivities
    
- Risks
    
- Mitigations
    
- Required decisions
    
- Required actions
    
- Decision owners
    
- Supporting evidence
    

Allow export to CSV and Excel where practical.

A PDF export may be represented as a future enhancement if it materially complicates the first version.

## 6. Core economic calculations

Build a deterministic calculation engine separate from the Streamlit UI.

At minimum, calculate:

### Quoted purchase cost

Quoted purchase cost =  
Quoted unit price × volume

### Material cost

Material cost =  
Sum of component quantity × component unit cost  
adjusted for scrap, yield, freight, and duty where applicable

### Conversion cost

Conversion cost =  
Labor

- labor burden
    
- equipment
    
- test
    
- setup allocation
    
- indirect labor
    
- factory overhead
    
- program-management fee
    
- procurement fee
    
- material-handling fee
    
- supplier margin
    

### Logistics cost

Logistics cost =  
Freight

- premium freight
    
- insurance
    
- brokerage
    
- duties
    
- tariffs
    
- packaging
    
- warehousing
    
- customs
    
- handling
    

### Cost of poor quality

Cost of poor quality =  
Scrap

- rework
    
- retest
    
- inspection
    
- downtime
    
- returns
    
- warranty
    
- field failures
    
- quality-related freight
    
- expected recall cost
    
- corrective-action cost
    

### Working-capital cost

Working-capital cost =  
Average company-owned inventory × carrying-cost percentage

- deposits
    
- advance payments
    
- financing charges
    
- inventory exposure costs
    

### Service cost

Service cost =  
Safety-stock carrying cost

- buffer-stock carrying cost
    
- expedite cost
    
- expected stockout cost
    
- expected lost-margin cost
    
- penalties
    

### Expected risk cost

Expected risk cost =  
Sum of risk probability × risk impact

### Total economic cost

Total economic cost =  
Quoted purchase cost

- costs not included in the quote
    
- logistics
    
- duties and tariffs
    
- cost of poor quality
    
- working-capital cost
    
- service cost
    
- expected risk cost
    
- one-time costs
    
- transition costs  
    minus recoveries, rebates, credits, and savings
    

Avoid double counting. Clearly identify which costs are included in the supplier quote and which are incremental.

### Economic cost per unit

Economic cost per unit =  
Total annual economic cost ÷ annual good units received

Good units received should account for yield, scrap, and defects.

### Gross-margin impact

Gross-margin impact =  
Change in revenue, if any  
minus change in COGS

For the first version, assume revenue is unchanged unless the scenario explicitly includes service-related lost sales or revenue-at-risk.

### Working-capital impact

Working-capital impact =  
Change in company-owned inventory

- change in deposits
    
- change in prepayments
    
- change in payment-term effects
    
- change in material liability exposure
    

### Should-cost variance

Should-cost variance =  
Supplier quoted cost minus internal should-cost

### Risk-adjusted supplier score

Create a configurable weighted score using:

- Economic cost
    
- Quality
    
- Delivery
    
- Service
    
- Capacity
    
- Flexibility
    
- Working capital
    
- Risk
    
- Data transparency
    
- Strategic fit
    

Weights should be editable and sum to 100 percent.

Do not allow the score to replace the detailed economics. It is a decision-support summary only.

## 7. Treatment of uncertainty

The first version must support deterministic scenarios and sensitivity analysis.

Also build an optional Monte Carlo module that can be enabled or disabled.

Potential uncertain variables:

- Volume
    
- Product mix
    
- Material price
    
- Commodity price
    
- FX rate
    
- Yield
    
- Scrap
    
- Rework
    
- Freight rate
    
- Expedite frequency
    
- Lead time
    
- Quality failure
    
- Supplier disruption
    
- Demand variability
    
- Inventory level
    
- Transition duration
    

Support distributions such as:

- Normal
    
- Triangular
    
- Uniform
    
- Lognormal
    
- Bernoulli
    
- Discrete scenario
    

For Monte Carlo outputs, show:

- Mean
    
- Median
    
- P10
    
- P50
    
- P90
    
- Minimum
    
- Maximum
    
- Probability one scenario is cheaper than another
    
- Probability savings exceed a target
    
- Probability gross-margin impact is negative
    
- Probability inventory exceeds a threshold
    
- Top drivers of outcome variability
    

Use a fixed random seed option for reproducibility.

The application must clearly distinguish deterministic outputs from simulated outputs.

## 8. Data architecture

Create a modular data structure using CSV files for sample data and an internal repository layer that can later be replaced with a database.

Suggested entities:

- suppliers
    
- sites
    
- products
    
- subassemblies
    
- scenarios
    
- bom_items
    
- supplier_quotes
    
- contract_terms
    
- conversion_costs
    
- inventory_records
    
- quality_metrics
    
- logistics_assumptions
    
- service_levels
    
- capacity_records
    
- risks
    
- assumptions
    
- negotiation_levers
    
- scenario_overrides
    
- model_results
    
- decision_records
    

Use stable unique identifiers.

Include created date, updated date, source, owner, confidence, and scenario where relevant.

## 9. Software architecture

Use a clean project structure similar to:

apex_ems_economics/  
app.py  
pages/  
core/  
economics_engine.py  
should_cost_engine.py  
inventory_engine.py  
quality_engine.py  
logistics_engine.py  
service_engine.py  
risk_engine.py  
scenario_engine.py  
monte_carlo_engine.py  
scoring_engine.py  
recommendation_engine.py  
validation_engine.py  
data/  
sample/  
templates/  
models/  
schemas.py  
repositories/  
csv_repository.py  
services/  
export_service.py  
contract_parser_service.py  
ai_insight_service.py  
components/  
charts.py  
tables.py  
input_forms.py  
executive_cards.py  
tests/  
requirements.txt  
README.md

Use typed Python where practical.

Use dataclasses or Pydantic models for major entities.

Keep business logic out of Streamlit page files.

The financial engine must be callable independently from the user interface.

## 10. User experience

The application should look like a credible executive operations-finance application.

Use:

- Wide-screen layout
    
- Clear navigation
    
- Executive summary cards
    
- Expanders for detailed assumptions
    
- Editable tables
    
- Input validations
    
- Tooltips
    
- Clear units
    
- Currency formatting
    
- Percentage formatting
    
- Conditional formatting
    
- Scenario selectors
    
- Supplier filters
    
- Product filters
    
- Confidence indicators
    
- Warnings for missing data
    
- Explanations of formulas
    
- Download buttons
    

Use a professional, restrained visual style.

Avoid excessive color.

Do not use decorative graphics that do not support a decision.

## 11. Explainability requirements

Every major output should allow the user to understand:

- What the number means
    
- How it was calculated
    
- Which inputs drove it
    
- Which assumptions were used
    
- What data is missing
    
- What the confidence level is
    
- What could change the answer
    

Create calculation-detail views or expandable formula explanations.

Create a cost bridge from:

Supplier quoted price

to:

True economic cost

The bridge should show additions or deductions for:

- Material differences
    
- Conversion
    
- Freight
    
- Duties
    
- Quality
    
- Working capital
    
- Service
    
- Risk
    
- One-time cost
    
- Rebates or credits
    

## 12. AI capabilities

AI should be optional and separated from the deterministic engine.

Create placeholder service interfaces for future AI integration.

Potential AI capabilities:

1. Contract extraction
    

Accept pasted contract text and identify candidate terms such as:

- Pricing
    
- Volume commitments
    
- Material liability
    
- Inventory ownership
    
- Title transfer
    
- Payment terms
    
- Service levels
    
- Quality obligations
    
- Termination
    
- Tooling ownership
    
- Cost transparency
    

The AI output must be treated as a draft requiring human validation.

2. Cost triangulation
    

Help estimate missing costs using:

- Historical data
    
- Comparable products
    
- Comparable suppliers
    
- User-provided benchmarks
    
- Engineering estimates
    
- Market indices
    

3. Anomaly detection
    

Flag:

- Supplier quote changes
    
- Unusual markup
    
- Unusual conversion rates
    
- Deteriorating yield
    
- Excess inventory
    
- Cost variances
    
- Contract inconsistencies
    

4. Narrative insights
    

Generate:

- Executive summary
    
- Key drivers
    
- Risks
    
- Recommended actions
    
- Questions for Procurement
    
- Questions for Quality
    
- Questions for Engineering
    
- Questions for the EMS supplier
    

5. Assumption challenge
    

Identify assumptions that:

- Have low confidence
    
- Have high financial impact
    
- Appear inconsistent
    
- Require validation
    
- Drive scenario conclusions
    

Do not require an API key for the application to run.

If no API key is available, show deterministic template-based insights.

## 13. Sample data

Include realistic sample data for a fictional advanced test-equipment manufacturer.

Do not use confidential or claimed actual Teradyne data.

Create three fictional EMS suppliers:

- Atlas Manufacturing Services
    
- Meridian Electronics
    
- Pacific Integrated Systems
    

Create at least:

- Three supplier sites
    
- Four products
    
- Multiple subassemblies
    
- Multiple BOM structures
    
- Different ownership models
    
- Different contract structures
    
- Different quality profiles
    
- Different service levels
    
- Different capacity constraints
    
- Different risk profiles
    

Include at least four sample scenarios:

1. Current State
    
2. Shift 25 Percent of Volume to Lower-Cost Supplier
    
3. Renegotiate Inventory Ownership and Payment Terms
    
4. Dual-Source Critical Product
    

Construct the sample data so that:

- The lowest quoted-price supplier is not the lowest total-economic-cost supplier.
    
- One supplier has better quality but higher quoted cost.
    
- One supplier has favorable working-capital terms.
    
- One supplier has low cost but elevated risk.
    
- A contract renegotiation creates meaningful cash improvement.
    
- A dual-source scenario costs slightly more but reduces expected risk.
    

## 14. Validation rules

Build validation checks such as:

- Scenario volume must not be negative
    
- Supplier weights must sum to 100 percent where allocation is required
    
- Yield must be between 0 and 100 percent
    
- Scrap must be between 0 and 100 percent
    
- Risk probability must be between 0 and 100 percent
    
- Contract dates must be logical
    
- Currency must be specified
    
- Volume tiers must not overlap
    
- Ownership model must be selected
    
- Physical location must be selected
    
- Costs cannot be double counted
    
- Supplier capacity must support allocated volume
    
- Supplier scoring weights must sum to 100 percent
    
- Minimum, most likely, and maximum assumptions must be ordered correctly
    
- Monte Carlo distributions must have valid parameters
    

Warnings should not necessarily stop the model. Differentiate:

- Error
    
- Warning
    
- Information
    
- Data-quality issue
    

## 15. Testing

Create unit tests for:

- Material-cost calculation
    
- Conversion-cost calculation
    
- Total-landed-cost calculation
    
- Working-capital calculation
    
- Quality-cost calculation
    
- Risk-adjusted-cost calculation
    
- Should-cost variance
    
- Scenario comparison
    
- Volume-tier pricing
    
- Inventory ownership treatment
    
- Yield and good-unit calculation
    
- Avoidance of double counting
    
- Monte Carlo reproducibility
    

Include at least one end-to-end test using the sample scenarios.

## 16. Exports

Support export of:

- Supplier comparison
    
- Scenario comparison
    
- Cost breakdown
    
- Contract-term register
    
- Assumption register
    
- Inventory exposure
    
- Negotiation opportunities
    
- Executive evidence package
    

Export to CSV.

Where practical, export a multi-tab Excel workbook containing:

- Executive Summary
    
- Scenario Comparison
    
- Supplier Economics
    
- Product Economics
    
- Inventory
    
- Quality
    
- Contract Terms
    
- Risks
    
- Assumptions
    
- Actions
    

## 17. Decision recommendations

Build a deterministic recommendation engine.

The recommendation engine should not merely choose the cheapest supplier.

It should consider:

- Total economic cost
    
- Gross-margin impact
    
- Working-capital impact
    
- Quality
    
- Service
    
- Capacity
    
- Flexibility
    
- Risk
    
- Switching cost
    
- Data confidence
    
- Strategic fit
    

Recommendations should be framed as:

- Recommended action
    
- Why
    
- Financial impact
    
- Operational impact
    
- Key risks
    
- Required conditions
    
- Confidence
    
- Next validation step
    

Possible recommendations:

- Maintain current allocation
    
- Renegotiate contract
    
- Shift incremental volume
    
- Shift a defined percentage of volume
    
- Dual-source
    
- Increase consignment
    
- Reduce OEM-owned inventory
    
- Require open-book pricing
    
- Validate BOM pricing
    
- Launch should-cost review
    
- Improve quality before volume shift
    
- Reserve capacity
    
- Avoid supplier transfer
    
- Collect more data before deciding
    

## 18. Future integration design

Create interface-ready output tables for future integration with the Apex platform.

At minimum, create standardized outputs for:

### Product cost output

- Product
    
- Scenario
    
- Supplier
    
- Material cost
    
- Conversion cost
    
- Quality cost
    
- Logistics cost
    
- Total economic cost
    
- Cost per unit
    
- Confidence
    

### Inventory output

- Product
    
- Supplier
    
- Scenario
    
- Ownership
    
- Location
    
- Inventory value
    
- Days of supply
    
- Carrying cost
    
- Risk exposure
    

### Margin output

- Product
    
- Scenario
    
- Revenue
    
- COGS
    
- Gross profit
    
- Gross margin
    
- Change from baseline
    

### Supply output

- Product
    
- Supplier
    
- Scenario
    
- Allocated volume
    
- Capacity utilization
    
- Lead time
    
- Service level
    
- Risk score
    

These outputs should be usable later by:

- Executive SIOP Decision Engine
    
- Manufacturing Economics Studio
    
- Margin Intelligence
    
- Working Capital Optimizer
    
- Strategic Network Optimizer
    

## 19. README requirements

Create a detailed README that explains:

- Purpose of the application
    
- Business problem
    
- Intended users
    
- Core economic concepts
    
- Installation
    
- How to run the application
    
- Project structure
    
- Sample scenarios
    
- Calculation logic
    
- Data files
    
- Assumption treatment
    
- AI architecture
    
- Testing
    
- Export features
    
- Future roadmap
    
- Known limitations
    

Include commands such as:

python -m venv .venv

source .venv/bin/activate

For Windows:

.venv\Scripts\activate

Then:

pip install -r requirements.txt

streamlit run app.py

## 20. Implementation order

Build the application in phases.

### Phase 1

- Project structure
    
- Data schemas
    
- Sample data
    
- Core deterministic economic engine
    
- Supplier, product, contract, inventory, and scenario inputs
    
- Executive Overview
    
- Scenario Comparison
    
- Basic exports
    
- Unit tests
    

### Phase 2

- Should-cost engine
    
- Quality economics
    
- Service-level economics
    
- Risk-adjusted economics
    
- Negotiation opportunity analysis
    
- Assumption register
    
- Executive Evidence Package
    

### Phase 3

- Monte Carlo simulation
    
- AI service placeholders
    
- Contract text extraction interface
    
- Advanced sensitivity analysis
    
- Future integration output tables
    

Complete as much of all three phases as practical, but prioritize a stable, functioning deterministic application over unfinished advanced features.

## 21. Important modeling distinctions

The application must explicitly distinguish:

### Ownership versus location

Inventory may be owned by the OEM but physically located at the EMS.

Do not assume physical possession determines accounting ownership.

### Quote versus economic cost

A supplier quote may exclude freight, duties, quality costs, working capital, service costs, risk, transition costs, or customer-owned material.

### Cost versus cash

A change may improve cash flow without changing accounting COGS.

For example:

- Payment terms
    
- Deposits
    
- Inventory ownership
    
- Prepayments
    

### Booked cost versus expected cost

Expected disruption cost and expected recall cost are decision-analysis measures, not necessarily booked expenses.

### Known versus estimated information

All assumptions and inferred contract terms must be visibly labeled.

### Supplier price versus supplier value

A higher-price supplier may deliver lower total economic cost through better quality, service, flexibility, or inventory terms.

### Recurring versus one-time cost

Separate:

- Recurring unit cost
    
- Recurring annual fixed cost
    
- One-time transition cost
    
- Tooling
    
- Qualification
    
- Engineering
    
- Severance
    
- Inventory write-off
    
- Contract termination
    

## 22. Final deliverable

Produce a fully runnable repository.

Do not stop at an architecture description.

Create the actual files, code, sample data, tests, and README.

After building, provide:

1. A summary of what was created
    
2. The project structure
    
3. Instructions to run it
    
4. Key modeling assumptions
    
5. Known limitations
    
6. Recommended next development steps
    
7. Any decisions you made where the requirements were ambiguous
    

Use sensible defaults rather than asking repeated clarification questions.

The application should demonstrate the core Apex philosophy:

Finance should not merely report supplier cost after the fact. Finance should create a transparent decision system that connects contracts, operations, supply chain, quality, inventory, risk, and economics so leadership can make better decisions before outcomes are locked in.