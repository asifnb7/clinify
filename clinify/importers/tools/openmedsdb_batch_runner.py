from __future__ import annotations

import csv
import json
import sys
import tempfile
from pathlib import Path

import frappe

from clinify.importers.openmedsdb_importer import import_pilot


DEFAULT_SOURCE = (
    "/home/clinify/clinify-medicine-source/openmedsdb/"
    "OpenMedsDB_385605_Medicines.csv"
)


def write_slice(
    source: Path,
    destination: Path,
    start: int,
    batch_size: int,
) -> int:
    end = start + batch_size
    written = 0

    with (
        source.open("r", newline="", encoding="utf-8-sig") as src,
        destination.open("w", newline="", encoding="utf-8") as dst,
    ):
        reader = csv.reader(src)
        writer = csv.writer(dst)

        header = next(reader)
        writer.writerow(header)

        for row_number, row in enumerate(reader):
            if row_number < start:
                continue
            if row_number >= end:
                break

            writer.writerow(row)
            written += 1

    return written


def run_batch(
    source: str = DEFAULT_SOURCE,
    start: int = 0,
    batch_size: int = 5000,
    write: bool = False,
) -> dict[str, object]:
    source_path = Path(source).expanduser().resolve()

    if not source_path.exists():
        raise FileNotFoundError(f"Source CSV not found: {source_path}")

    if start < 0:
        raise ValueError("start must be >= 0")

    if batch_size <= 0:
        raise ValueError("batch_size must be > 0")

    with tempfile.TemporaryDirectory(
        prefix="clinify-openmedsdb-batch-"
    ) as temp_dir:
        batch_path = Path(temp_dir) / "batch.csv"

        actual_rows = write_slice(
            source_path,
            batch_path,
            start,
            batch_size,
        )

        if actual_rows == 0:
            return {
                "source_file": str(source_path),
                "start_row": start,
                "end_row": start,
                "batch_size": batch_size,
                "actual_rows": 0,
                "status": "COMPLETE",
            }

        result = import_pilot(
            batch_path,
            write=write,
        )

        output = {
            "source_file": str(source_path),
            "start_row": start,
            "end_row": start + actual_rows,
            "batch_size": batch_size,
            "actual_rows": actual_rows,
            "result": result,
        }

        print(json.dumps(output, indent=2, default=str))

        if result.get("errors"):
            print(
                f"\nBATCH COMPLETED WITH "
                f"{len(result['errors'])} ROW ERROR(S).",
                file=sys.stderr,
            )

        return output


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run one resumable OpenMedsDB import batch."
    )
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
    )
    parser.add_argument(
        "--start",
        type=int,
        default=0,
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Actually write the batch. Default is dry-run.",
    )

    args = parser.parse_args()

    run_batch(
        source=args.source,
        start=args.start,
        batch_size=args.batch_size,
        write=args.write,
    )
