import pytest
from pydantic import ValidationError

import config_schema


def _entry(**kw):
    return {"id": "a", "title": "A", "schedule": "0 6 * * *", "goosepaper_config": "a.json",
            "remarkable_folder": "/", **kw}


def test_local_editions_ignores_prefix_titles_and_glob_chars(tmp_path):
    for name in ["Raetselheft 2026-01-01.pdf", "Raetselheft Kids 2026-01-01.pdf", "A[1] 2026-01-01.pdf"]:
        (tmp_path / name).touch()
    assert [p.name for p in config_schema.local_editions("Raetselheft", tmp_path)] == ["Raetselheft 2026-01-01.pdf"]
    assert [p.name for p in config_schema.local_editions("A[1]", tmp_path)] == ["A[1] 2026-01-01.pdf"]


def test_invalid_cron_rejected():
    with pytest.raises(ValidationError):
        config_schema.AddonConfig.model_validate({"newspapers": [_entry(schedule="nonsense")]})


def test_duplicate_ids_rejected():
    with pytest.raises(ValidationError):
        config_schema.AddonConfig.model_validate({"newspapers": [_entry(), _entry()]})
