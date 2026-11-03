"""Simple JSON endpoints that call Oracle SQL and PL/SQL."""

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import oracledb
from flask import Blueprint, current_app, jsonify, request


api = Blueprint("api", __name__, url_prefix="/api")


def _read(action: Any) -> Any:
    """Run a database operation and return its connection to the pool."""
    pool = current_app.config["ORACLE_POOL"]
    connection = pool.acquire()
    try:
        with connection.cursor() as cursor:
            return action(cursor)
    finally:
        pool.release(connection)


def _write(action: Any) -> Any:
    """Commit a successful database operation and roll back a failed one."""
    pool = current_app.config["ORACLE_POOL"]
    connection = pool.acquire()
    try:
        with connection.cursor() as cursor:
            result = action(cursor)
        connection.commit()
        return result
    except Exception:
        connection.rollback()
        raise
    finally:
        pool.release(connection)


def _rows(cursor: Any) -> list[dict[str, Any]]:
    names = [column[0].lower() for column in cursor.description]
    return [
        {
            name: _json_value(value)
            for name, value in zip(names, row)
        }
        for row in cursor.fetchall()
    ]


def _json_value(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _body() -> dict[str, Any]:
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise ValueError("Send a JSON object.")
    return value


def _required(data: dict[str, Any], key: str) -> Any:
    value = data.get(key)
    if value is None or value == "":
        raise ValueError(f"{key.replace('_', ' ').capitalize()} is required.")
    return value


def _number(value: Any, label: str, whole: bool = False) -> int | float:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{label} must be a number.")
    if not parsed.is_finite() or (whole and parsed != parsed.to_integral_value()):
        raise ValueError(f"{label} is invalid.")
    return int(parsed) if whole else float(parsed)


@api.get("/health")
def health() -> Any:
    return jsonify(_read(lambda cursor: _health(cursor)))


def _health(cursor: Any) -> dict[str, str]:
    cursor.execute("SELECT 'Oracle connection is ready' AS message FROM dual")
    return {"message": cursor.fetchone()[0]}


@api.get("/categories")
def categories() -> Any:
    return jsonify(_read(lambda cursor: _select(cursor, "SELECT category_id, category_name FROM categories ORDER BY category_name")))


@api.get("/users")
def users() -> Any:
    return jsonify(_read(lambda cursor: _select(cursor, "SELECT user_id, username, role_name FROM users ORDER BY user_id")))


@api.get("/reasons")
def reasons() -> Any:
    return jsonify(_read(lambda cursor: _select(cursor, "SELECT reason_id, reason_name FROM waste_reasons ORDER BY reason_name")))


def _select(cursor: Any, sql: str) -> list[dict[str, Any]]:
    cursor.execute(sql)
    return _rows(cursor)


@api.get("/dashboard")
def dashboard() -> Any:
    def query(cursor: Any) -> dict[str, Any]:
        cursor.execute(
            """SELECT COUNT(*) AS product_count, NVL(SUM(quantity), 0) AS stock_count,
                      SUM(CASE WHEN TRUNC(expiry_date) BETWEEN TRUNC(SYSDATE) AND TRUNC(SYSDATE)+7
                               THEN 1 ELSE 0 END) AS expiring_count,
                      SUM(CASE WHEN TRUNC(expiry_date)<TRUNC(SYSDATE) THEN 1 ELSE 0 END) AS expired_count
                 FROM food_items WHERE is_active='Y'"""
        )
        inventory = _rows(cursor)[0]
        cursor.execute(
            "SELECT COUNT(*) AS waste_count, NVL(SUM(estimated_loss),0) AS total_loss FROM food_waste_log"
        )
        waste = _rows(cursor)[0]
        return {**inventory, **waste}

    return jsonify(_read(query))


@api.get("/inventory")
def inventory() -> Any:
    search = request.args.get("search", "").strip()
    sql = """SELECT i.item_id, i.item_name, c.category_id, c.category_name,
                    i.quantity, i.unit, i.unit_price, i.expiry_date,
                    get_expiry_status(i.expiry_date) AS expiry_status
               FROM food_items i JOIN categories c ON c.category_id=i.category_id
              WHERE i.is_active='Y'
                AND (:search IS NULL OR UPPER(i.item_name) LIKE UPPER(:pattern))
              ORDER BY i.expiry_date"""

    def query(cursor: Any) -> list[dict[str, Any]]:
        cursor.execute(sql, search=search or None, pattern=f"%{search}%" if search else None)
        return _rows(cursor)

    return jsonify(_read(query))


@api.post("/inventory")
def add_inventory() -> Any:
    data = _body()
    fields = [
        str(_required(data, "item_name")).strip(),
        _number(_required(data, "category_id"), "Category", True),
        _number(_required(data, "quantity"), "Quantity"),
        str(_required(data, "unit")).strip(),
        _number(_required(data, "unit_price"), "Unit price"),
        date.fromisoformat(str(_required(data, "expiry_date"))),
    ]
    if fields[2] < 0 or fields[4] <= 0 or not fields[0] or not fields[3]:
        raise ValueError("Name, unit, quantity, or price is invalid.")

    def insert(cursor: Any) -> dict[str, int]:
        item_id = cursor.var(oracledb.NUMBER)
        cursor.callproc("add_food_item", fields + [item_id])
        return {"item_id": int(item_id.getvalue())}

    return jsonify(_write(insert)), 201


@api.get("/alerts")
def alerts() -> Any:
    sql = """SELECT a.alert_id, a.item_id, i.item_name, a.alert_type, a.alert_date, a.status
               FROM expiry_alerts a JOIN food_items i ON i.item_id=a.item_id
              ORDER BY CASE a.status WHEN 'OPEN' THEN 1 WHEN 'ACKNOWLEDGED' THEN 2 ELSE 3 END,
                       a.alert_date DESC"""
    return jsonify(_read(lambda cursor: _select(cursor, sql)))


@api.post("/alerts/check")
def check_alerts() -> Any:
    def run(cursor: Any) -> dict[str, bool]:
        cursor.callproc("check_food_expiry")
        return {"checked": True}

    return jsonify(_write(run))


@api.post("/waste")
def record_waste() -> Any:
    data = _body()
    fields = [
        _number(_required(data, "item_id"), "Food item", True),
        _number(_required(data, "quantity"), "Waste quantity"),
        _number(_required(data, "reason_id"), "Waste reason", True),
        _number(_required(data, "user_id"), "User", True),
        str(data.get("remarks", ""))[:250],
    ]
    if fields[1] <= 0:
        raise ValueError("Waste quantity must be greater than zero.")

    def insert(cursor: Any) -> dict[str, int]:
        waste_id = cursor.var(oracledb.NUMBER)
        cursor.callproc("record_food_waste", fields + [waste_id])
        return {"waste_id": int(waste_id.getvalue())}

    return jsonify(_write(insert)), 201


@api.get("/waste")
def waste_history() -> Any:
    sql = """SELECT w.waste_id, i.item_name, r.reason_name,
                    w.quantity_wasted, i.unit, w.estimated_loss, w.waste_date, w.remarks
               FROM food_waste_log w JOIN food_items i ON i.item_id=w.item_id
               JOIN waste_reasons r ON r.reason_id=w.reason_id
              ORDER BY w.waste_date DESC"""
    return jsonify(_read(lambda cursor: _select(cursor, sql)))


def register_routes(app: Any) -> None:
    """Attach the routes and friendly errors to the web application."""
    app.register_blueprint(api)

    @app.errorhandler(ValueError)
    def input_error(error: ValueError) -> Any:
        return jsonify({"error": str(error)}), 400

    @app.errorhandler(oracledb.DatabaseError)
    def database_error(error: Exception) -> Any:
        app.logger.exception("Oracle operation failed.")
        details = error.args[0] if error.args else None
        message = getattr(details, "message", "The Oracle database could not complete the request.")
        if str(message).strip().startswith("ORA-20"):
            return jsonify({"error": str(message).strip()}), 400
        return jsonify({"error": "Database request failed. Check the Oracle connection and setup script."}), 500
