import logging
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_service_key: str = ""
    gemini_api_key: str = ""
    resend_api_key: str = ""
    sentry_dsn: str = ""

    # Nowy standard Pydantic V2
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

def get_settings() -> Settings:
    return Settings()

def setup_monitoring():
    """Inicjalizuje Sentry wg sekcji 12.1 planu, jesli podano DSN."""
    settings = get_settings()
    if settings.sentry_dsn:
        try:
            import sentry_sdk
            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                traces_sample_rate=1.0,
            )
            print("Monitoring Sentry: Włączony")
        except ImportError:
            print("Monitoring Sentry: Błąd - brak pakietu sentry-sdk")
    else:
        print("Monitoring Sentry: Wyłączony (brak SENTRY_DSN w .env)")

if __name__ == "__main__":
    print("Test wczytywania konfiguracji i Sentry...")
    settings = get_settings()
    print(f"SUPABASE_URL obecny: {bool(settings.supabase_url)}")
    print(f"GEMINI_API_KEY obecny: {bool(settings.gemini_api_key)}")
    setup_monitoring()