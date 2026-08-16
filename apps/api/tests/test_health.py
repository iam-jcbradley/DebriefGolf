from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.db.session import get_session


def test_health_returns_ok_with_no_db_dependency(client: TestClient) -> None:
    """No `session` override needed here at all — that's the point: a
    Postgres outage can't affect this endpoint's answer."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


class TestReady:
    def test_returns_ok_when_the_database_answers(self, client: TestClient) -> None:
        response = client.get("/api/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "db": "connected"}

    def test_returns_503_when_the_database_is_unreachable(self, client: TestClient) -> None:
        class _BrokenSession:
            def execute(self, *args, **kwargs):
                raise OperationalError("SELECT 1", {}, Exception("connection refused"))

        def _override():
            yield _BrokenSession()

        client.app.dependency_overrides[get_session] = _override

        response = client.get("/api/ready")

        assert response.status_code == 503
