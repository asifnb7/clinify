from clinify.importers.tools.openmedsdb_batch_runner import run_batch

SOURCE = "/home/clinify/clinify-medicine-source/openmedsdb/OpenMedsDB_385605_Medicines.csv"

def run_census():
    result = run_batch(
        source=SOURCE,
        start=0,
        batch_size=385605,
        write=False,
    )

    inner = result.get("result", {})

    summary = {
        "source_file": result.get("source_file"),
        "start_row": result.get("start_row"),
        "end_row": result.get("end_row"),
        "actual_rows": result.get("actual_rows"),
        "total_rows": inner.get("total_rows"),
        "clean_rows": inner.get("clean_rows"),
        "review_rows": inner.get("review_rows"),
        "created_medications": inner.get("created_medications"),
        "created_items": inner.get("created_items"),
        "created_links": inner.get("created_links"),
        "repaired_items": inner.get("repaired_items"),
        "skipped_existing": inner.get("skipped_existing"),
        "error_count": len(inner.get("errors") or []),
        "preflight_issues": inner.get("preflight_issues"),
    }

    print("\n===== OPENMEDSDB FULL CENSUS SUMMARY =====")
    for key, value in summary.items():
        print(f"{key}: {value}")
    print("===== END CENSUS SUMMARY =====")

    return summary
