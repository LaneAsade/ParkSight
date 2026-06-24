# ParkSight AI — Data Schema

## Input: violations.csv

| Column | Type | Description |
|--------|------|-------------|
| `id` | int | Unique challan identifier |
| `created_datetime` | ISO-8601 string (UTC) | When the challan was issued |
| `junction_name` | string | Nearest junction name |
| `police_station` | string | Issuing police station |
| `district` | string | Administrative district |
| `latitude` | float | Violation location latitude |
| `longitude` | float | Violation location longitude |
| `vehicle_type` | string | Vehicle category (CAR, TWO_WHEELER, AUTO, BUS, …) |
| `validation_status` | string | Adjudication status: `approved`, `rejected`, `pending` |

## Key output artifacts

### hotspot_clusters.csv
One row per DBSCAN cluster. Fields: `cluster_id`, `top_junction`, `police_station`, `district`, `violations`, `n_junctions`, `pct_at_junction`, `pct_peak_hour`, `top_vehicle`, `peak_hour`, `lat`, `lon`, `risk_score`, `risk_tier`.

### traffic_enrichment.csv
One row per cluster with traffic probe data. Fields: `cluster_id`, `n_directions_attempted`, `n_directions_succeeded`, `mean_congestion_index`, `mean_avg_speed_kmh`, `mean_delay_minutes`, `validation_status`.

### capacity_impact.csv
One row per cluster with road geometry. Fields: `cluster_id`, `road_class`, `lane_count`, `road_width_m`, `capacity_loss_pct`, `erci_index`, `capacity_loss_tier`, `geometry_source`, `validation_status`, `confidence_level`.

### evidence_ledger.csv
Claims with provenance labels. Fields: `claim`, `value`, `status`, `source`, `confidence`.

### temporal_audit.json
Date range, approval rate, backlog warnings, monthly panel metadata.

### patrol_plan.csv
Patrol assignments output from the MILP solver.
