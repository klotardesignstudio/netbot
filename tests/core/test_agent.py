import pytest
from unittest.mock import MagicMock, patch
from core.agent import SocialAgent, AgentOutput
from core.models import SocialPost, SocialPlatform, SocialAuthor, SocialComment

@pytest.fixture
def mock_post():
    return SocialPost(
        id="post_123",
        platform=SocialPlatform.INSTAGRAM,
        content="This is a test post about AI.",
        url="http://example.com/post/123",
        author=SocialAuthor(username="ai_fan", platform=SocialPlatform.INSTAGRAM, id="user_1"),
        media_type="image",
        media_urls=["http://example.com/ai.jpg"]
    )

@pytest.fixture
def mock_agent_dependencies():
    """Mocks settings and Agno Agent creation to avoid OpenAI calls."""
    with patch("core.agent.settings") as mock_settings, \
         patch("core.agent.Agent") as mock_agno_agent_cls:
        
        # Mock settings.load_prompts
        mock_settings.load_prompts.return_value = {
            "persona": {"role": "Tester", "tone": "Neutral"},
            "constraints": {}
        }
        
        # Mock the Agent instance returned by the class
        mock_agent_instance = MagicMock()
        mock_agno_agent_cls.return_value = mock_agent_instance
        
        yield mock_agent_instance

def test_decide_and_comment_should_act(mock_agent_dependencies, mock_post):
    """Test scenario where the agent decides to comment."""
    mock_agent_instance = mock_agent_dependencies
    
    # Setup mock response
    mock_response = MagicMock()
    mock_response.content = AgentOutput(
        should_comment=True,
        comment_text="This is amazing!",
        reasoning="Post is relevant to AI."
    )
    mock_agent_instance.run.return_value = mock_response

    # Initialize Agent (will use mocks)
    social_agent = SocialAgent()
    
    # Act
    decision = social_agent.decide_and_comment(mock_post)
    
    # Assert
    assert decision.should_act is True
    assert decision.content == "This is amazing!"
    assert decision.reasoning == "Post is relevant to AI."
    assert decision.platform == SocialPlatform.INSTAGRAM
    
    # Verify input prompt contained key info
    calls = mock_agent_instance.run.call_args_list
    assert len(calls) == 1
    prompt_text = calls[0][0][0]
    assert "ai_fan" in prompt_text
    assert "Test post about AI" in prompt_text or "test post about AI" in prompt_text

def test_decide_and_comment_should_skip(mock_agent_dependencies, mock_post):
    """Test scenario where the agent decides to skip."""
    mock_agent_instance = mock_agent_dependencies
    
    # Setup mock response
    mock_response = MagicMock()
    mock_response.content = AgentOutput(
        should_comment=False,
        comment_text="",
        reasoning="Off-topic content."
    )
    mock_agent_instance.run.return_value = mock_response

    social_agent = SocialAgent()
    decision = social_agent.decide_and_comment(mock_post)
    
    assert decision.should_act is False
    assert decision.content == ""
    assert decision.reasoning == "Off-topic content."

def test_decide_and_comment_exception_handling(mock_agent_dependencies, mock_post):
    """Test that exceptions during agent execution are handled gracefully."""
    mock_agent_instance = mock_agent_dependencies
    
    # Simulate an error (e.g., API timeout)
    mock_agent_instance.run.side_effect = Exception("OpenAI API Timeout")

    social_agent = SocialAgent()
    decision = social_agent.decide_and_comment(mock_post)
    
    assert decision.should_act is False
    assert "Agent Malfunction" in decision.reasoning or "Error" in decision.reasoning

def test_decide_and_comment_with_history(mock_agent_dependencies):
    """Test that existing comments are included in the prompt context."""
    mock_agent_instance = mock_agent_dependencies
    
    # Setup mock response
    mock_response = MagicMock()
    mock_response.content = AgentOutput(
        should_comment=True, comment_text="Agreed!", reasoning="Concurring."
    )
    mock_agent_instance.run.return_value = mock_response

    # Create post with comments
    author = SocialAuthor(username="op", platform=SocialPlatform.INSTAGRAM, id="u1")
    commenter = SocialAuthor(username="fan1", platform=SocialPlatform.INSTAGRAM, id="u2")
    
    post = SocialPost(
        id="p1", 
        platform=SocialPlatform.INSTAGRAM, 
        content="Hello", 
        url="...", 
        author=author,
        comments=[
            SocialComment(id="c1", author=commenter, text="First interaction!")
        ]
    )
    
    # Act
    SocialAgent().decide_and_comment(post)
    
    # Assert
    prompt_text = mock_agent_instance.run.call_args[0][0]
    assert "Recent Comments" in prompt_text
    assert "@fan1: First interaction!" in prompt_text

def test_decide_and_comment_with_image(mock_agent_dependencies):
    """Test that image URL is included in the prompt context."""
    mock_agent_instance = mock_agent_dependencies
    
    mock_response = MagicMock()
    mock_response.content = AgentOutput(
        should_comment=True, comment_text="Nice pic!", reasoning="Visuals."
    )
    mock_agent_instance.run.return_value = mock_response
    
    post = SocialPost(
        id="p2",
        platform=SocialPlatform.INSTAGRAM,
        content="Look at this",
        url="...",
        author=SocialAuthor(username="op", platform=SocialPlatform.INSTAGRAM, id="u1"),
        media_urls=["http://example.com/pic.jpg"],
        media_type="image"
    )
    
    # Act
    SocialAgent().decide_and_comment(post)
    
    # Assert
    prompt_text = mock_agent_instance.run.call_args[0][0]
    assert "Image URL" in prompt_text
    assert "http://example.com/pic.jpg" in prompt_text
