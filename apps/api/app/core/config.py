from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# The value shipped in .env.example. Fine for local development, fatal
# anywhere else — it signs both the Garmin OAuth state token and the login
# session cookie, so anyone who knows it can mint a session for any account.
DEFAULT_SECRET_KEY = "dev-insecure-secret-change-me"


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

    # Signs the login session cookie (app/core/security.py) and the Garmin
    # OAuth `state` token (app/services/garmin_oauth.py), and derives the
    # encryption key for stored Garmin tokens. MUST be overridden in any real
    # deployment — see the validator below, which enforces that.
    secret_key: str = DEFAULT_SECRET_KEY
    frontend_url: str = "http://localhost:3000"

    # --- Login sessions (Phase 10) ---
    session_cookie_name: str = "debrief_session"
    session_ttl_days: int = 30

    @property
    def session_ttl_seconds(self) -> int:
        return self.session_ttl_days * 24 * 60 * 60

    @property
    def is_development(self) -> bool:
        return self.env == "development"

    @property
    def session_cookie_secure(self) -> bool:
        """HTTPS-only outside development. Local dev runs on plain http://
        localhost, where a Secure cookie would simply never be sent."""
        return not self.is_development

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

    @model_validator(mode="after")
    def _reject_default_secret_outside_development(self) -> "Settings":
        """Refuse to start rather than run a deployment anyone can forge a
        session for. Deliberately a hard failure at import time: a warning
        in a log nobody reads is how this ships to production by accident."""
        if not self.is_development and self.secret_key == DEFAULT_SECRET_KEY:
            raise ValueError(
                f"SECRET_KEY is still the example value from .env.example, and ENV is "
                f"{self.env!r}. It signs login session cookies and the Garmin OAuth state "
                "token — anyone who knows it can mint a session for any account. Set "
                "SECRET_KEY to a real random secret, e.g. `python -c \"import secrets; "
                'print(secrets.token_urlsafe(32))"`.'
            )
        return self


settings = Settings()
