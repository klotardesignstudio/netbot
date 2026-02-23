import os
import textwrap
from typing import List, Dict, Any
from PIL import Image, ImageDraw, ImageFont
from core.logger import logger

class PillowRenderer:
    """Renderer responsible for generating internal carousel slides using Pillow."""
    
    def __init__(self, output_dir: str = "temp_slides"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        # 4:5 aspect ratio for Instagram Portrait
        self.width = 1080
        self.height = 1350
        # Default Colors (From brand.md)
        self.default_bg_color = (30, 30, 30)       # #1E1E1E Deep Charcoal
        self.default_text_color = (249, 249, 249)  # #F9F9F9 Pure Ghost
        
        # Vignette Overlay Cache
        self._vignette = None
        
        # Fonts
        self.font_title = self._load_font(90, "Inter-Regular.ttf")
        self.font_body = self._load_font(75, "Inter-Regular.ttf")
        self.font_handle = self._load_font(30, "Inter-Regular.ttf")

    def _load_font(self, size: int, filename: str):
        try:
            # Try to load the custom downloaded fonts
            font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "fonts", filename)
            return ImageFont.truetype(font_path, size)
        except:
            # Fallback
            try:
                return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
            except:
                return ImageFont.load_default()

    def _get_vignette_overlay(self):
        """Generates a radial gradient from center (0% opacity) to edges (15% black opacity)"""
        import math
        if self._vignette is not None:
            return self._vignette
            
        # Generate on a smaller texture for speed, then upscale
        w, h = self.width // 10, self.height // 10
        overlay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        pixels = overlay.load()
        cx, cy = w / 2, h / 2
        max_dist = math.hypot(cx, cy)
        
        for y in range(h):
            for x in range(w):
                dist = math.hypot(x - cx, y - cy)
                ratio = min(1.0, dist / max_dist)
                # Figma: 15% opacity overall -> 0.15 * 255 = ~38
                alpha = int(38 * ratio)
                pixels[x, y] = (0, 0, 0, alpha)
                
        self._vignette = overlay.resize((self.width, self.height), Image.Resampling.LANCZOS)
        return self._vignette

    def _hex_to_rgb(self, hex_color: str) -> tuple:
        hex_color = hex_color.lstrip('#')
        # If shorthand like #FFF
        if len(hex_color) == 3:
            hex_color = ''.join(c + c for c in hex_color)
        try:
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        except:
            return (0, 0, 0) # Fallback black

    def generate_carousel_slides(self, slide_contents: List[Dict[str, str]], 
                                 bg_color_hex: str = "#1E1E1E", 
                                 text_color_hex: str = "#F9F9F9",
                                 handle: str = "@guilhermezaia") -> List[str]:
        """
        Takes a list of JSON slide definitions and outputs the image file paths.
        Example: [{'titulo': 'Step 1', 'conteudo': 'Do this...'}, ...]
        """
        logger.info(f"Rendering {len(slide_contents)} internal slides with Pillow (Bg: {bg_color_hex}, Text: {text_color_hex})")
        paths = []
        
        # Parse dynamic colors or fallback to defaults
        bg_color_rgb = self._hex_to_rgb(bg_color_hex) if bg_color_hex else self.default_bg_color
        text_color_rgb = self._hex_to_rgb(text_color_hex) if text_color_hex else self.default_text_color
        
        for index, slide in enumerate(slide_contents):
            title = slide.get('titulo', '')
            content = slide.get('conteudo', '')
            
            # Create base image
            img = Image.new('RGB', (self.width, self.height), color=bg_color_rgb)
            
            # Apply Radial Gradient
            vignette = self._get_vignette_overlay()
            img.paste(vignette, (0, 0), vignette)
            
            draw = ImageDraw.Draw(img)
            
            # Prepare Text
            # We combine title and content for a fluid read, wrapped at ~22 chars wide depending on font
            wrapped_text = ""
            current_y = 0
            
            # Pre-calculate heights for vertical centering
            block_parts = []
            if title:
                w_title = textwrap.fill(title, width=18)
                bbox = draw.textbbox((0, 0), w_title, font=self.font_title)
                h = bbox[3] - bbox[1]
                block_parts.append((w_title, self.font_title, h))
            
            if content:
                w_content = textwrap.fill(content, width=22)
                bbox = draw.textbbox((0, 0), w_content, font=self.font_body)
                h = bbox[3] - bbox[1]
                block_parts.append((w_content, self.font_body, h))
                
            total_h = sum(p[2] for p in block_parts) + (60 if len(block_parts) > 1 else 0) # 60px padding between title/content
            
            # Draw vertically centered
            start_y = (self.height - total_h) // 2
            
            for text_chunk, font_to_use, chunk_h in block_parts:
                draw.text((100, start_y), text_chunk, font=font_to_use, fill=text_color_rgb, spacing=20)
                start_y += chunk_h + 60
            
            # Draw Footer Handle Pill
            bbox_h = draw.textbbox((0, 0), handle, font=self.font_handle)
            w_h = bbox_h[2] - bbox_h[0]
            h_h = bbox_h[3] - bbox_h[1]
            pad_x, pad_y = 25, 12
            
            is_last_slide = index == len(slide_contents) - 1
            
            if is_last_slide:
                # Center horizontally
                px = (self.width - w_h) // 2
            else:
                # Align left with text
                px = 100 + pad_x
                
            py = self.height - 150
            
            # Pill outline
            draw.rounded_rectangle([px - pad_x, py - pad_y, px + w_h + pad_x, py + h_h + pad_y], radius=25, outline=text_color_rgb, width=2)
            # Text handle
            draw.text((px, py), handle, font=self.font_handle, fill=text_color_rgb)
            
            # Draw Next Arrow (bottom right) ONLY if NOT last slide
            if not is_last_slide:
                ax, ay = self.width - 150, self.height - 130
                arrow_thickness = 4
                draw.line([(ax, ay), (ax + 50, ay)], fill=text_color_rgb, width=arrow_thickness)
                draw.line([(ax + 30, ay - 20), (ax + 50, ay)], fill=text_color_rgb, width=arrow_thickness)
                draw.line([(ax + 30, ay + 20), (ax + 50, ay)], fill=text_color_rgb, width=arrow_thickness)
            
            # Save
            file_path = os.path.join(self.output_dir, f"slide_{index + 1}.png")
            img.save(file_path)
            paths.append(file_path)
            
        logger.info(f"✅ Rendered {len(paths)} slides.")
        return paths
