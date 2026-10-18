from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aura_api.main import create_app


@pytest.fixture()
def client(tmp_path: Path):
    app = create_app(f"sqlite:///{tmp_path / 'test.db'}")
    with TestClient(app) as http:
        yield http
    app.state.engine.dispose()
