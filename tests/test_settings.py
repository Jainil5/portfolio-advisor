"""Settings resolve data paths relative to the project root, not CWD."""

import importlib

from backend.config import settings


def test_data_root_defaults_under_project_root():
    assert settings.DATA_ROOT == str(settings.PROJECT_ROOT / "data")


def test_all_paths_derive_from_data_root(monkeypatch):
    monkeypatch.setenv("STOCK_DATA_ROOT", "/tmp/custom_pa_data")
    reloaded = importlib.reload(settings)

    assert reloaded.DATA_ROOT == "/tmp/custom_pa_data"
    assert reloaded.FEATURES_FILE == "/tmp/custom_pa_data/silver/features.csv"
    assert reloaded.STOCKS_FILE == "/tmp/custom_pa_data/bronze/stocks.csv"
    assert reloaded.PRICE_DIR == "/tmp/custom_pa_data/bronze/prices"

    # restore module-level constants for other tests
    monkeypatch.delenv("STOCK_DATA_ROOT", raising=False)
    importlib.reload(settings)
