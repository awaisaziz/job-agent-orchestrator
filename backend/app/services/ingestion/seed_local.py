"""Seed command for local ingestion reproducibility."""

from __future__ import annotations

import argparse

from app.db.base import Base
from app.db.models.user import User
from app.db.session import SessionLocal, engine
from app.services.ingestion.pipeline import run_dataset_pipeline
from app.services.ingestion.repository import persist_normalized_jobs


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize demo dataset and persist into local DB")
    parser.add_argument("--dataset", default="jobs_demo")
    parser.add_argument("--dataset-version", default=None)
    parser.add_argument("--user-email", default="seed.user@example.com")
    parser.add_argument("--user-name", default="Seed User")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)

    processed = run_dataset_pipeline(dataset_name=args.dataset, dataset_version=args.dataset_version)

    with SessionLocal() as session:
        user = session.query(User).filter(User.email == args.user_email).one_or_none()
        if user is None:
            user = User(email=args.user_email, full_name=args.user_name)
            session.add(user)
            session.commit()
            session.refresh(user)

        persist_normalized_jobs(
            session,
            user_id=user.id,
            dataset_version=processed.dataset_version,
            jobs=processed.normalized_jobs,
        )

    print(
        "seed_complete "
        f"dataset={processed.dataset_name} version={processed.dataset_version} "
        f"normalized_jobs={len(processed.normalized_jobs)} output_dir={processed.output_dir}"
    )


if __name__ == "__main__":
    main()
