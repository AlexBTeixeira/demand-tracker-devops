import pytest
from app import create_app
from config import TestConfig
from datetime import datetime

@pytest.fixture
def client():
    app = create_app(TestConfig)
    with app.test_client() as client:
        yield client

def test_demands_dashboard_loads(client, mock_mysql):
    """
    Testa se o dashboard de demandas carrega com dados mockados.
    """
    # Mock dos dados que o banco de dados retornaria
    mock_demands = [
        {'id': 1, 'title': 'Demanda 1', 'status': 'Em Fila', 'created_at': datetime.now(), 'priority': 0, 'executed_hours': 10, 'estimated_hours': 20},
        {'id': 2, 'title': 'Demanda 2', 'status': 'Em Execução', 'created_at': datetime.now(), 'priority': 1, 'executed_hours': 5, 'estimated_hours': 15},
    ]
    mock_mysql.connection.cursor.return_value.fetchall.return_value = mock_demands

    response = client.get('/demands/')
    assert response.status_code == 200
    assert b"Painel de Demandas" in response.data
    assert b"Demanda 1" in response.data
    assert b"Demanda 2" in response.data

def test_new_demand_page_loads(client):
    """
    Testa se a página para criar uma nova demanda (detalhe com id 0) carrega.
    """
    response = client.get('/demands/0')
    assert response.status_code == 200
    assert b"Nova Demanda" in response.data

def test_save_new_demand(client, mock_mysql):
    """
    Testa o salvamento de uma nova demanda.
    """
    # Mock para a consulta que busca a prioridade máxima
    mock_mysql.connection.cursor.return_value.fetchone.return_value = {'max_p': 5}
    # Mock para o lastrowid retornado após a inserção
    mock_mysql.connection.cursor.return_value.lastrowid = 100

    response = client.post('/demands/save', data={
        'demand_id': '', # ID vazio para criação
        'title': 'Nova Demanda de Teste',
        'description': 'Descricao da nova demanda.',
        'status': 'Em Fila',
        'estimated_hours': '10'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Priorize a Nova Demanda" in response.data # Deve redirecionar para a página de priorização
    assert b"Demanda criada!" in response.data
    
    # Verifica a chamada de INSERT no banco de dados
    mock_mysql.connection.cursor.return_value.execute.assert_any_call(
        """
                INSERT INTO demands (title, description, status, estimated_hours, priority)
                VALUES (%s, %s, %s, %s, %s)
            """,
        ('Nova Demanda de Teste', 'Descricao da nova demanda.', 'Em Fila', '10', 6) # max_priority + 1
    )
    # Verifica se o commit foi chamado
    mock_mysql.connection.commit.assert_called_once()

def test_update_priorities(client, mock_mysql):
    """
    Testa a atualização de prioridades via JSON.
    """
    response = client.post('/demands/update_priorities', json={
        'ordered_ids': ['3', '1', '2']
    })
    
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['status'] == 'success'
    
    # Verifica as chamadas de UPDATE no banco
    cursor_mock = mock_mysql.connection.cursor.return_value
    cursor_mock.execute.assert_any_call("UPDATE demands SET priority = %s WHERE id = %s", (0, '3'))
    cursor_mock.execute.assert_any_call("UPDATE demands SET priority = %s WHERE id = %s", (1, '1'))
    cursor_mock.execute.assert_any_call("UPDATE demands SET priority = %s WHERE id = %s", (2, '2'))
    
    mock_mysql.connection.commit.assert_called_once()