from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "development"
    database_url: str = "postgresql+psycopg://debrief:debrief@localhost:5432/debrief_golf"
    # Comma-separated origins allowed to call the API from a browser (the
    # Next.js dev server by default — see apps/web's NEXT_PUBLIC_API_URL).
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    # Signs the OAuth `state` token (app/services/garmin_oauth.py) so it can
    # carry data through the Garmin redirect without server-side session
    # storage. MUST be overridden in any real deployment.
    secret_key: str = "dev-insecure-secret-change-me"
    frontend_url: str = "http://localhost:3000"

    # --- Garmin Connect OAuth 2.0 (PRD §4.1, §9.2) ---
    # client_id/secret and the exact authorize/token endpoint URLs come from
    # the Garmin Developer Portal for a registered app — left blank by
    # default rather than guessed, since a wrong-but-plausible-looking URL
    # here is worse than a clear "not configured" error. See .env.example.
    garmin_client_id: str = ""
    garmin_client_secret: str = ""
    garmin_redirect_uri: str = "http://localhost:8000/api/auth/garmin/callback"
    garmin_authorize_url: str = ""
    garmin_token_url: str = ""


settings = Settings()
