"""Modal deployment entrypoint for the MakeUpArt V8 FastAPI backend.

The application image is built from the existing backend/Dockerfile so the
same Python/MediaPipe/InsightFace runtime is used in CI and production.
"""

import modal

APP_NAME = "makeupart-v8-api"

image = modal.Image.from_dockerfile(
    "Dockerfile",
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

modal_app = modal.App(APP_NAME)

production_secret = modal.Secret.from_name("makeupart-v8-production")


@modal_app.function(
    image=image,
    secrets=[production_secret],
    timeout=900,
)
def migrate():
    from alembic import command
    from alembic.config import Config

    command.upgrade(Config("/app/alembic.ini"), "head")


@modal_app.function(
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
