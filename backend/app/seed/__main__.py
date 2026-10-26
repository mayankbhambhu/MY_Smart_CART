"""python -m app.seed [--reset]  — create tables and load demo data (--reset wipes everything first)."""

import argparse
import logging

from app.seed import init_db

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="drop all tables before seeding")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    init_db(seed=True, reset=args.reset)
    print("Database ready.")
