# Epstein Investigation - Hex Dashboard Setup Guide

This guide explains how to set up interactive dashboards in [Hex](https://hex.tech) using the exported CSV datasets.

## Quick Start

1. **Upload CSV files** from `hex_datasets/` folder to Hex
2. **Create 5 dashboards** using the configurations below
3. **Connect data sources** and build visualizations

---

## Dataset Overview

| Dataset | Records | Purpose |
|---------|---------|---------|
| `nodes.csv` | 4,004 | Network graph nodes (people, orgs, locations) |
| `edges.csv` | 153 | Relationships between entities |
| `transactions.csv` | 35 | Major financial transactions |
| `entity_totals.csv` | 15 | Aggregated financial flows per entity |
| `time_series.csv` | 8 | Transaction volumes by year |
| `events.csv` | 10,514 | Dated events extracted from claims |
| `parallel_tracks.csv` | 15 | Multi-track timeline (1953-2022) |
| `locations.csv` | 98 | Properties and jurisdictions |
| `jurisdictions.csv` | 3 | Offshore jurisdiction analysis |
| `claims.csv` | 72,223 | All knowledge claims with confidence |
| `evidence_gaps.csv` | 5 | Investigation priority by topic |
| `entity_types.csv` | 3 | Entity type distribution |

---

## Dashboard 1: Network Graph - "Power Web"

### Data Sources
- `nodes.csv` (primary)
- `edges.csv` (relationships)

### Setup Steps

1. **Import Data**
   ```sql
   -- In Hex SQL cell
   SELECT * FROM nodes
   ```

2. **Create Network Chart**
   - Chart type: **Network Graph** (or use Python with networkx)
   - Nodes: `entity_id`, Label: `name`
   - Node Size: `mention_count`
   - Node Color: `role_category`

3. **Color Mapping**
   | Category | Color | Description |
   |----------|-------|-------------|
   | `core` | Red | Epstein inner circle |
   | `finance` | Gold | Financial actors |
   | `intel_defense` | Purple | Intelligence/defense |
   | `political` | Blue | Politicians |
   | `victim` | Teal | Victims/survivors |
   | `legal` | Green | Law enforcement |
   | `other` | Gray | Others |

4. **Add Filters**
   - Dropdown: `role_category`
   - Dropdown: `entity_type`
   - Slider: `mention_count` (min threshold)

### Python Alternative (if native network chart unavailable)
```python
import pandas as pd
import networkx as nx
import plotly.graph_objects as go

nodes = hex_df  # nodes.csv
edges = hex_df2  # edges.csv

G = nx.Graph()
for _, row in nodes.iterrows():
    G.add_node(row['entity_id'], label=row['name'],
               category=row['role_category'], size=row['mention_count'])

for _, row in edges.iterrows():
    G.add_edge(row['source_id'], row['target_id'], weight=row['strength'])

# Use plotly for interactive visualization
pos = nx.spring_layout(G, k=0.5)
# ... create plotly figure
```

---

## Dashboard 2: Financial Flow - "Follow the Money"

### Data Sources
- `transactions.csv`
- `entity_totals.csv`
- `time_series.csv`

### Setup Steps

1. **Sankey Diagram** (Money Flow)
   ```sql
   SELECT source_entity, target_entity, amount_usd, purpose
   FROM transactions
   WHERE evidence_strength IN ('high', 'medium')
   ORDER BY amount_usd DESC
   ```
   - Source: `source_entity`
   - Target: `target_entity`
   - Value: `amount_usd`
   - Tooltip: `purpose`

2. **Top Transactions Bar Chart**
   - X-axis: `target_entity`
   - Y-axis: `amount_usd`
   - Color: `transaction_type`
   - Sort: Descending by amount

3. **Time Series Line Chart**
   ```sql
   SELECT year, total_flow, transaction_count
   FROM time_series
   ORDER BY year
   ```
   - X-axis: `year`
   - Y-axis: `total_flow`
   - Secondary Y: `transaction_count`

4. **Entity Totals Table**
   - Columns: entity_name, total_inflow, total_outflow, net_flow
   - Format: Currency ($)
   - Conditional formatting: Red for negative net_flow

### Key Insights to Highlight
- Wexner → Epstein: $1.3B+ (largest flow)
- Leon Black → Epstein: $170M ("tax advice")
- Epstein → Carbyne: $1.5M (Israeli surveillance)

---

## Dashboard 3: Timeline - "Chronology"

### Data Sources
- `events.csv`
- `parallel_tracks.csv`

### Setup Steps

1. **Parallel Timeline Table**
   ```sql
   SELECT year, epstein_activity, financial_event, intel_event, legal_response
   FROM parallel_tracks
   ORDER BY year
   ```
   - Display as formatted table with colored columns
   - Each column represents a "track"

2. **Event Density Heatmap**
   ```sql
   SELECT
     SUBSTRING(event_date, 1, 4) as year,
     event_type,
     COUNT(*) as event_count
   FROM events
   WHERE event_date != ''
   GROUP BY year, event_type
   ```
   - X-axis: `year`
   - Y-axis: `event_type`
   - Color intensity: `event_count`

3. **Events Explorer Table**
   - Columns: event_date, event_type, title, confidence_score
   - Searchable by title
   - Filterable by event_type, confidence_score

4. **Add Filters**
   - Date range slider
   - Event type multi-select
   - Confidence threshold slider

### Key Periods to Highlight
- 1991: Wexner POA + Robert Maxwell death
- 2005-2008: Florida investigation → NPA
- 2019: Arrest → Death (48 days)

---

## Dashboard 4: Geographic - "Properties & Locations"

### Data Sources
- `locations.csv`
- `jurisdictions.csv`

### Setup Steps

1. **Property Map**
   ```sql
   SELECT name, lat, lng, value_usd, owner, purpose, location_type
   FROM locations
   WHERE lat IS NOT NULL AND lat != 0
   ```
   - Map type: Scatter map or Mapbox
   - Latitude: `lat`
   - Longitude: `lng`
   - Bubble size: `value_usd`
   - Tooltip: `name`, `purpose`, `owner`

2. **Property Value Bar Chart**
   ```sql
   SELECT name, value_usd, location_type
   FROM locations
   WHERE value_usd > 0
   ORDER BY value_usd DESC
   ```

3. **Jurisdiction Analysis**
   ```sql
   SELECT jurisdiction, entity_count, shell_company_count, secrecy_score
   FROM jurisdictions
   ```
   - Bar chart with secrecy_score overlay

### Key Properties
| Property | Location | Value | Purpose |
|----------|----------|-------|---------|
| 9 E 71st St | NYC | $77M | Primary residence, surveillance |
| Little St. James | USVI | $63M | Private island |
| Great St. James | USVI | $22M | Second island |
| Zorro Ranch | NM | $18M | 8,000 acres, DNA plans |
| El Brillo Way | Palm Beach | $12M | 40+ victims |
| Paris Apartment | France | $8.7M | European base |

---

## Dashboard 5: Evidence Matrix - "Claim Verification"

### Data Sources
- `claims.csv`
- `evidence_gaps.csv`
- `entity_types.csv`

### Setup Steps

1. **Confidence Distribution**
   ```sql
   SELECT
     ROUND(confidence_score, 1) as confidence_bucket,
     COUNT(*) as claim_count
   FROM claims
   GROUP BY confidence_bucket
   ORDER BY confidence_bucket
   ```
   - Chart type: Histogram
   - X-axis: confidence_bucket
   - Y-axis: claim_count

2. **Verification Status Pie Chart**
   ```sql
   SELECT verification_status, COUNT(*) as count
   FROM claims
   GROUP BY verification_status
   ```

3. **Evidence Gaps Priority Table**
   ```sql
   SELECT topic, claims_count, avg_confidence,
          unverified_count, investigation_priority
   FROM evidence_gaps
   ORDER BY investigation_priority DESC
   ```
   - Highlight rows with high `investigation_priority`

4. **Claims Explorer**
   - Searchable table with all 72K claims
   - Columns: claim_type, summary, confidence_score, event_date
   - Full-text search on `summary` and `content`

5. **Entity Type Distribution**
   ```sql
   SELECT entity_type, entity_count, total_mentions, avg_mentions
   FROM entity_types
   ```

---

## Dashboard Layout Recommendations

### Single Page Layout
```
+------------------+------------------+
|   Key Metrics    |   Key Metrics    |
|   (4 stat cards) |   (4 stat cards) |
+------------------+------------------+
|                                     |
|        Main Visualization           |
|        (Network/Sankey/Map)         |
|                                     |
+------------------+------------------+
|   Supporting     |   Supporting     |
|   Chart 1        |   Chart 2        |
+------------------+------------------+
|        Data Table (searchable)      |
+-------------------------------------+
|        Filters Sidebar              |
+-------------------------------------+
```

### Key Metrics Cards
- **$1.7B+** - Total documented financial flow
- **4,004** - Entities in database
- **72,223** - Knowledge claims
- **40+** - Identified victims (Florida)
- **0** - Clients charged

---

## SQL Snippets for Common Queries

### Find connections to specific person
```sql
SELECT n2.name, e.relationship_type, e.strength
FROM edges e
JOIN nodes n1 ON e.source_id = n1.entity_id
JOIN nodes n2 ON e.target_id = n2.entity_id
WHERE n1.name ILIKE '%Epstein%'
ORDER BY e.strength DESC
```

### High-confidence claims about topic
```sql
SELECT summary, confidence_score, event_date
FROM claims
WHERE content ILIKE '%surveillance%'
  AND confidence_score > 0.7
ORDER BY confidence_score DESC
LIMIT 50
```

### Financial flow by year
```sql
SELECT
  SUBSTRING(date, 1, 4) as year,
  SUM(amount_usd) as total,
  COUNT(*) as tx_count
FROM transactions
WHERE amount_usd > 0
GROUP BY year
ORDER BY year
```

---

## Tips for Hex

1. **Use SQL cells** for data transformation before visualization
2. **Create parameters** for interactive filters (dropdowns, sliders)
3. **Use Python cells** for complex visualizations (networkx, plotly)
4. **Enable caching** for large datasets (claims.csv is 28MB)
5. **Create calculated columns** in SQL for derived metrics

---

## Export Script

To regenerate the CSV files with updated data:

```bash
cd C:\Users\kazim\dac\rag
python backend/scripts/export_hex_datasets.py
```

Files will be saved to `hex_datasets/` directory.

---

## Questions or Issues?

The export script is at: `backend/scripts/export_hex_datasets.py`

Data sources:
- Supabase knowledge base (4,004 entities, 72K claims)
- 17 import batches from TrumpEpsteinFiles documents
- Web research enrichment (financial transactions, defense connections)
