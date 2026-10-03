import pytest

from src import usage_budget


def test_budget_counts_and_stops(tmp_path, monkeypatch):
    monkeypatch.setattr(usage_budget, "PATH", tmp_path / "usage.json")
    monkeypatch.setenv("CDSE_MONTHLY_BUDGET", "3")
    assert usage_budget.spend("cdse") == 1
    assert usage_budget.spend("cdse", 2) == 3
    with pytest.raises(usage_budget.BudgetExceeded):
        usage_budget.spend("cdse")
    report = usage_budget.report()
    assert report["services"]["cdse"] == {"used": 3, "budget": 3}


def test_new_month_resets(tmp_path, monkeypatch):
    monkeypatch.setattr(usage_budget, "PATH", tmp_path / "usage.json")
    (tmp_path / "usage.json").write_text('{"month": "2000-01", "counts": {"cdse": 9999}}')
    assert usage_budget.spend("cdse") == 1
