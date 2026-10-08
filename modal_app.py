"""Modal deployment entrypoint for the MakeUpArt V8 FastAPI backend.

The application image is built from the existing backend/Dockerfile so the
same Python/MediaPipe/InsightFace runtime is used in CI and production.
"""

import modal

APP_NAME = "makeupart-v8-api"

image = modal.Image.from_dockerfile(
    "backend/Dockerfile",
    context_dir="backend",
)

media_volume = modal.Volume.from_name(
    "makeupart-v8-media",
    create_if_missing=True,
)

insightface_volume = modal.Volume.from_name(
    "makeupart-v8-insightface",
    create_if_missing=True,
)

app = modal.App(APP_NAME)

production_secret = modal.Secret.from_name("makeupart-v8-production")


@app.function(
    image=image,
    secrets=[production_secret],
    timeout=900,
)
def migrate():
    from alembic import command
    from alembic.config import Config
    from alembic.migration import MigrationContext
    from alembic.script import ScriptDirectory

    from app.db.session import engine

    alembic_config = Config('/app/alembic.ini')
    command.upgrade(alembic_config, 'head')

    script = ScriptDirectory.from_config(alembic_config)
    heads = script.get_heads()
    with engine.connect() as connection:
        current = MigrationContext.configure(connection).get_current_revision()

    if len(heads) != 1 or current != heads[0]:
        raise RuntimeError(f'Migration head mismatch: expected {heads}, current {current!r}')

    print(f'Migration head confirmed: {current}')


@app.function(
    image=image,
    secrets=[production_secret],
    volumes={
        "/app/media": media_volume,
        "/home/app/.insightface": insightface_volume,
    },
    cpu=2.0,
    memory=4096,
    timeout=1200,
)
@modal.asgi_app()
def fastapi_app():
    from app.main import app

    return app
