import hashlib
import json
import sqlite3
import tarfile
import tempfile
from collections import Counter
from pathlib import Path

import xlrd


ORIGINAL = Path("com.halfbrick.birzzlefever-20160501-111000.tar.gz")
HEALTHY = Path("device-snapshots/2026-08-29-bonus-mode-test/post-bonus-v18-data.tar.gz")
OUTPUT = Path("save-analysis/ole-analytics.json")
OLE_NAMES = {"clearbox", "highscore", "order", "profile", "test"}


def archive_files(path):
    with tarfile.open(path, "r:*") as archive:
        return {
            Path(member.name).name: archive.extractfile(member).read()
            for member in archive.getmembers()
            if member.isfile() and archive.extractfile(member) is not None
        }


def workbook_report(raw):
    book = xlrd.open_workbook(file_contents=raw, on_demand=True)
    sheets = []
    total_nonempty = 0
    numeric = Counter()
    strings = []
    for sheet_name in book.sheet_names():
        sheet = book.sheet_by_name(sheet_name)
        nonempty = 0
        for row in range(sheet.nrows):
            for column in range(sheet.ncols):
                value = sheet.cell_value(row, column)
                if value in ("", None):
                    continue
                nonempty += 1
                if isinstance(value, (int, float)):
                    numeric[str(int(value) if value == int(value) else value)] += 1
                elif len(strings) < 100:
                    strings.append({"sheet": sheet_name, "row": row, "column": column, "value": value})
        total_nonempty += nonempty
        sheets.append({"name": sheet_name, "rows": sheet.nrows, "columns": sheet.ncols, "nonempty": nonempty})
    return {
        "sheet_count": len(sheets),
        "total_nonempty": total_nonempty,
        "numeric_frequency": dict(numeric.most_common()),
        "string_cells": strings,
        "sheets": sheets,
    }


def sqlite_report(name, raw):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "artifact.db"
        path.write_bytes(raw)
        connection = sqlite3.connect(path)
        tables = []
        for table, sql in connection.execute("SELECT name, sql FROM sqlite_master WHERE type='table'"):
            count = connection.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
            tables.append({"name": table, "rows": count, "sql": sql})
        connection.close()
    return {"name": name, "tables": tables}


def main():
    original = archive_files(ORIGINAL)
    healthy = archive_files(HEALTHY)
    workbooks = {}
    for name in sorted(OLE_NAMES):
        report = workbook_report(original[name])
        report.update(
            original_sha256=hashlib.sha256(original[name]).hexdigest(),
            healthy_sha256=hashlib.sha256(healthy[name]).hexdigest(),
            unchanged=original[name] == healthy[name],
        )
        workbooks[name] = report
    databases = []
    for name, raw in healthy.items():
        if raw.startswith(b"SQLite format 3\x00"):
            databases.append(sqlite_report(name, raw))
    preference_names = sorted(name for name in healthy if name.endswith(".xml"))
    output = {
        "workbooks": workbooks,
        "databases": databases,
        "xml_preferences": preference_names,
        "analytics_artifacts": [
            "Kontagent.xml", "kontagentCheck_v2_2.dat", "mat_id.xml", "mat_queue.xml",
            "mat_log_id_open.xml", "mat_log_id_last_open.xml", "OL_Prefs_Keys.xml",
            "com.google.android.gcm.xml", "AppEventsLogger.persistedevents",
            "e30b431a9b2d47948fed9f6a5602fa91",
        ],
    }
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps({name: {"sheets": value["sheet_count"], "cells": value["total_nonempty"], "unchanged": value["unchanged"]} for name, value in workbooks.items()}, indent=2))


if __name__ == "__main__":
    main()
