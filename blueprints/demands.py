# blueprints/demands.py
import traceback

import boto3
import MySQLdb.cursors
from botocore.exceptions import NoCredentialsError
from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.utils import secure_filename

from extensions import mysql

s3_client = boto3.client("s3")

demands_bp = Blueprint("demands", __name__)


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in current_app.config["ALLOWED_EXTENSIONS"]
    )


@demands_bp.route("/")
def dashboard():
    view = request.args.get("view", "prioritize")  # 'prioritize' or 'all'
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    query_base = "SELECT id, title, status, created_at, priority, executed_hours, estimated_hours FROM demands"

    if view == "prioritize":
        query = f"{query_base} WHERE status IN ('Em Fila', 'Em Execução') ORDER BY priority ASC, created_at ASC"
    else:  # 'all'
        query = f"{query_base} ORDER BY created_at DESC"

    cur.execute(query)
    demands = cur.fetchall()
    cur.close()

    return render_template(
        "pages/demands/dashboard.html", demands=demands, current_view=view
    )


@demands_bp.route("/<int:demand_id>")
def detail(demand_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if demand_id == 0:  # Indicates a new demand
        demand = None
        attachments = []
        work_history = []
    else:
        cur.execute("SELECT * FROM demands WHERE id = %s", (demand_id,))
        demand = cur.fetchone()

        if not demand:
            flash("Demanda não encontrada.", "danger")
            return redirect(url_for("demands.dashboard"))

        cur.execute(
            "SELECT id, filename, filepath FROM attachments WHERE demand_id = %s",
            (demand_id,),
        )
        attachments = cur.fetchall()

        cur.execute(
            """
            SELECT wl.*, ws.start_time, ws.end_time 
            FROM work_logs wl
            JOIN work_sessions ws ON wl.work_session_id = ws.id
            WHERE wl.demand_id = %s
            ORDER BY ws.start_time DESC
        """,
            (demand_id,),
        )
        work_history = cur.fetchall()

    cur.close()

    return render_template(
        "pages/demands/detail.html",
        demand=demand,
        attachments=attachments,
        work_history=work_history,
    )


@demands_bp.route("/save", methods=["POST"])
def save_demand():
    print("Estou na rota save_demand")
    demand_id = request.form.get("demand_id")
    title = request.form.get("title")
    description = request.form.get("description")
    status = request.form.get("status")
    estimated_hours = request.form.get("estimated_hours") or None

    if not title or not status:
        flash("Título e Status são campos obrigatórios.", "danger")
        return redirect(url_for("demands.dashboard"))

    conn = mysql.connection
    cur = conn.cursor(MySQLdb.cursors.DictCursor)

    try:
        print("Tentando salvar a demanda...")
        if demand_id and demand_id != "0":  # Update existing demand
            print(f"Atualizando demanda com ID: {demand_id}")
            cur.execute(
                """
                UPDATE demands SET title=%s, description=%s, status=%s, estimated_hours=%s, updated_at=NOW()
                WHERE id=%s
            """,
                (title, description, status, estimated_hours, demand_id),
            )
            flash("Demanda atualizada com sucesso!", "success")
            redirect_url = url_for("demands.detail", demand_id=demand_id)
        else:  # Create new demand
            print("Criando uma nova demanda...")
            cur.execute("SELECT COALESCE(MAX(priority), -1) AS max_p FROM demands")
            result = cur.fetchone()
            max_priority = result["max_p"]
            cur.execute(
                """
                INSERT INTO demands (title, description, status, estimated_hours, priority)
                VALUES (%s, %s, %s, %s, %s)
            """,
                (title, description, status, estimated_hours, max_priority + 1),
            )
            demand_id = cur.lastrowid
            flash("Demanda criada! Agora, defina sua prioridade.", "info")
            redirect_url = url_for(
                "demands.prioritize", new_demand_id=demand_id
            )  # Redirect to prioritization

        if "attachments" in request.files:
            files_to_upload = request.files.getlist("attachments")
            for file in files_to_upload:
                if file and file.filename != "" and allowed_file(file.filename):
                    filename = secure_filename(file.filename)

                    try:
                        s3_client.upload_fileobj(
                            file,
                            current_app.config["S3_BUCKET"],
                            f"demands/{demand_id}/{filename}",
                        )
                        file_url = f"{current_app.config['S3_LOCATION']}demands/{demand_id}/{filename}"
                        # Salvar file_url no banco
                        cur.execute(
                            "INSERT INTO attachments (demand_id, filename, filepath) VALUES (%s, %s, %s)",
                            (demand_id, filename, file_url),  # Salva a URL
                        )
                    except NoCredentialsError:
                        flash("Credenciais AWS não configuradas no servidor.", "danger")
                    except Exception as e:
                        flash(f"Erro ao enviar arquivo para o S3: {e}", "danger")

        conn.commit()
    except Exception as e:
        conn.rollback()

        # ==========================================================
        # == MODIFICAÇÃO PARA DEBUGGING - IMPRIMA O ERRO COMPLETO ==
        # ==========================================================
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!!!!!!!!!!!!!  ERRO CAPTURADO EM SAVE_DEMAND !!!!!!!!!!!!!!")
        print(f"TIPO DE ERRO: {type(e)}")
        print(f"MENSAGEM: {e}")
        traceback.print_exc()  # Isso imprime o stack trace completo no terminal
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

        flash(f"Erro ao salvar demanda: {e}", "danger")
        redirect_url = url_for("demands.dashboard")
    finally:
        cur.close()

    return redirect(redirect_url)


@demands_bp.route("/prioritize/<int:new_demand_id>")
def prioritize(new_demand_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    query = "SELECT id, title, status, priority FROM demands WHERE status IN ('Em Fila', 'Em Execução') ORDER BY priority ASC, created_at ASC"
    cur.execute(query)
    demands = cur.fetchall()
    cur.close()

    return render_template(
        "pages/demands/prioritize.html", demands=demands, new_demand_id=new_demand_id
    )


@demands_bp.route("/attachment/<int:attachment_id>")
def download_attachment(attachment_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute(
        "SELECT filename, filepath FROM attachments WHERE id = %s", (attachment_id,)
    )
    attachment = cur.fetchone()
    cur.close()

    if not attachment:
        return "Arquivo não encontrado", 404

    # --- MODIFICAÇÃO PRINCIPAL AQUI ---
    try:
        bucket_name = current_app.config["S3_BUCKET"]

        # Extrai o object_key da URL completa salva no banco
        # Ex: https://bucket-name.s3.amazonaws.com/demands/1/file.pdf -> demands/1/file.pdf
        object_key = attachment["filepath"].split(f"{bucket_name}.s3.amazonaws.com/")[1]

        # Gera uma URL segura e temporária para download
        presigned_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": object_key},
            ExpiresIn=300,  # A URL expira em 5 minutos (300 segundos)
        )

        return redirect(presigned_url)

    except Exception as e:
        flash(f"Erro ao gerar link de download: {e}", "danger")
        # Idealmente, redirecionar para a página de detalhes da demanda
        return redirect(url_for("demands.dashboard"))


@demands_bp.route("/update_priorities", methods=["POST"])
def update_priorities():
    data = request.get_json()
    ordered_ids = data.get("ordered_ids")

    if not ordered_ids or not isinstance(ordered_ids, list):
        return jsonify(status="error", message="Lista de IDs inválida."), 400

    conn = mysql.connection
    cur = conn.cursor()
    try:
        # Update priority for each demand in a single transaction
        for index, demand_id in enumerate(ordered_ids):
            cur.execute(
                "UPDATE demands SET priority = %s WHERE id = %s", (index, demand_id)
            )
        conn.commit()
        return jsonify(status="success", message="Prioridades atualizadas."), 200
    except Exception as e:
        conn.rollback()
        return (
            jsonify(status="error", message=f"Erro ao atualizar prioridades: {e}"),
            500,
        )
    finally:
        cur.close()
