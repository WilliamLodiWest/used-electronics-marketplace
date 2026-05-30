"""Ponto de entrada WSGI para produção (Render, Railway, etc.)."""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROUTES_DIR = os.path.join(BASE_DIR, "routes")

for path in (BASE_DIR, ROUTES_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

import app as flask_app_module  # noqa: E402

app = flask_app_module.app
