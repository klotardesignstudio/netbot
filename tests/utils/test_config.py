import pytest
import json
import yaml
from unittest.mock import patch, mock_open
from config.settings import Settings

def test_load_vip_list_exists():
    """Test loading VIP list when file exists."""
    mock_data = ["user1", "user2"]
    
    with patch("pathlib.Path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=json.dumps(mock_data))):
        
        vips = Settings.load_vip_list()
        assert vips == mock_data
        assert len(vips) == 2

def test_load_vip_list_missing():
    """Test loading VIP list when file does not exist."""
    with patch("pathlib.Path.exists", return_value=False):
        vips = Settings.load_vip_list()
        assert vips == []

def test_load_hashtags_exists():
    """Test loading hashtags when file exists."""
    mock_data = ["#ai", "#bot"]
    
    with patch("pathlib.Path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=json.dumps(mock_data))):
        
        tags = Settings.load_hashtags()
        assert tags == mock_data

def test_load_prompts_exists():
    """Test loading prompts from YAML."""
    mock_data = {"persona": {"role": "Bot"}}
    yaml_content = yaml.dump(mock_data)
    
    with patch("pathlib.Path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=yaml_content)):
        
        prompts = Settings.load_prompts()
        assert prompts == mock_data
        assert prompts["persona"]["role"] == "Bot"

def test_settings_env_vars():
    """Test that critical settings are loaded (checking default or mocked values)."""
    # specific env vars might be None in test env, but defaults should be present
    assert Settings.daily_interaction_limit is not None
    assert isinstance(Settings.daily_interaction_limit, int)
    assert Settings.min_sleep_interval == 600

def test_load_hashtags_missing():
    """Test loading hashtags when file is missing."""
    with patch("pathlib.Path.exists", return_value=False):
        tags = Settings.load_hashtags()
        assert tags == []

def test_load_prompts_missing():
    """Test loading prompts when file is missing."""
    with patch("pathlib.Path.exists", return_value=False):
        prompts = Settings.load_prompts()
        assert prompts == {}
