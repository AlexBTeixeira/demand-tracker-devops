# tests/conftest.py
import pytest
from unittest.mock import Mock, MagicMock
import sys
import os

# Adiciona o diretório raiz ao path para imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(autouse=True)
def mock_mysql():
    """Mock do MySQL para todos os testes"""
    # Mock do cursor
    mock_cursor = Mock()
    mock_cursor.execute = Mock()
    mock_cursor.fetchone = Mock(return_value=None)
    mock_cursor.fetchall = Mock(return_value=[])
    mock_cursor.close = Mock()
    
    # Mock da conexão
    mock_connection = Mock()
    mock_connection.cursor = Mock(return_value=mock_cursor)
    mock_connection.commit = Mock()
    mock_connection.close = Mock()
    
    # Mock do objeto mysql
    mock_mysql_obj = Mock()
    mock_mysql_obj.connection = mock_connection
    mock_mysql_obj.init_app = Mock()
    
    # Substitui o mysql nos módulos que o importam
    import extensions
    original_mysql = extensions.mysql
    extensions.mysql = mock_mysql_obj
    
    # Também substitui nos blueprints
    try:
        import blueprints.auth
        blueprints.auth.mysql = mock_mysql_obj
    except ImportError:
        pass
        
    try:
        import blueprints.demands
        blueprints.demands.mysql = mock_mysql_obj
    except ImportError:
        pass
        
    try:
        import blueprints.tracker
        blueprints.tracker.mysql = mock_mysql_obj
    except ImportError:
        pass
        
    try:
        import blueprints.reports
        blueprints.reports.mysql = mock_mysql_obj
    except ImportError:
        pass
    
    yield mock_mysql_obj
    
    # Restaura o mysql original
    extensions.mysql = original_mysql
