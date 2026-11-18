import json
from datetime import datetime

from ddoc.core.version_service import VersionService
from ddoc.core.metadata_service import MetadataService


def _iso_now() -> str:
    return datetime.now().isoformat()


def test_version_alias_roundtrip(tmp_path):
    project_root = tmp_path
    version_service = VersionService(str(project_root))

    versions_data = {
        "sample": {
            "versions": {
                "v1.0": {
                    "hash": "hash123",
                    "timestamp": _iso_now(),
                    "message": "initial",
                    "git_commit": None,
                    "git_tag": None,
                    "restore_strategy": "dvc-only",
                    "metadata": {}
                }
            },
            "current_version": "v1.0",
            "latest_hash": "hash123",
            "aliases": {}
        }
    }

    version_service.dataset_versions_file.write_text(json.dumps(versions_data, indent=2), encoding="utf-8")

    renamed = version_service.set_dataset_version_alias("sample", "v1.0", "baseline")
    assert renamed["success"]
    assert renamed["alias"] == "baseline"

    versions = version_service.list_dataset_versions("sample")
    assert versions[0]["alias"] == "baseline"

    resolved = version_service.get_dataset_version_by_alias("sample", "baseline")
    assert resolved == "v1.0"

    cleared = version_service.set_dataset_version_alias("sample", "v1.0", None)
    assert cleared["success"]
    assert cleared["alias"] is None
    assert version_service.get_dataset_version_by_alias("sample", "baseline") is None


def test_metadata_timeline_includes_alias(tmp_path):
    project_root = tmp_path
    metadata_service = MetadataService(str(project_root))

    dataset_id = "sample@v1.0"
    metadata_service.add_dataset(
        dataset_id=dataset_id,
        dataset_name="sample",
        version="v1.0",
        metadata={"hash": "hash123", "message": "init"}
    )

    metadata_service.update_dataset_alias(dataset_id, "baseline")

    metadata_service.add_analysis(
        analysis_id="analysis_1",
        analysis_name="EDA run",
        dataset_id=dataset_id,
        metadata={"summary": "ok"}
    )

    timeline = metadata_service.get_dataset_timeline("sample")

    assert len(timeline) == 2
    version_event = timeline[0]
    analysis_event = timeline[1]

    assert version_event["event_type"] == "version"
    assert version_event["alias"] == "baseline"

    assert analysis_event["event_type"] == "analysis"
    assert analysis_event["alias"] == "baseline"
    assert analysis_event["relationship"] == "generates"





