import json
from datetime import datetime, timedelta

import pytest

from app import create_app
from config import TestConfig


@pytest.fixture
def client():
    app = create_app(TestConfig)
    with app.test_client() as client:
        yield client


def test_tracker_page_loads(client, mock_mysql):
    """
    Testa se a página do tracker carrega com as demandas pendentes.
    """
    mock_demands = [
        {"id": 1, "title": "Demanda Pendente 1"},
        {"id": 2, "title": "Demanda Pendente 2"},
    ]
    mock_mysql.connection.cursor.return_value.fetchall.return_value = mock_demands

    response = client.get("/tracker/")
    assert response.status_code == 200
    assert b"Registro de Horas" in response.data
    assert b"Demanda Pendente 1" in response.data
    assert b"Demanda Pendente 2" in response.data


def test_log_work_success(client, mock_mysql):
    """
    Testa o registro de uma sessão de trabalho com sucesso.
    """
    start_time = datetime.utcnow()
    end_time = start_time + timedelta(minutes=60)

    payload = {
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "total_minutes": 60,
        "allocations": [
            {
                "demand_id": "1",
                "minutes_spent": 40,
                "description": "Trabalhei na demanda 1",
                "new_status": "Concluída",
            },
            {
                "demand_id": "2",
                "minutes_spent": 20,
                "description": "Trabalhei na demanda 2",
                "new_status": None,  # CORREÇÃO: Mudar de '' para None para simular o comportamento do JS
            },
        ],
    }

    # Mock para o lastrowid da sessão de trabalho
    mock_mysql.connection.cursor.return_value.lastrowid = 99

    response = client.post(
        "/tracker/log_work", data=json.dumps(payload), content_type="application/json"
    )

    assert response.status_code == 201
    json_data = response.get_json()
    assert json_data["status"] == "success"

    cursor_mock = mock_mysql.connection.cursor.return_value

    # Verifica a inserção na tabela work_sessions
    cursor_mock.execute.assert_any_call(
        "INSERT INTO work_sessions (start_time, end_time, total_minutes) VALUES (%s, %s, %s)",
        (start_time, end_time, 60),
    )

    # Verifica as inserções na tabela work_logs
    cursor_mock.execute.assert_any_call(
        "INSERT INTO work_logs (work_session_id, demand_id, minutes_spent, description, status_changed_to) VALUES (%s, %s, %s, %s, %s)",
        (99, "1", 40, "Trabalhei na demanda 1", "Concluída"),
    )
    cursor_mock.execute.assert_any_call(
        "INSERT INTO work_logs (work_session_id, demand_id, minutes_spent, description, status_changed_to) VALUES (%s, %s, %s, %s, %s)",
        (99, "2", 20, "Trabalhei na demanda 2", None),
    )

    # Verifica os updates na tabela demands
    hours_spent_1 = 40.0 / 60.0
    cursor_mock.execute.assert_any_call(
        "UPDATE demands SET executed_hours = executed_hours + %s WHERE id = %s",
        (hours_spent_1, "1"),
    )
    cursor_mock.execute.assert_any_call(
        "UPDATE demands SET status = %s WHERE id = %s", ("Concluída", "1")
    )

    mock_mysql.connection.commit.assert_called_once()


def test_log_work_incomplete_data(client):
    """
    Testa a falha no registro de trabalho com dados incompletos.
    """
    payload = {
        "start_time": datetime.utcnow().isoformat(),
        # Faltando end_time, total_minutes, allocations
    }

    response = client.post(
        "/tracker/log_work", data=json.dumps(payload), content_type="application/json"
    )

    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data["status"] == "error"
    assert json_data["message"] == "Dados incompletos."
