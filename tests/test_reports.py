from datetime import datetime

import pytest

from app import create_app
from config import TestConfig


@pytest.fixture
def client():
    app = create_app(TestConfig)
    with app.test_client() as client:
        yield client


def test_reports_page_loads(client, mock_mysql):
    """
    Testa se a página de relatórios carrega com dados mockados.
    """
    mock_sessions = [
        {
            "id": 1,
            "start_time": datetime(2025, 8, 20, 10, 0),
            "end_time": datetime(2025, 8, 20, 11, 0),
            "total_minutes": 60,
            "demands_worked": "Demanda A",
            "work_descriptions": "Fiz X e Y",
        },
    ]
    mock_mysql.connection.cursor.return_value.fetchall.return_value = mock_sessions

    response = client.get("/reports/")
    assert response.status_code == 200
    assert (
        b"Relat\xc3\xb3rio de Horas Trabalhadas" in response.data
    )  # Relatório de Horas Trabalhadas
    assert b"Demanda A" in response.data
    assert b"Fiz X e Y" in response.data


def test_reports_page_with_filter(client, mock_mysql):
    """
    Testa se a página de relatórios funciona com filtros de data.
    """
    client.get("/reports/?start_date=2025-08-01&end_date=2025-08-31")

    # Verifica se a consulta SQL foi chamada com os parâmetros de filtro corretos
    cursor_mock = mock_mysql.connection.cursor.return_value
    args = cursor_mock.execute.call_args
    query = args[0][0]  # O primeiro argumento da chamada (a string da query)
    params = args[0][1]  # O segundo argumento da chamada (a tupla de parâmetros)

    assert "ws.start_time >= %s" in query
    assert "ws.end_time <= %s" in query
    assert params == ("2025-08-01", "2025-08-31 23:59:59")


def test_export_report(client, mock_mysql):
    """
    Testa a funcionalidade de exportar o relatório para Excel.
    """
    mock_data = [
        {
            "start_time": datetime(2025, 8, 20, 10, 0),
            "end_time": datetime(2025, 8, 20, 11, 0),
            "total_minutes": 60,
            "demand_title": "Demanda A",
            "minutes_spent": 60,
            "description": "Descrição A",
        },
    ]
    mock_mysql.connection.cursor.return_value.fetchall.return_value = mock_data

    response = client.post(
        "/reports/export", data={"start_date": "2025-08-01", "end_date": "2025-08-31"}
    )

    assert response.status_code == 200
    assert (
        response.mimetype
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "attachment" in response.headers["Content-Disposition"]
    assert ".xlsx" in response.headers["Content-Disposition"]
