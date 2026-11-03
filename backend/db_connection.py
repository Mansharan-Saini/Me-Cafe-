"""Create a small Oracle connection pool from the local environment."""

import os

import oracledb


def create_pool() -> oracledb.ConnectionPool:
    """Make sure all database credentials come from environment variables."""
    user = os.getenv("ORACLE_USER")
    password = os.getenv("ORACLE_PASSWORD")
    dsn = os.getenv("ORACLE_DSN")
    if not user or not password or not dsn:
        raise RuntimeError("Set ORACLE_USER, ORACLE_PASSWORD, and ORACLE_DSN in .env.")

    return oracledb.create_pool(
        user=user,
        password=password,
        dsn=dsn,
        min=int(os.getenv("ORACLE_POOL_MIN", "1")),
        max=int(os.getenv("ORACLE_POOL_MAX", "5")),
        increment=int(os.getenv("ORACLE_POOL_INCREMENT", "1")),
    )
