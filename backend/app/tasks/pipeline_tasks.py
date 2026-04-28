"""Pipeline task orchestration and async retry placeholders.

This module documents how to migrate synchronous demo execution to Celery workers.
Use app.tasks.worker.celery_app to register asynchronous pipeline stages.

Suggested structure:
- enqueue_demo_pipeline(run_id): fan-out stage tasks or chain sequential tasks.
- task_ingestion_normalization: normalize raw postings and persist stage logs.
- task_match_scoring: compute scores, apply top-N selection, persist stage logs.
- task_resume_tailoring: generate tailored resume for highest match.

Retry policy placeholder (per-task):
- autoretry_for = (TimeoutError, ConnectionError)
- retry_backoff = True
- retry_backoff_max = 60
- retry_jitter = True
- max_retries = 3
"""


def run_pipeline_tasks() -> list[str]:
    """Placeholder synchronous order used in local mock flow."""
    return ["ingestion", "matching", "tailoring", "application", "feedback"]
