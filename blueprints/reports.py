# blueprints/reports.py
from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
import MySQLdb.cursors
from extensions import mysql
import pandas as pd
import io
from datetime import datetime

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/")
def index():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    query = """
        SELECT 
            ws.id,
            ws.start_time,
            ws.end_time,
            ws.total_minutes,
            GROUP_CONCAT(d.title SEPARATOR '; ') as demands_worked,
            GROUP_CONCAT(wl.description SEPARATOR '; ') as work_descriptions
        FROM work_sessions ws
        JOIN work_logs wl ON ws.id = wl.work_session_id
        JOIN demands d ON wl.demand_id = d.id
    """
    params = []

    where_clauses = []
    if start_date:
        where_clauses.append("ws.start_time >= %s")
        params.append(start_date)
    if end_date:
        where_clauses.append("ws.end_time <= %s")
        params.append(end_date + " 23:59:59")

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    query += " GROUP BY ws.id ORDER BY ws.start_time DESC"

    cur.execute(query, tuple(params))
    work_sessions = cur.fetchall()
    cur.close()

    return render_template(
        "pages/reports/index.html",
        sessions=work_sessions,
        start_date=start_date,
        end_date=end_date,
    )


@reports_bp.route("/export", methods=["POST"])
def export_report():
    start_date = request.form.get("start_date")
    end_date = request.form.get("end_date")

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    query = """
        SELECT 
            ws.start_time,
            ws.end_time,
            ws.total_minutes,
            d.title AS demand_title,
            wl.minutes_spent,
            wl.description
        FROM work_sessions ws
        JOIN work_logs wl ON ws.id = wl.work_session_id
        JOIN demands d ON wl.demand_id = d.id
    """
    params = []

    where_clauses = []
    if start_date:
        where_clauses.append("ws.start_time >= %s")
        params.append(start_date)
    if end_date:
        where_clauses.append("ws.end_time <= %s")
        params.append(end_date + " 23:59:59")

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    query += " ORDER BY ws.start_time ASC, d.title ASC"

    cur.execute(query, tuple(params))
    data = cur.fetchall()
    cur.close()

    if not data:
        flash("Nenhum dado encontrado para exportar no período selecionado.", "warning")
        return redirect(url_for("reports.index"))

    # Create a pandas DataFrame
    df = pd.DataFrame(data)

    # Format data for Excel
    df.rename(
        columns={
            "start_time": "Início da Sessão",
            "end_time": "Fim da Sessão",
            "total_minutes": "Duração Total da Sessão (min)",
            "demand_title": "Demanda",
            "minutes_spent": "Minutos Alocados na Demanda",
            "description": "Descrição do Trabalho",
        },
        inplace=True,
    )

    df["Início da Sessão"] = pd.to_datetime(df["Início da Sessão"]).dt.strftime(
        "%d/%m/%Y %H:%M"
    )
    df["Fim da Sessão"] = pd.to_datetime(df["Fim da Sessão"]).dt.strftime(
        "%d/%m/%Y %H:%M"
    )

    # Create an in-memory Excel file
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="HorasTrabalhadas")

    output.seek(0)

    filename = f"Relatorio_Horas_{datetime.now().strftime('%Y%m%d')}.xlsx"

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )
