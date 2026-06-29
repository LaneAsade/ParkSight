"""
cli.py — Command-line entry point.

    python -m parksight.cli --input data/raw/violations.csv --output outputs/
"""

import argparse
import logging
import sys

from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="parksight",
        description="ParkSight AI — illegal-parking hotspot intelligence pipeline.",
    )
    p.add_argument("--input", required=True, help="Path to the violations CSV.")
    p.add_argument("--output", default="outputs/", help="Output directory (default: outputs/).")
    p.add_argument("--config", default=None, help="Path to settings.yaml (default: config/settings.yaml).")
    p.add_argument("--teams", type=int, default=None, help="Number of patrol teams for MILP assignment.")
    p.add_argument("--skip-traffic", action="store_true", help="Skip Google Distance Matrix traffic enrichment.")
    p.add_argument("--skip-external-apis", action="store_true",
                    help="Skip all external API calls (traffic + road geometry); run fully offline.")
    p.add_argument("--google-api-key", default=None, help="Google Maps API key (overrides GOOGLE_MAPS_API_KEY).")
    p.add_argument("--mappls-api-key", default=None, help="Mappls access token (overrides MAPPLS_ACCESS_TOKEN).")
    p.add_argument("--log-level", default="INFO",
                    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Logging verbosity.")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    summary = run_pipeline(
        input_path=args.input,
        output_dir=args.output,
        config_path=args.config,
        teams=args.teams,
        skip_traffic=args.skip_traffic,
        skip_external_apis=args.skip_external_apis,
        google_api_key=args.google_api_key,
        mappls_api_key=args.mappls_api_key,
    )
    if summary.get("n_failures"):
        logging.warning("Pipeline completed with %d stage failure(s): %s",
                         summary["n_failures"], list(summary["failures"].keys()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
