from app.core.config import Settings


def test_cors_origin_list_splits_and_strips_comma_separated_origins() -> None:
    settings = Settings(cors_origins="http://localhost:3000, https://example.com ,")
    assert settings.cors_origin_list == ["http://localhost:3000", "https://example.com"]


def test_cors_origin_list_defaults_to_local_dev_frontend() -> None:
    settings = Settings()
    assert settings.cors_origin_list == ["http://localhost:3000"]
