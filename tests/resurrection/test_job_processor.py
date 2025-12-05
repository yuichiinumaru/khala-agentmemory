import pytest
import json
from datetime import datetime, timezone
from khala.infrastructure.background.jobs.job_processor import JobProcessor, JobDefinition, JobPriority, JobStatus

def test_job_serialization_datetime():
    processor = JobProcessor(redis_url=None) # In-memory

    payload = {
        "timestamp": datetime.now(timezone.utc),
        "nested": {"date": datetime(2025, 1, 1)}
    }

    job = JobDefinition(
        job_id="test_1",
        job_type="test",
        job_class="TestJob",
        priority=JobPriority.MEDIUM,
        payload=payload,
        created_at=datetime.now(timezone.utc)
    )

    # This should not raise TypeError
    serialized = processor._serialize_job(job)

    # Verify we can deserialize payload
    deserialized_payload = json.loads(serialized["payload"])
    assert "timestamp" in deserialized_payload
    # Note: isoformat converts to string, deserializer in job_processor currently uses json.loads
    # which returns strings. It doesn't auto-convert back to datetime unless we custom deserialize.
    # The current code in job_processor.py _deserialize_job uses json.loads(data["payload"]).
    # So we expect strings.
    assert isinstance(deserialized_payload["timestamp"], str)
