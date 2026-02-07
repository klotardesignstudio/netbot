from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from datetime import datetime

class SocialPlatform(str, Enum):
    INSTAGRAM = "instagram"
    THREADS = "threads"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    BLUESKY = "bluesky"
    DEVTO = "devto"

@dataclass
class SocialAuthor:
    username: str
    platform: SocialPlatform
    id: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None
    profile_url: Optional[str] = None
    is_verified: bool = False

@dataclass
class SocialComment:
    id: str
    author: SocialAuthor
    text: str
    created_at: Optional[datetime] = None
    like_count: int = 0

@dataclass
class SocialPost:
    id: str
    platform: SocialPlatform
    author: SocialAuthor
    content: str  # Caption or Tweet text
    url: str
    created_at: Optional[datetime] = None
    
    # Media
    media_urls: List[str] = field(default_factory=list) # Images/Videos
    media_type: str = "text" # image, video, carousel, text
    
    # Interactions
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    
    # Context
    comments: List[SocialComment] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict) # Original payload

@dataclass
class ActionDecision:
    should_act: bool
    action_type: str = "comment" # comment, like, share
    content: Optional[str] = None # The comment text
    reasoning: Optional[str] = None
    platform: Optional[SocialPlatform] = None
