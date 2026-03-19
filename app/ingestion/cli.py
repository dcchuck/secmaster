"""CLI for running data ingestion.

Usage:
    python -m app.ingestion.cli fidelity
"""
import argparse

from sqlmodel import Session

from app.db.session import engine

INGESTORS = {
    "fidelity": "app.ingestion.fidelity.FidelityIngestor",
}


def main():
    parser = argparse.ArgumentParser(description="Run data ingestion")
    parser.add_argument("vendor", choices=INGESTORS.keys(), help="Vendor to ingest from")
    args = parser.parse_args()

    module_path, class_name = INGESTORS[args.vendor].rsplit(".", 1)
    module = __import__(module_path, fromlist=[class_name])
    ingestor_class = getattr(module, class_name)

    with Session(engine) as session:
        ingestor = ingestor_class(session)
        result = ingestor.run()
        print(f"Ingestion complete: {result}")


if __name__ == "__main__":
    main()
