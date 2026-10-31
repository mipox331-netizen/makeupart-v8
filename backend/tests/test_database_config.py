from app.core.config import Settings


def test_supabase_database_url_takes_precedence_over_legacy_render_url():
    settings = Settings(
        _env_file=None,
        SECRET_KEY="test-secret-key-for-database-config",
        DATABASE_URL="postgresql://legacy-render-host/makeupart",
        SUPABASE_DB_URL="postgresql://supabase-host/makeupart",
    )

    assert settings.DATABASE_URL == "postgresql://supabase-host/makeupart"


def test_legacy_database_url_remains_supported_without_supabase_override():
    settings = Settings(
        _env_file=None,
        SECRET_KEY="test-secret-key-for-database-config",
        DATABASE_URL="sqlite://",
        SUPABASE_DB_URL="",
    )

    assert settings.DATABASE_URL == "sqlite://"
