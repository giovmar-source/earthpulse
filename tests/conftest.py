import pytest


@pytest.fixture(autouse=True)
def _isolated_usage_budget(tmp_path, monkeypatch):
    """I test non toccano il contatore mensile reale delle richieste."""
    from src import usage_budget
    monkeypatch.setattr(usage_budget, "PATH", tmp_path / "usage.json")
