# Data Directory

Place your input CSV file here before running the pipeline.

## Expected Input Format

The pipeline expects a CSV file with at least these columns:

| Column | Type | Description |
|--------|------|-------------|
| `id` | str/int | Unique violation identifier |
| `created_datetime` | str | UTC timestamp (ISO 8601 or mixed format) |
| `validation_status` | str | `approved`, `rejected`, or `pending` |
| `latitude` | float | Violation location latitude |
| `longitude` | float | Violation location longitude |
| `junction_name` | str | Junction name or `No Junction` |
| `police_station` | str | Reporting police station |
| `vehicle_type` | str | Vehicle type (e.g. `CAR`, `MOTOR CYCLE`) |
| `closed_datetime` | str | Resolution timestamp (may be null) |

## Source Dataset

This project was developed against the Bengaluru illegal parking dataset:
- **Name:** Gridlock Dataset — Jan to May Police Violation (Anonymized)
- **Source:** Kaggle / naelsaade
- **Note:** The filename implies January–May coverage but actual timestamps span November 2023 – March 2024. See `temporal_audit.json` for the date-range consistency check.

## Data Not Committed

CSV files are excluded from version control via `.gitignore`.
Download the dataset separately and place it here as `violations.csv`.
