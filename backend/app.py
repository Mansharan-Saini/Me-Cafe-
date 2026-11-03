"""Start the small Flask application for the Oracle food mini-project."""

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template

from db_connection import create_pool
from routes import register_routes


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

app = Flask(
    __name__,
    template_folder=PROJECT_ROOT / "frontend" / "templates",
    static_folder=PROJECT_ROOT / "frontend" / "static",
)
app.config["ORACLE_POOL"] = create_pool()
register_routes(app)


@app.get("/")
def home() -> str:
    """Show the inventory and waste dashboard."""
    return render_template("index.html")


if __name__ == "__main__":
    app.run(
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=False,
    )
