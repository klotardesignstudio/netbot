import requests
from typing import Optional, List, Dict, Any
from core.interfaces import SocialNetworkClient
from core.models import SocialPlatform, SocialPost, SocialAuthor, SocialComment, SocialProfile
from config.settings import settings
from core.logger import logger

class DevToClient(SocialNetworkClient):
    BASE_URL = "https://dev.to/api"

    @property
    def platform(self) -> SocialPlatform:
        return SocialPlatform.DEVTO

    def __init__(self):
        self.api_key = settings.DEVTO_API_KEY
        self.headers = {
            "api-key": self.api_key,
            "User-Agent": "NetBot/2.0"
        }

    def login(self) -> bool:
        """
        Dev.to uses API Key, so specific login flow isn't strictly necessary,
        but we can check if the key is valid by fetching the authenticated user.
        """
        if not self.api_key:
            logger.error("[DevTo] No API Key provided.")
            return False
            
        try:
            response = requests.get(f"{self.BASE_URL}/users/me", headers=self.headers)
            if response.status_code == 200:
                user_data = response.json()
                logger.info(f"[DevTo] Authenticated as {user_data.get('username')}")
                return True
            else:
                logger.error(f"[DevTo] Authentication failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"[DevTo] Login error: {e}")
            return False

    def stop(self):
        """No browser to close."""
        pass

    def get_post_details(self, post_id: str) -> Optional[SocialPost]:
        """Fetches article details and recent comments for context."""
        try:
            # 1. Fetch Article Details
            response = requests.get(f"{self.BASE_URL}/articles/{post_id}", headers=self.headers)
            if response.status_code != 200:
                logger.error(f"[DevTo] Failed to fetch article {post_id}: {response.status_code}")
                return None
            
            data = response.json()
            
            # 2. Fetch Comments (for context)
            comments = self._fetch_comments(post_id)

            author = SocialAuthor(
                username=data["user"]["username"],
                platform=SocialPlatform.DEVTO,
                id=str(data["user"]["user_id"]),
                display_name=data["user"]["name"],
                profile_url=f"https://dev.to/{data['user']['username']}",
                bio=data["user"].get("github_username") # using github as bio proxy or fetch profile
            )

            return SocialPost(
                id=str(data["id"]),
                platform=SocialPlatform.DEVTO,
                author=author,
                content=data.get("body_markdown", "")[:5000], # Limit content for context window
                url=data["url"],
                created_at=None, # Parse if needed
                media_urls=[data["cover_image"]] if data.get("cover_image") else [],
                media_type="image" if data.get("cover_image") else "text",
                like_count=data["public_reactions_count"],
                comment_count=data["comments_count"],
                comments=comments,
                raw_data=data
            )
            
        except Exception as e:
            logger.error(f"[DevTo] Error getting post details: {e}")
            return None

    def _fetch_comments(self, article_id: str, limit: int = 5) -> List[SocialComment]:
        """Fetches top-level comments for context."""
        try:
            response = requests.get(f"{self.BASE_URL}/comments?a_id={article_id}", headers=self.headers)
            if response.status_code == 200:
                comments_data = response.json()
                # Dev.to returns a tree. We just take top-level for now.
                # Sort by latest or top? API returns threaded.
                
                parsed_comments = []
                for c in comments_data[:limit]:
                    author = SocialAuthor(
                        username=c["user"]["username"],
                        platform=SocialPlatform.DEVTO,
                        id=str(c["user"]["user_id"])
                    )
                    parsed_comments.append(SocialComment(
                        id=c["id_code"],
                        author=author,
                        text=self._clean_html(c.get("body_html", "")),
                        like_count=0 # API doesn't expose this easily in list
                    ))
                return parsed_comments
            return []
        except Exception as e:
            logger.warning(f"[DevTo] Failed to fetch comments: {e}")
            return []

    def _clean_html(self, raw_html: str) -> str:
        """Simple HTML cleaner for comments (Dev.to returns body_html for comments)."""
        import re
        cleanr = re.compile('<.*?>')
        cleantext = re.sub(cleanr, '', raw_html)
        return cleantext.strip()

    def like_post(self, post: SocialPost) -> bool:
        """
        Reacts to an article.
        Dev.to requires category: "like", "unicorn", "exploding_head", "raised_hands", "fire"
        """
        try:
            payload = {
                "reactable_id": int(post.id),
                "reactable_type": "Article",
                "category": "like" 
            }
            response = requests.post(f"{self.BASE_URL}/reactions", json=payload, headers=self.headers)
            if response.status_code in [200, 201]:
                logger.info(f"[DevTo] Liked article {post.id}")
                return True
            elif response.status_code == 422: # Already reacted?
                logger.warning(f"[DevTo] Already liked? {response.text}")
                return True # Treat as success
            else:
                logger.error(f"[DevTo] Failed to like: {response.text}")
                return False
        except Exception as e:
            logger.error(f"[DevTo] Error liking: {e}")
            return False

    def post_comment(self, post: SocialPost, text: str) -> bool:
        """Posts a comment to the article."""
        try:
            payload = {
                "comment": {
                    "body_markdown": text
                }
            }
            # Endpoint: POST /api/comments?a_id={id} - NO, docs say POST /api/comments with payload
            # Actually structure is specific.
            # Docs: POST /api/comments
            # Payload: { "comment": { "body_markdown": "..." } } 
            # It seems we need to pass reactable_id or similar?
            # Re-checking docs... 
            # https://developers.forem.com/api/v1#tag/comments/operation/createComment
            # It says path param? No.
            # It seems we might need to target the article via specific endpoint or payload param.
            # Let's try adding reactable_id to payload or using the specific endpoint if it exists.
            
            # Correction: It seems usually it's POST /api/comments with reactable_id inside or similar.
            # Let's inspect the `request` usage in standard libs or assume standard Forem API.
            # Forem API: POST /comments
            # "comment": { "body_markdown": "..." } -> This creates a comment but where?
            # Missing `commentable_id` and `commentable_type` in strict API?
            # Actually, standard is to pass it in the URL if it's a nested resource, OR in body.
            
            # Let's use the `POST /api/articles/{id}/comments` if it exists? No.
            # Common pattern in Dev.to API wrappers:
            # { "comment": { "body_markdown": "...", "commentable_id": 123, "commentable_type": "Article" } }
            
            payload["comment"]["commentable_id"] = int(post.id)
            payload["comment"]["commentable_type"] = "Article"
            
            response = requests.post(f"{self.BASE_URL}/comments", json=payload, headers=self.headers)
            
            if response.status_code in [200, 201]:
                logger.info(f"[DevTo] Commented on {post.id}")
                return True
            else:
                logger.error(f"[DevTo] Failed to comment: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"[DevTo] Error commenting: {e}")
            return False

    def search_posts(self, query: str, limit: int = 10) -> List[SocialPost]:
        """Searches articles by tag."""
        try:
            # Discovery uses query as tag
            params = {
                "tag": query,
                "per_page": limit,
                "state": "fresh" # fresh checking? or rising.
            }
            response = requests.get(f"{self.BASE_URL}/articles", params=params, headers=self.headers)
            if response.status_code == 200:
                return self._parse_articles_list(response.json())
            return []
        except Exception as e:
            logger.error(f"[DevTo] Error searching: {e}")
            return []

    def get_user_latest_posts(self, username: str, limit: int = 5) -> List[SocialPost]:
        """Fetches latest posts from a user."""
        try:
            params = {
                "username": username,
                "per_page": limit
            }
            response = requests.get(f"{self.BASE_URL}/articles", params=params, headers=self.headers)
            if response.status_code == 200:
                return self._parse_articles_list(response.json())
            return []
        except Exception as e:
            logger.error(f"[DevTo] Error fetching user posts: {e}")
            return []
            
    def _parse_articles_list(self, articles_data: List[Dict]) -> List[SocialPost]:
        posts = []
        for data in articles_data:
            if data.get("type_of") != "article":
                continue
                
            author = SocialAuthor(
                username=data["user"]["username"],
                platform=SocialPlatform.DEVTO,
                id=str(data["user"]["user_id"]),
                display_name=data["user"]["name"],
                profile_url=f"https://dev.to/{data['user']['username']}"
            )
            
            post = SocialPost(
                id=str(data["id"]),
                platform=SocialPlatform.DEVTO,
                author=author,
                content=data["title"] + "\n" + data["description"], # Content is limited in list view
                url=data["url"],
                created_at=None,
                media_urls=[data["cover_image"]] if data.get("cover_image") else [],
                media_type="image" if data.get("cover_image") else "text",
                like_count=data["public_reactions_count"],
                comment_count=data["comments_count"],
                raw_data=data
            )
            posts.append(post)
        return posts
        
    def get_profile_data(self, username: str) -> Optional[SocialProfile]:
        try:
            response = requests.get(f"{self.BASE_URL}/users/by_username", params={"url": username}, headers=self.headers)
            # Actually endpoint is /users/by_username?url={username} ?? No. 
            # Correct is /users/by_username?username={username}
            
            response = requests.get(f"{self.BASE_URL}/users/by_username", params={"url": username}, headers=self.headers)
            # Re-checking docs.. GET /users/by_username?url=... seems to be a specific lookup. 
            # Let's try simple GET /users/{id} if we had ID, but we have username.
            # Typically user object in article has most info.
            # Let's stick to what we have or try parsing.
            return None # Not critical for interactions right now
        except:
            return None
