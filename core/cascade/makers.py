import os
import json
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.anthropic import Claude


from config.settings import settings
from core.logger import logger

# --- AGENT 1: VISUAL DESIGNER ---

class CarouselCoverSchema(BaseModel):
    formato: str = Field(description="Retrato (4:5)")
    instrucoes_gerais: str = Field(description="Gere a imagem final já contendo estes textos, estilos e estrutura.")
    elementos_visuais: Dict[str, Any] = Field(description="Visual elements config with descriptive prompt for the background")
    elementos_texto: Dict[str, Any] = Field(description="Text configurations (titles, subtitles, positions, fonts, colors)")

class FixedImageSchema(BaseModel):
    formato: str = Field(description="Retrato (4:5) ou Quadrado (1:1)")
    tipo_post: str = Field(description="Imagem Única")
    instrucoes_gerais: str = Field(description="Gere a arte final completa. Sem indicadores de arrastar.")
    elementos_visuais: Dict[str, Any] = Field(description="Visual scene description for the background")
    elementos_texto: Dict[str, Any] = Field(description="Catchy phrase and signature configs")
    branding: Dict[str, Any] = Field(description="Branding rules")

class VisualDesigner:
    """Agent responsible for generating the JSON design schema and image via Gemini."""
    
    def __init__(self):
        # We use Gemini 1.5 Pro (via agno's Gemini integration)
        # Note: 'gemini-1.5-pro' is the standard model name in Agno/Google AI SDK
        self.cover_agent = Agent(
            model=OpenAIChat(id="gpt-4o"),
            description="Visual Cover Designer",
            instructions=(
                "You are an expert graphic designer and prompt engineer for Guilherme Zaia's technical Instagram. "
                "Based on the daily briefing, formulate the precise visual JSON structure for the initial cover image. "
                "The target aesthetic is modern tech, dark mode or sleek minimal, highly professional."
                "YOU MUST OUTPUT ONLY VALID JSON. No markdown blocks, no conversational text. "
                "ALL TEXT CONTENT INSIDE THE JSON MUST BE IN ENGLISH."
            )
        )
        
        self.fixed_image_agent = Agent(
            model=OpenAIChat(id="gpt-4o"),
            description="Visual Single Image Designer",
            instructions=(
                "You are an expert graphic designer for a technical Instagram. "
                "Based on the briefing, create the visual JSON structure for a single, impactful fixed image post. "
                "Focus on a bold statement, clean typography, and a tech-oriented premium background."
                "YOU MUST OUTPUT ONLY VALID JSON. No markdown blocks, no conversational text. "
                "ALL TEXT CONTENT INSIDE THE JSON MUST BE IN ENGLISH."
            )
        )

    def generate_visual_json(self, briefing: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        logger.info(f"Generating Visual JSON for format: {briefing.get('format')}...")
        
        prompt = f"""
        BRIEFING SUMMARY:
        - Angle: {briefing.get('content_angle')}
        - Formato: 1:1
        - Key Points: {json.dumps(briefing.get('key_points', []))}
        - Visual Suggestion: {briefing.get('visual_suggestion')}
        
        Create the full JSON configuration for the image. Make sure the 'elementos_visuais.fundo_imagem.descricao_prompt' 
        is extremely detailed, as it will be used to generate the final image if needed. 
        Invent a catchy, punchy Title and Subtitle based on the Angle and Key Points.
        
        The JSON must follow this exact structure:
        {{
            "formato": "1:1",
            "instrucoes_gerais": "...",
            "elementos_visuais": {{ ... }},
            "elementos_texto": {{ ... }}
        }}
        """
        
        try:
            if briefing.get('format') == 'carousel_cover':
                response = self.cover_agent.run(prompt)
            else:
                response = self.fixed_image_agent.run(prompt)
                
            raw_content = response.content.strip()
            if raw_content.startswith("```json"):
                raw_content = raw_content[7:-3].strip()
            elif raw_content.startswith("```"):
                raw_content = raw_content[3:-3].strip()
                
            json_output = json.loads(raw_content)
            logger.info("✅ Visual JSON generated successfully.")
            return json_output
            
        except Exception as e:
            logger.error(f"Error generating visual JSON: {e}")
            return None

    def generate_image(self, visual_json: Dict[str, Any]) -> Optional[str]:
        """Uses Gemini 2.5 Flash image generation API to render the visual JSON into an image."""
        logger.info("Generating Image with Gemini 2.5 Flash...")
        from google import genai
        from google.genai import types
        import mimetypes
        
        try:
            client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
            model = "gemini-2.5-flash-image"
            
            # Stringify the json to form the prompt
            prompt_text = f"Create exactly this image. Ensure high premium tech aesthetics:\n\n{json.dumps(visual_json, indent=2, ensure_ascii=False)}"
            
            contents = [
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=prompt_text)],
                ),
            ]
            
            # Set up the requested aspect ratio
            aspect_ratio_str = "1:1" if "1:1" in str(visual_json.get("formato", "")) else "3:4"
            
            generate_content_config = types.GenerateContentConfig(
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio_str,
                    # Optional args the user provided:
                    # image_size="",
                    # person_generation="",
                ),
                response_modalities=["IMAGE", "TEXT"],
            )

            file_path = None
            file_index = 0
            for chunk in client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=generate_content_config,
            ):
                if chunk.parts is None:
                    continue
                if chunk.parts[0].inline_data and chunk.parts[0].inline_data.data:
                    file_name = f"generated_cover_{file_index}"
                    file_index += 1
                    inline_data = chunk.parts[0].inline_data
                    data_buffer = inline_data.data
                    file_extension = mimetypes.guess_extension(inline_data.mime_type) or ".png"
                    
                    full_name = f"{file_name}{file_extension}"
                    with open(full_name, "wb") as f:
                        f.write(data_buffer)
                    file_path = full_name
                    logger.info(f"✅ Image generated and saved locally to {file_path}")
                    break # We only need the first image for the PoC
                else:
                    # Sometimes the model returns text instead of image chunks
                    logger.info("Gemini chunk response text: " + chunk.text)
                    
            return file_path
            
        except Exception as e:
            logger.error(f"Error generating image with Gemini 2.5 Flash: {e}")
            return None

# --- AGENT 2: SLIDE CONTENT GENERATOR ---

class SlideItem(BaseModel):
    titulo: str = Field(..., description="The title of the slide")
    conteudo: str = Field(..., description="The body text of the slide")

class SlideContentOutput(BaseModel):
    slides: List[SlideItem] = Field(..., description="List of slides.")

class SlideContentGenerator:
    """Agent responsible for writing the content of the internal carousel slides."""
    
    def __init__(self):
        # Load Persona / Brand Guide
        brand_path = settings.BASE_DIR / "docs" / "persona" / "brand.md"
        try:
            with open(brand_path, "r", encoding="utf-8") as f:
                self.persona_content = f.read()
        except:
            self.persona_content = "You are Guilherme Zaia, a Senior Software Engineer."

        self.agent = Agent(
            model=OpenAIChat(id="gpt-4o-mini"),
            description="Carousel Slide Content Writer",
            instructions=(
                f"{self.persona_content}\n\n"
                "You write the textual content for the internal slides of an Instagram Carousel. "
                "Keep the text concise, punchy, and highly readable. "
                "Each slide should have a short 'titulo' and a brief 'conteudo' explaining that specific point. "
                "ALL CONTENT MUST BE STRICTLY IN ENGLISH. "
                "YOU MUST OUTPUT ONLY VALID JSON matching the schema. No markdown blocks, no conversational text."
            ),
            output_schema=SlideContentOutput,
        )

    def generate_slides(self, briefing: Dict[str, Any]) -> List[Dict[str, str]]:
        logger.info("Generating internal carousel slides content...")
        
        prompt = f"""
        BRIEFING TOPIC: {briefing.get('content_angle')}
        KEY POINTS TO COVER:
        {json.dumps(briefing.get('key_points', []))}
        
        Create the text for each internal slide of the carousel based on the key points.
        Do not include the cover or the final CTA slide, just the educational/content slides.
        """
        
        try:
            response = self.agent.run(prompt)
            
            if isinstance(response.content, str):
                raw_content = response.content.strip()
                if raw_content.startswith("```json"):
                    raw_content = raw_content[7:-3].strip()
                elif raw_content.startswith("```"):
                    raw_content = raw_content[3:-3].strip()
                data = json.loads(raw_content)
                output = SlideContentOutput(**data)
            else:
                output = response.content
                
            logger.info(f"✅ Generated {len(output.slides)} internal slides.")
            
            # Convert SlideItems back to Dict[str, str] for the Renderer
            return [{"titulo": s.titulo, "conteudo": s.conteudo} for s in output.slides]
            
        except Exception as e:
            logger.error(f"Error generating slide contents: {e}")
            return []


# --- AGENT 3: COPYWRITER ---

class CopywriterOutput(BaseModel):
    caption: str = Field(..., description="The complete Instagram caption, engaging and well formatted.")
    hashtags: str = Field(..., description="A space-separated string of 15-20 relevant hashtags.")

class Copywriter:
    """Agent responsible for writing the Instagram caption."""
    
    def __init__(self):
        # Load Persona / Brand Guide
        brand_path = settings.BASE_DIR / "docs" / "persona" / "brand.md"
        try:
            with open(brand_path, "r", encoding="utf-8") as f:
                self.persona_content = f.read()
        except:
            self.persona_content = "You are Guilherme Zaia, a Senior Software Engineer."

        self.agent = Agent(
            model=OpenAIChat(id="gpt-4o"),
            description="Expert Tech Copywriter",
            instructions=(
                f"{self.persona_content}\n\n"
                "Your task is to write high-converting, authoritative Instagram captions based on the provided briefing. "
                "Rules:\n"
                "1. Hook: Start with a scroll-stopping first line.\n"
                "2. Body: Explain the concept clearly, using short paragraphs. Add value.\n"
                "3. CTA: End with a clear Call to Action (e.g., 'Save this post', 'Comment X for the link').\n"
                "4. Tone: Confident, technical but accessible, slightly provocative if appropriate.\n"
                "5. Emojis: Use 2-4 emojis max, intentionally placed.\n"
                "ALL TEXT AND CAPTIONS MUST BE STRICTLY IN ENGLISH.\n"
                "YOU MUST OUTPUT ONLY VALID JSON matching the schema. No markdown blocks, no conversational text."
            ),
            output_schema=CopywriterOutput,
        )

    def generate_caption(self, briefing: Dict[str, Any], visual_json: Dict[str, Any]) -> Optional[str]:
        logger.info("Generating Copywriter caption...")
        
        prompt = f"""
        BRIEFING:
        Angle: {briefing.get('content_angle')}
        Key Points: {json.dumps(briefing.get('key_points', []))}
        
        VISUAL CONTEXT (What the user will see in the image):
        {json.dumps(visual_json.get('elementos_texto', {}))}
        
        Write the Instagram caption.
        """
        
        try:
            response = self.agent.run(prompt)
            
            if isinstance(response.content, str):
                raw_content = response.content.strip()
                if raw_content.startswith("```json"):
                    raw_content = raw_content[7:-3].strip()
                elif raw_content.startswith("```"):
                    raw_content = raw_content[3:-3].strip()
                data = json.loads(raw_content)
                output = CopywriterOutput(**data)
            else:
                output = response.content
            
            final_text = f"{output.caption}\n\n{output.hashtags}"
            logger.info("✅ Caption generated successfully.")
            return final_text
            
        except Exception as e:
            logger.error(f"Error generating caption: {e}")
            return None
