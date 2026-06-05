import pytest


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    import services.db
    monkeypatch.setattr(services.db, "DB_PATH", str(tmp_path / "test.db"))
