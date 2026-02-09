
import pytest
from unittest.mock import MagicMock, patch
from core.database import Database

@pytest.fixture
def mock_supabase():
    with patch("core.database.create_client") as mock_create, \
         patch("core.database.settings") as mock_settings:
        
        mock_settings.SUPABASE_URL = "http://test.com"
        mock_settings.SUPABASE_KEY = "testkey"
        
        mock_client = MagicMock()
        mock_create.return_value = mock_client
        
        # Mock table().insert().execute() chain
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.insert.return_value.execute.return_value = MagicMock(data=[])
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        
        yield mock_client

def test_init_raises_error_without_keys():
    """Test that Database raises ValueError if keys are missing."""
    with patch("core.database.settings") as mock_settings:
        mock_settings.SUPABASE_URL = None
        with pytest.raises(ValueError):
            Database()

def test_log_interaction(mock_supabase):
    """Test logging an interaction."""
    db = Database()
    
    db.log_interaction("p1", "u1", "Nice!", "instagram")
    
    # Check insert called on "interactions" table
    mock_supabase.table.assert_any_call("interactions")
    mock_supabase.table().insert.assert_called()
    
    # Check increment_daily_stats RPC called
    mock_supabase.rpc.assert_called_with("increment_daily_stats", {"p_platform": "instagram"})

def test_check_if_interacted_false(mock_supabase):
    """Test interaction check returns False when no data found."""
    # Setup mock to return empty list
    mock_query = mock_supabase.table().select().eq().eq().execute()
    mock_query.data = []
    
    db = Database()
    result = db.check_if_interacted("p1", "instagram")
    
    assert result is False

def test_check_if_interacted_true(mock_supabase):
    """Test interaction check returns True when data found."""
    # Setup mock to return data
    mock_supabase.table().select().eq().eq().execute.return_value.data = [{"id": 1}]
    
    db = Database()
    result = db.check_if_interacted("p1", "instagram")
    
    assert result is True
