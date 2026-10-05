"""Import smoke test: every package module must import cleanly."""

import importlib

import pytest

MODULES = [
    "backend",
    "backend.config",
    "backend.config.settings",
    "backend.data",
    "backend.data.repository",
    "backend.utils.market_data",
    "backend.services.user_transactions",
    "backend.pipelines.ingest",
    "backend.pipelines.features",
    "backend.pipelines.recommendations",
    "backend.pipelines.update_pipeline",
    "backend.analytics.predict",
]


@pytest.mark.parametrize("module", MODULES)
def test_module_imports(module):
    importlib.import_module(module)


def test_heavy_modules_are_lazy():
    """Importing the spark pipeline module must not start a JVM."""
    pytest.importorskip("pyspark")
    import backend.pipelines.features_spark as fs

    assert fs._spark is None
