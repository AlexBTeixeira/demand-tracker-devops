# blueprints/tracker.py
from datetime import datetime

import MySQLdb.cursors
from flask import Blueprint, flash, jsonify, render_template, request

from extensions import mysql

tracker_bp = Blueprint("tracker", __name__)


@tracker_bp.route("/")
def index():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute(
        "SELECT id, title FROM demands WHERE status IN ('Em Fila', 'Em Execução') ORDER BY priority ASC"
    )
    pending_demands = cur.fetchall()
    cur.close()
    return render_template("pages/tracker/index.html", pending_demands=pending_demands)


@tracker_bp.route("/log_work", methods=["POST"])
def log_work():
    data = request.get_json()
    start_time_str = data.get("start_time")
    end_time_str = data.get("end_time")
    total_minutes = data.get("total_minutes")
    allocations = data.get("allocations")

    if not all([start_time_str, end_time_str, total_minutes, allocations]):
        return jsonify({"status": "error", "message": "Dados incompletos."}), 400

    # Lida com o formato 'Z' (Zulu time) enviado pelo JavaScript que o fromisoformat() não entende nativamente
    if start_time_str and start_time_str.endswith("Z"):
        start_time_str = start_time_str[:-1] + "+00:00"

    if end_time_str and end_time_str.endswith("Z"):
        end_time_str = end_time_str[:-1] + "+00:00"

    # --- FIM DA CORREÇÃO ---

    conn = mysql.connection
    cur = conn.cursor()

    try:

        start_time = datetime.fromisoformat(start_time_str)
        end_time = datetime.fromisoformat(end_time_str)
        # 1. Create the work session record
        cur.execute(
            "INSERT INTO work_sessions (start_time, end_time, total_minutes) VALUES (%s, %s, %s)",
            (start_time, end_time, total_minutes),
        )
        session_id = cur.lastrowid

        # 2. Iterate through allocations to create logs and update demands
        for alloc in allocations:
            demand_id = alloc.get("demand_id")
            minutes_spent = alloc.get("minutes_spent")
            description = alloc.get("description")
            new_status = alloc.get("new_status")

            if not all([demand_id, minutes_spent, description]):
                raise ValueError("Alocação de demanda com dados incompletos.")

            # Create work_log
            cur.execute(
                "INSERT INTO work_logs (work_session_id, demand_id, minutes_spent, description, status_changed_to) VALUES (%s, %s, %s, %s, %s)",
                (session_id, demand_id, minutes_spent, description, new_status),
            )

            # Update demand's executed_hours
            hours_spent = float(minutes_spent) / 60.0
            cur.execute(
                "UPDATE demands SET executed_hours = executed_hours + %s WHERE id = %s",
                (hours_spent, demand_id),
            )

            # Update demand's status if changed
            if new_status:
                cur.execute(
                    "UPDATE demands SET status = %s WHERE id = %s",
                    (new_status, demand_id),
                )

        conn.commit()
        flash("Sessão de trabalho registrada com sucesso!", "success")
        return jsonify({"status": "success", "message": "Log de trabalho salvo."}), 201

    except Exception as e:
        conn.rollback()
        flash(f"Erro ao registrar trabalho: {e}", "danger")
        return jsonify({"status": "error", "message": f"Erro no servidor: {e}"}), 500
    finally:
        cur.close()
