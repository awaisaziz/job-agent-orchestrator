"""Dataset ingestion pipeline for local development."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.schemas.job import JobNormalized
from app.services.ingestion.normalize import normalize_raw_record

REPO_ROOT = Path(__file__).resolve().parents[4]
DATA_ROOT = REPO_ROOT / "data"
CATALOG_PATH = DATA_ROOT / "catalog.yaml"


@dataclass(slots=True)
class ProcessedDataset:
    dataset_name: str
    dataset_version: str
    source_path: Path
    output_dir: Path
    normalized_jobs: list[JobNormalized]


def run_dataset_pipeline(dataset_name: str = "jobs_demo", dataset_version: str | None = None) -> ProcessedDataset:
    """Load raw records, normalize them, and persist processed artifacts."""

    catalog = _read_catalog(CATALOG_PATH)
    dataset_config = catalog["datasets"][dataset_name]
    resolved_version = dataset_version or dataset_config["latest_version"]
    version_entry = _resolve_version(dataset_config["versions"], resolved_version)

    source_path = REPO_ROOT / version_entry["source"]
    output_dir = REPO_ROOT / version_entry["processed_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_records = _load_raw_records(source_path)
    normalized_jobs = [normalize_raw_record(record) for record in raw_records]

    _write_jsonl(output_dir / "jobs.normalized.jsonl", normalized_jobs)
    _write_csv(output_dir / "jobs.normalized.csv", normalized_jobs)

    return ProcessedDataset(
        dataset_name=dataset_name,
        dataset_version=resolved_version,
        source_path=source_path,
        output_dir=output_dir,
        normalized_jobs=normalized_jobs,
    )


def _load_raw_records(source_path: Path) -> list[dict[str, Any]]:
    if source_path.suffix == ".jsonl":
        return _read_jsonl(source_path)
    if source_path.suffix == ".csv":
        return _read_csv(source_path)
    raise ValueError(f"Unsupported raw dataset format: {source_path}")


def _read_catalog(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    # minimal yaml support for this catalog structure.
    catalog = json.loads(json.dumps(_tiny_yaml_parse(text)))
    return catalog


def _resolve_version(versions: list[dict[str, Any]], target: str) -> dict[str, Any]:
    for version_entry in versions:
        if version_entry["version"] == target:
            return version_entry
    raise ValueError(f"Dataset version '{target}' not found in catalog")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_jsonl(path: Path, jobs: list[JobNormalized]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for job in jobs:
            handle.write(json.dumps(job.model_dump(mode="json"), ensure_ascii=False) + "\n")


def _write_csv(path: Path, jobs: list[JobNormalized]) -> None:
    fieldnames = ["title", "company", "location", "skills", "entities", "description", "apply_link"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for job in jobs:
            payload = job.model_dump(mode="json")
            payload["skills"] = "|".join(payload["skills"])
            payload["entities"] = "|".join(payload["entities"])
            writer.writerow({field: payload.get(field) for field in fieldnames})


def _tiny_yaml_parse(text: str) -> dict[str, Any]:
    """Parse a small subset of YAML used by data/catalog.yaml."""

    result: dict[str, Any] = {"datasets": {}}
    current_dataset: dict[str, Any] | None = None
    current_versions: list[dict[str, Any]] | None = None
    current_version_item: dict[str, Any] | None = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "datasets:":
            continue

        indent = len(line) - len(line.lstrip(" "))
        if indent == 2 and stripped.endswith(":"):
            dataset_name = stripped[:-1]
            current_dataset = {"versions": []}
            result["datasets"][dataset_name] = current_dataset
            current_versions = current_dataset["versions"]
            current_version_item = None
            continue

        if current_dataset is None:
            continue

        if indent == 4 and stripped.startswith("latest_version:"):
            current_dataset["latest_version"] = stripped.split(":", 1)[1].strip()
            continue

        if indent == 4 and stripped == "versions:":
            continue

        if indent == 6 and stripped.startswith("- version:") and current_versions is not None:
            version = stripped.split(":", 1)[1].strip()
            current_version_item = {"version": version, "schema": {"fields": []}}
            current_versions.append(current_version_item)
            continue

        if current_version_item is None:
            continue

        if indent == 8 and ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key == "schema":
                continue
            current_version_item[key] = value
            continue

        if indent == 10 and stripped == "fields:":
            continue

        if indent == 12 and stripped.startswith("-"):
            current_version_item["schema"]["fields"].append(stripped[1:].strip())

    return result
