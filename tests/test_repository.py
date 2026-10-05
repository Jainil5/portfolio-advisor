"""Repository layer round-trip and caching against tmp fixtures (no real data)."""

import pandas as pd
import pytest

from backend.data import repository


@pytest.fixture(autouse=True)
def clear_cache():
    repository._csv_cache.clear()
    yield
    repository._csv_cache.clear()


def test_write_then_read_round_trip(tmp_path):
    path = str(tmp_path / "out.csv")
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})

    repository.write_csv(df, path)
    loaded = repository.read_csv_cached(path)

    assert list(loaded.columns) == ["a", "b"]
    assert len(loaded) == 2


def test_read_csv_cached_serves_cache_until_mtime_changes(tmp_path):
    path = str(tmp_path / "data.csv")
    repository.write_csv(pd.DataFrame({"a": [1]}), path)

    first = repository.read_csv_cached(path)
    second = repository.read_csv_cached(path)
    assert first is second  # same cached object, no re-parse


def test_read_csv_safe_missing_returns_empty(tmp_path):
    result = repository.read_csv_safe(str(tmp_path / "nope.csv"))
    assert result.empty


def test_read_csv_cached_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        repository.read_csv_cached(str(tmp_path / "nope.csv"))


def test_column_names_are_stripped(tmp_path):
    path = str(tmp_path / "spaced.csv")
    pd.DataFrame({" a ": [1], "b ": [2]}).to_csv(path, index=False)

    loaded = repository.read_csv_cached(path)
    assert list(loaded.columns) == ["a", "b"]
