import json
from typing import Optional, List
from pydantic import BaseModel, Field
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from config.settings import settings
from core.logger import logger
from core.models import SocialPost, ActionDecision, SocialPlatform
from core.knowledge_base import NetBotKnowledgeBase

# --- Structured Output Schema ---
# We reuse ActionDecision from models, but Agno might need a Pydantic model for output parsing
# So we keep a specific output model and map it later, or use valid Pydantic models directly.

class AgentOutput(BaseModel):
    should_comment: bool = Field(..., description="Set to True if we should comment, False to skip.")
    comment_text: str = Field(..., description="The comment text. MUST be in English. No hashtags. Max 1 emoji. Avoid generic phrases.")
    reasoning: str = Field(..., description="Brief reason for the decision and the chosen comment.")

class SocialAgent:
    def __init__(self):
        self.prompts = settings.load_prompts()
        self.knowledge_base = NetBotKnowledgeBase()
        self.agent = self._create_agent()

    def _create_agent(self) -> Agent:
        """Configures the Agno Agent with GPT-4o-mini."""
        
        # Construct System Prompt from YAML
        persona = self.prompts.get("persona", {})
        constraints = self.prompts.get("constraints", {})
        
        system_prompt = f"""
        You are a Social Media User interacting with posts.
        Role: {persona.get('role', 'User')}
        Tone: {persona.get('tone', 'Casual')}
        Language: {persona.get('language', 'en-US')}
        
        Style Guidelines:
        {json.dumps(persona.get('style_guidelines', []), indent=2)}
        
        Constraints:
        {json.dumps(constraints, indent=2)}
        
        Your Goal: Read the content, comments (context), and analyze media to generate a contextual, authentic engagement.
        
        IMPORTANT: Access your knowledge base to see how you've interacted with similar posts in the past. 
        Maintain consistency in tone and opinions. If you've praised a topic before, don't hate on it now unless there's a good reason.
        """
        
        return Agent(
            model=OpenAIChat(id="gpt-4o-mini"),
            description="Social Engagement Agent",
            instructions=system_prompt,
            output_schema=AgentOutput,
            knowledge=self.knowledge_base,
            search_knowledge=True,
            markdown=True
        )

    def decide_and_comment(self, post: SocialPost) -> ActionDecision:
        """
        Analyzes a candidate post and returns an ActionDecision.
        """
        try:
            # Prepare Input
            comments_context = ""
            if post.comments:
                formatted_comments = "\n".join([f"- @{c.author.username}: {c.text}" for c in post.comments])
                comments_context = f"\nRecent Comments (for context):\n{formatted_comments}"

            user_input = f"""
            Analyze this {post.platform.value} Post:
            - Author: @{post.author.username}
            - Content: "{post.content}"
            - Media Type: {post.media_type}
            {comments_context}
            
            Determine if I should comment. If yes, write the comment.
            """
            
            logger.info(f"Agent analyzing post {post.id} by {post.author.username} on {post.platform.value}...")
            
            # Try to pass image URL directly in the prompt if available
            if post.media_urls:
                # Assuming simple support for the first image for now
                user_input += f"\n\nImage URL (for context): {post.media_urls[0]}"
            
            # Run agent
            response_obj = self.agent.run(user_input)
            response: AgentOutput = response_obj.content
            
            # Log Token Usage if available
            if hasattr(response_obj, 'metrics') and response_obj.metrics:
                logger.info(f"💰 Token Usage: {response_obj.metrics}")
            
            logger.info(f"Agent Decision: Comment={response.should_comment} | Reasoning: {response.reasoning}")
            
            return ActionDecision(
                should_act=response.should_comment,
                content=response.comment_text,
                reasoning=response.reasoning,
                action_type="comment",
                platform=post.platform
            )

        except Exception as e:
            logger.error(f"Agent Malfunction: {e}")
            return ActionDecision(should_act=False, reasoning=f"Error: {e}")

# agent = SocialAgent() # Instantiation moved to main.py to avoid side effects on import
