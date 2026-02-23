import calendar
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from agno.agent import Agent
from agno.models.openai import OpenAIChat

from config.settings import settings
from core.database import db
from core.logger import logger

# --- UTILS ---

def get_iso_weeks_for_month(year: int, month: int) -> List[int]:
    """Returns a list of ISO week numbers that fall into the given month."""
    cal = calendar.monthcalendar(year, month)
    weeks = []
    for week_arr in cal:
        # Find any valid day in this week
        valid_days = [d for d in week_arr if d != 0]
        if valid_days:
            iso_week = date(year, month, valid_days[0]).isocalendar()[1]
            if iso_week not in weeks:
                weeks.append(iso_week)
    return weeks

# --- AGENT 1: STRATEGIC ROADMAPPER ---

class MonthlyTheme(BaseModel):
    month: int = Field(..., description="Month number (1-12)")
    year: int = Field(..., description="Year (e.g., 2026)")
    theme: str = Field(..., description="The macro theme for the month (e.g., 'Mastering Distributed Systems')")
    description: str = Field(..., description="Detailed description of the macro theme and its goals")

class SemesterRoadmapResponse(BaseModel):
    themes: List[MonthlyTheme]

class StrategicRoadmapper:
    """Agent responsible for planning macro monthly themes."""
    def __init__(self):
        persona_path = settings.BASE_DIR / "docs" / "persona" / "persona.md"
        try:
            with open(persona_path, "r", encoding="utf-8") as f:
                persona_content = f.read()
        except:
            persona_content = "You are Guilherme Zaia, a Senior Software Engineer."

        self.agent = Agent(
            model=OpenAIChat(id="gpt-4o"),
            description="Strategic Content Planner",
            instructions=(
                f"{persona_content}\n\n"
                "Your objective is to define high-level monthly themes for technical content "
                "that builds authority. The themes must be progressive, modern, and engaging. "
                "OUTPUT MUST BE STRICTLY IN ENGLISH."
            ),
            output_schema=SemesterRoadmapResponse,
        )

    def generate_semester_plan(self, current_year: int, start_month: int) -> List[Dict]:
        logger.info(f"Generating semester roadmap starting from {start_month}/{current_year}...")
        
        # Fetch past themes to avoid repetition
        past_themes_str = ""
        try:
            res = db.client.table("monthly_themes").select("theme").order("created_at", desc=True).limit(20).execute()
            if res.data:
                past_themes_str = ", ".join([t["theme"] for t in res.data])
        except Exception:
            pass

        prompt = f"""
        Generate a 6-month content roadmap starting from Month {start_month}, Year {current_year}.
        Focus on advanced backend engineering (.NET, Python), system architecture, multi-agent AI, and tech leadership.
        
        CRITICAL GUARDRAIL - DO NOT REPEAT OR CLOSELY RESEMBLE THESE PAST THEMES:
        {past_themes_str if past_themes_str else "None yet."}
        """
        
        try:
            response = self.agent.run(prompt)
            roadmap: SemesterRoadmapResponse = response.content
            
            # Save to database
            results = []
            for theme in roadmap.themes:
                try:
                    data = {
                        "year": theme.year,
                        "month": theme.month,
                        "theme": theme.theme,
                        "description": theme.description
                    }
                    res = db.client.table("monthly_themes").upsert(data, on_conflict="year, month").execute()
                    if res.data:
                        results.append(res.data[0])
                    else:
                        results.append(data)
                except Exception as db_err:
                    logger.error(f"Failed to save monthly theme: {db_err}")
                    
            logger.info("✅ Semester roadmap generated and saved.")
            return results
                
        except Exception as e:
            logger.error(f"Error generating semester plan: {e}")
            return []


# --- AGENT 2: WEEKLY TACTICIAN ---

class WeeklyTopic(BaseModel):
    week_number: int = Field(..., description="The absolute ISO week number provided in the prompt")
    topic: str = Field(..., description="Specific, actionable topic related to the monthly theme")
    description: str = Field(..., description="Brief outline of what to cover this week")

class MonthlyTacticsResponse(BaseModel):
    topics: List[WeeklyTopic]

class WeeklyTactician:
    """Agent responsible for breaking down a monthly theme into weekly practical topics."""
    def __init__(self):
        persona_path = settings.BASE_DIR / "docs" / "persona" / "persona.md"
        try:
            with open(persona_path, "r", encoding="utf-8") as f:
                persona_content = f.read()
        except:
            persona_content = "You are Guilherme Zaia, a Senior Software Engineer."

        self.agent = Agent(
            model=OpenAIChat(id="gpt-4o-mini"),
            description="Tactical Content Planner",
            instructions=(
                f"{persona_content}\n\n"
                "You break down macro monthly themes into specific, actionable weekly topics. "
                "Each topic should stand alone but contribute to the overall monthly goal. "
                "OUTPUT MUST BE STRICTLY IN ENGLISH."
            ),
            output_schema=MonthlyTacticsResponse,
        )

    def generate_weekly_topics(self, monthly_theme_id: str, year: int, month: int, theme: str, description: str) -> List[Dict]:
        logger.info(f"Generating weekly topics for theme: {theme}...")
        
        iso_weeks = get_iso_weeks_for_month(year, month)
        
        # Fetch past topics to avoid repetition
        past_topics_str = ""
        try:
            res = db.client.table("weekly_topics").select("topic").order("created_at", desc=True).limit(50).execute()
            if res.data:
                past_topics_str = ", ".join([t["topic"] for t in res.data])
        except Exception:
            pass

        prompt = f"""
        MONTHLY THEME: {theme}
        DESCRIPTION: {description}
        
        Break this theme down into specific weekly topics for the following ISO Week Numbers: {iso_weeks}.
        Generate EXACTLY one topic per week number provided.

        CRITICAL GUARDRAIL - DO NOT REPEAT OR CLOSELY RESEMBLE THESE PAST TOPICS:
        {past_topics_str if past_topics_str else "None yet."}
        """
        
        try:
            response = self.agent.run(prompt)
            tactics: MonthlyTacticsResponse = response.content
            
            results = []
            for t in tactics.topics:
                # Ensure the LLM didn't hallucinate a week number not in our list
                if t.week_number in iso_weeks:
                    try:
                        data = {
                            "monthly_theme_id": monthly_theme_id,
                            "year": year,
                            "week_number": t.week_number,
                            "topic": t.topic,
                            "description": t.description
                        }
                        res = db.client.table("weekly_topics").upsert(data, on_conflict="year, week_number").execute()
                        if res.data:
                            results.append(res.data[0])
                        else:
                            results.append(data)
                    except Exception as db_err:
                        logger.error(f"Failed to save weekly topic: {db_err}")
                else:
                    logger.warning(f"Tactician returned an invalid week number: {t.week_number}")
                    
            logger.info(f"✅ Generated {len(results)} weekly topics.")
            return results
            
        except Exception as e:
            logger.error(f"Error generating weekly topics: {e}")
            return []


# --- AGENT 3: DAILY BRIEFING AGENT ---

class DailyBriefingContent(BaseModel):
    format: str = Field(..., description="Must be exactly 'carousel_cover' or 'fixed_image'")
    content_angle: str = Field(..., description="The specific hook or angle for today's post.")
    key_points: List[str] = Field(..., description="3-5 key points to cover in the caption or slides.")
    visual_suggestion: str = Field(..., description="A brief prompt idea for the generated background image.")

class DailyBriefingAgent:
    """Agent responsible for generating the daily post briefing based on the week's topic."""
    def __init__(self):
        persona_path = settings.BASE_DIR / "docs" / "persona" / "persona.md"
        try:
            with open(persona_path, "r", encoding="utf-8") as f:
                persona_content = f.read()
        except:
            persona_content = "You are Guilherme Zaia, a Senior Software Engineer."

        self.agent = Agent(
            model=OpenAIChat(id="gpt-4o-mini"),
            description="Daily Content Briefer",
            instructions=(
                f"{persona_content}\n\n"
                "You translate a weekly topic into a specific daily post briefing. "
                "Decide the best format (carousel_cover for deep dives/tutorials, fixed_image for quick insights/quotes) "
                "and provide a concrete outline. "
                "OUTPUT MUST BE STRICTLY IN ENGLISH."
            ),
            output_schema=DailyBriefingContent,
        )

    def generate_briefing(self, weekly_topic: str) -> Optional[Dict[str, Any]]:
        logger.info(f"Generating daily briefing for topic: {weekly_topic}...")
        
        day_of_week = datetime.now().strftime("%A")
        
        # Fetch past post angles to avoid repetition
        past_angles_str = ""
        try:
            res = db.client.table("content_queue").select("briefing_json").order("created_at", desc=True).limit(30).execute()
            if res.data:
                past_angles_str = ", ".join([row["briefing_json"].get("content_angle", "") for row in res.data if row.get("briefing_json")])
        except Exception:
            pass

        prompt = f"""
        WEEKLY TOPIC: {weekly_topic}
        TODAY: {day_of_week}
        
        Create a specific daily post briefing for an Instagram post based on this topic.
        If the topic requires multiple steps or deep explanation, suggest 'carousel_cover'. 
        If it's a quick insight, opinion, or single strong statement, suggest 'fixed_image'.

        CRITICAL GUARDRAIL - DO NOT REPEAT THESE PAST ANGLES:
        {past_angles_str if past_angles_str else "None yet."}
        """
        
        try:
            response = self.agent.run(prompt)
            briefing: DailyBriefingContent = response.content
            logger.info(f"✅ Daily briefing generated (Format: {briefing.format}).")
            return briefing.model_dump()
        except Exception as e:
            logger.error(f"Error generating daily briefing: {e}")
            return None
