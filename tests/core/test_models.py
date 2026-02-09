import pytest
from core.models import SocialPost, ActionDecision, SocialPlatform, SocialAuthor, SocialComment

def test_social_post_creation_valid():
    """Test creating a SocialPost with valid data."""
    post = SocialPost(
        id="123",
        platform=SocialPlatform.INSTAGRAM,
        content="Test content",
        url="http://example.com/post/123",
        author=SocialAuthor(username="testuser", platform=SocialPlatform.INSTAGRAM, id="user123"),
        media_type="image",
        media_urls=["http://example.com/image.jpg"],
        comments=[
            SocialComment(
                id="c1", 
                text="Nice!", 
                author=SocialAuthor(username="fan1", platform=SocialPlatform.INSTAGRAM, id="u1")
            )
        ]
    )
    assert post.id == "123"
    assert post.platform == SocialPlatform.INSTAGRAM
    assert len(post.comments) == 1

def test_social_post_validation_error():
    """Test that missing required fields raises ValidationError."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        # Missing url, platform, author
        SocialPost(
            id="123",
            content="Invalid post"
        )

def test_action_decision_creation():
    """Test ActionDecision creation."""
    decision = ActionDecision(
        should_act=True,
        action_type="comment",
        content="Great post!",
        reasoning="Relevant content",
        platform=SocialPlatform.INSTAGRAM
    )
    assert decision.should_act is True
    assert decision.content == "Great post!"

def test_action_decision_default_skip():
    """Test logic for skipping action."""
    decision = ActionDecision(
        should_act=False,
        reasoning="Not relevant",
        platform=SocialPlatform.INSTAGRAM
    )
    assert decision.should_act is False
    assert decision.content is None
