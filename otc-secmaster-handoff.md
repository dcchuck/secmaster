# OTC / Microcap Secmaster Project Handoff

## Purpose

This document captures the current plan for building a solo-developer **OTC / microcap security master (secmaster)**. It is intended as a kickoff artifact for a new repository and as a handoff brief for another agent or engineer.

The goal is not to recreate Bloomberg. The goal is to build a **practical, survivorship-safe, point-in-time-aware secmaster** that is robust enough for microcap and OTC research, backtesting, and universe construction.

---

## Project Goals

### Primary goal
Build a canonical internal data model that can answer:

- What security is this, really?
- What issuer does it belong to?
- What identifiers has it used over time?
- What venue or OTC tier did it trade on at a given date?
- Was it active, delisted, grey market, expert market, suspended, or caveat emptor at a given time?
- What major corporate actions changed its identity or continuity?

### Research goals
The secmaster should support:

- OTC and microcap universe construction
- Historical screening without survivorship bias
- Point-in-time joins to price and fundamentals data
- Investigation of messy issuer histories such as shells, reverse mergers, ticker changes, and reverse splits
- Future integration with trading, research, or backtesting workflows

### Design goals
The system should be:

- **Portable**: schema and documentation stored in git
- **Local-dev friendly**: easy to run with Postgres and migration tooling
- **Point-in-time aware**: mutable facts tracked with effective dates
- **Survivorship-safe**: dead and delisted names remain first-class
- **Vendor-agnostic**: internal canonical IDs should outlive any single vendor
- **Incrementally buildable**: useful in phases, without requiring perfect coverage on day one

---

## Key Decisions Made So Far

### 1. The project will use SQL migrations as the source of truth
The schema should live in migration files committed to the repo.

Rationale:
- Most portable long-term format
- Directly usable for deployment and local dev
- Avoids coupling the core design to a browser-only diagramming tool
- Easy for future agents or engineers to extend safely

### 2. The repo should include a Mermaid ERD for human-readable schema documentation
A `schema.md` or similar documentation file should include a Mermaid ER diagram.

Rationale:
- Visual and easy to understand
- Git-friendly
- Renders in many markdown workflows, including GitHub-supported Mermaid environments
- Keeps the visual model close to the actual schema docs

### 3. Ticker must not be the primary identity key
The canonical model will use internal IDs rather than ticker symbols.

Rationale:
- Tickers change
- Tickers get reused
- Different venues can use overlapping symbols
- OTC history is too messy for ticker-as-identity

### 4. The data model must distinguish issuer, security, and listing
This separation is a core design decision.

- **Issuer** = company / legal entity
- **Security** = instrument
- **Listing** = that security quoted or traded on a venue / tier over time

Rationale:
- A company can have multiple securities
- A security can move across venues or OTC tiers
- Historical modeling is cleaner and more accurate
- Prevents a flat schema from collapsing important distinctions

### 5. Point-in-time history is required
Important mutable data must support effective dating.

Examples:
- issuer names
n- security identifiers
- listing status
- venue / tier membership
- classifications
- capital structure metadata

Recommended pattern:
- `effective_start_date`
- `effective_end_date`

### 6. Survivorship bias resistance is mandatory
The secmaster must preserve:

- dead tickers
- delisted names
- historical mappings
- prior issuer names
- old venue assignments
- OTC status history

### 7. OTC status is not optional metadata
For this domain, status and tier are part of the core identity context.

Examples:
- OTCQX
- OTCQB
- Pink
- Grey
- Expert Market
- Caveat Emptor
- SEC suspension
- current information / transfer agent verification flags where available

### 8. The build should be incremental
We do not need to build the entire perfect secmaster in phase one.

The initial implementation should prioritize:

- identifier history
- OTC tier and status history
- listing continuity
- reverse splits and symbol changes
- shares outstanding / float / market cap as-of history

---

## Product and Vendor Landscape Summary

This project discussion also established a rough external-data landscape.

### Official OTC-style secmaster source
**OTC Markets** appears to offer the closest thing to an official OTC secmaster through its Security Data File and Company Data File, with enterprise-style pricing.

High-level takeaway:
- Official and likely richest OTC-specific source
- Not priced like a consumer product
- More appropriate as an enterprise or serious commercial input

### Retail-friendlier substitutes
The closest lower-cost substitutes discussed were:

- **EODHD**: more retail-friendly pricing, broader exchange coverage, and more explicit OTC sub-venue handling
- **Polygon / Massive**: U.S.-focused API with OTC included, but more API/data-platform oriented than classic secmaster-oriented
- **Databento Security Master**: architecturally more secmaster-like, but appears to be positioned in a more sales-led / pro data category

### Practical conclusion
There does not appear to be a clean, truly retail-priced, official OTC secmaster product for hobbyist or solo traders. The likely path is:

- start with lower-cost reference + market data vendors
- build a canonical internal secmaster
- optionally upgrade upstream sources later

---

## Proposed Canonical Data Model

The current design is a **solo-builder OTC / microcap secmaster v1**.

### Core entities

#### `issuer`
Represents the company or legal entity.

Representative fields:
- `issuer_id`
- `legal_name`
- `normalized_name`
- `issuer_type`
- `country_incorporation`
- `domicile_country`
- `cik`
- `lei`
- `sic`
- `naics`
- `is_shell_flag`
- `is_bankrupt_flag`
- `is_liquidating_flag`

#### `issuer_name_history`
Tracks historical issuer names over time.

Representative fields:
- `issuer_id`
- `name`
- `normalized_name`
- `effective_start_date`
- `effective_end_date`
- `source`

#### `security`
Represents a financial instrument belonging to an issuer.

Representative fields:
- `security_id`
- `issuer_id`
- `security_type`
- `security_subtype`
- `share_class`
- `par_value`
- `currency`
- `is_primary_equity_flag`
- `underlying_security_id`

#### `security_identifier_history`
Tracks historical identifiers for each security.

Representative fields:
- `security_id`
- `id_type`
- `id_value`
- `venue_code`
- `effective_start_date`
- `effective_end_date`
- `is_primary_flag`
- `source`

Examples of `id_type`:
- ticker
- cusip
- isin
- figi
- sedol
- bbgid
- vendor_symbol
- otc_symbol

#### `listing`
Represents a security listed or quoted on a venue over time.

Representative fields:
- `listing_id`
- `security_id`
- `venue_code`
- `mic_code`
- `primary_symbol`
- `currency`
- `country`
- `listing_status`
- `effective_start_date`
- `effective_end_date`
- `is_primary_listing_flag`

#### `listing_status_history`
Tracks OTC status and other tradability/compliance context.

Representative fields:
- `listing_id`
- `status_date`
- `listing_status`
- `tier`
- `caveat_emptor_flag`
- `unsolicited_quotes_only_flag`
- `shell_risk_flag`
- `sec_suspension_flag`
- `bankruptcy_flag`
- `current_information_flag`
- `transfer_agent_verified_flag`
- `source`

#### `corporate_action`
Captures major lifecycle and continuity-changing events.

Representative fields:
- `corporate_action_id`
- `security_id`
- `issuer_id`
- `action_type`
- `announcement_date`
- `effective_date`
- `ratio_from`
- `ratio_to`
- `old_value`
- `new_value`
- `notes`
- `source`

Examples of `action_type`:
- split
- reverse_split
- symbol_change
- name_change
- merger
- acquisition
- spinoff
- cusip_change
- isin_change
- recapitalization
- bankruptcy
- liquidation
- uplisting
- delisting

#### `shares_outstanding_history`
Tracks point-in-time capital structure fields.

Representative fields:
- `security_id`
- `as_of_date`
- `shares_outstanding`
- `public_float`
- `authorized_shares`
- `market_cap`
- `enterprise_value`
- `value_source_type`
- `source`

#### `issuer_classification_history`
Tracks historical classification mappings.

Representative fields:
- `issuer_id`
- `classification_system`
- `classification_code`
- `classification_name`
- `effective_start_date`
- `effective_end_date`

#### `security_lifecycle_event`
Catch-all structured event stream for important but irregular lifecycle facts.

Representative fields:
- `security_id`
- `event_date`
- `event_type`
- `details_json`
- `source`

#### `vendor_security_map`
Maps external vendor identities to internal canonical entities.

Representative fields:
- `vendor_name`
- `vendor_entity_type`
- `vendor_id`
- `issuer_id`
- `security_id`
- `listing_id`
- `effective_start_date`
- `effective_end_date`
- `confidence_score`
- `mapping_method`

#### `data_source_observation`
Audit and lineage table for raw vendor facts.

Representative fields:
- `vendor_name`
- `dataset_name`
- `record_key`
- `field_name`
- `field_value_text`
- `field_value_numeric`
- `field_value_date`
- `observed_at`
- `effective_date`
- `issuer_id`
- `security_id`
- `listing_id`
- `raw_payload_json`

---

## Minimal Serious v1 Scope

If the first implementation needs to stay lean, the minimum serious version should include at least:

- `issuer`
- `issuer_name_history`
- `security`
- `security_identifier_history`
- `listing`
- `listing_status_history`
- `corporate_action`

And ideally add early:

- `shares_outstanding_history`
- `vendor_security_map`

This should be enough to support meaningful point-in-time security identity work.

---

## Core Modeling Principles

### Canonical IDs
Use internal canonical IDs for:

- issuer
- security
- listing

Do not make ticker, vendor symbol, or CUSIP the primary key.

### Effective dating
Any mutable identity or status field should be modeled with time boundaries.

Preferred pattern:
- `effective_start_date`
- `effective_end_date`

Typical point-in-time lookup pattern:

```sql
WHERE effective_start_date <= :as_of_date
  AND (effective_end_date IS NULL OR effective_end_date > :as_of_date)
```

### Source lineage
Important facts should retain origin metadata.

At a minimum, preserve:
- source/vendor name
- source record ID if available
- loaded timestamp
- observation timestamp when relevant

### OTC-first worldview
For this project, OTC tier and status data are not “nice to have.” They are central to the secmaster.

### Incremental ingestion
The data model should support phased ingestion rather than requiring all domains at once.

---

## Suggested Implementation Order

### Phase 1: schema foundation
- initialize repo
- choose migration tool
- create base tables for issuer, security, listing, identifier history, and OTC status history
- add markdown schema documentation with Mermaid ERD

### Phase 2: current-universe ingest
- ingest current issuer/security/listing universe from chosen vendors
- establish canonical internal IDs
- ingest current identifiers and basic status flags

### Phase 3: historical identity data
- ingest historical ticker/name changes
- populate `issuer_name_history`
- populate `security_identifier_history`

### Phase 4: corporate actions
- load splits, reverse splits, ticker changes, name changes, uplisting/delisting events

### Phase 5: capital structure history
- ingest shares outstanding, float, and market cap as-of data

### Phase 6: auditability and vendor mapping
- add `vendor_security_map`
- add `data_source_observation`
- refine confidence and mapping workflows

---

## Repo / Tooling Direction

### Chosen direction
The current preferred workflow is:

- **SQL migrations in repo** as the schema source of truth
- **Mermaid ERD in markdown** for visual schema documentation
- local development with Postgres

### Why this direction was chosen
It is:
- portable
- git-native
- local-dev friendly
- easy to hand off between agents and humans
- not dependent on a hosted schema editor

### Diagramming note
A browser tool like dbdiagram may still be useful for fast design iteration, but it is not the canonical source of truth for this repo.

---

## Immediate Deliverables for Repo Kickoff

A kickoff agent should create:

1. **Repository scaffold**
   - README
   - migrations folder
   - docs folder
   - schema documentation file

2. **Initial migrations**
   - create the core secmaster tables
   - add primary keys, foreign keys, and reasonable uniqueness constraints

3. **Schema documentation**
   - `docs/schema.md`
   - include project goals, domain notes, and Mermaid ERD

4. **Local dev setup**
   - Postgres via Docker or local install
   - migration runner
   - basic bootstrap instructions

5. **Seed or fixture strategy**
   - at least one ugly OTC-style example issuer/security lifecycle for testing identity history

---

## Suggested Questions for the Next Agent to Resolve

The next agent or engineer should make concrete calls on:

- migration tool choice
- Postgres version target
- naming conventions
- enum strategy vs text columns
- indexing strategy for point-in-time queries
- JSONB usage policy
- source ingestion architecture
- canonical matching strategy across vendors
- how to represent OTC-specific flags when source coverage is uneven

---

## Open Questions

These have not been fully decided yet:

- Which migration framework to use
- Which initial vendor or data source to integrate first
- Exact constraints and indexes for each table
- Whether to model some categorical fields as enums or lookup tables
- Whether to store raw vendor data in a separate landing schema before canonicalization
- How much historical coverage can be obtained affordably at the start

---

## Summary

The secmaster project is intended to become a durable internal identity layer for OTC and microcap securities.

The most important design decisions already made are:

- SQL migrations in repo are the source of truth
- Mermaid ERD in markdown is the visual documentation layer
- ticker is not identity
- issuer, security, and listing must be separate concepts
- point-in-time history is required
- survivorship-safe data is required
- OTC status and tier history are core features, not decorations
- the build should proceed incrementally, with early focus on identity history and OTC lifecycle context

This should be enough for a new repo or new agent to begin implementation.
