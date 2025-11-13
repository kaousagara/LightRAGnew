"""
Multimodal Content Processors for LightRAG

This module provides lightweight processors for handling multimodal content
including tables, images, charts, and equations without requiring RAG-Anything.
"""

import base64
import re
from typing import Dict, Any, Optional, Tuple, Callable
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class TableProcessor:
    """Processor for extracting and enriching table content"""
    
    def __init__(self, llm_func: Callable):
        self.llm_func = llm_func
    
    async def process_table(self, table_text: str, context: str = "") -> Tuple[str, Dict[str, Any]]:
        """
        Process table content and generate enriched description
        
        Args:
            table_text: Raw table content (Markdown or plain text)
            context: Optional context about the table
            
        Returns:
            Tuple of (description, metadata)
        """
        try:
            prompt = f"""Analyze the following table and provide:
1. A clear description of what the table represents
2. Key insights and patterns in the data
3. Any notable relationships or trends

Table:
{table_text}

{f'Context: {context}' if context else ''}

Provide a concise but informative analysis."""

            response = await self.llm_func(
                prompt=prompt,
                system_prompt="You are a data analyst expert at interpreting tables and extracting insights."
            )
            
            metadata = {
                "type": "table",
                "original_content": table_text[:500],  # First 500 chars
                "processed": True
            }
            
            return response, metadata
            
        except Exception as e:
            logger.error(f"Error processing table: {e}")
            return table_text, {"type": "table", "processed": False, "error": str(e)}


class ImageProcessor:
    """Processor for extracting information from images and charts"""
    
    def __init__(self, vision_llm_func: Callable):
        self.vision_llm_func = vision_llm_func
    
    async def process_image(
        self, 
        image_path: Path, 
        caption: str = "",
        prompt_override: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Process image content using vision-capable LLM
        
        Args:
            image_path: Path to the image file
            caption: Optional caption for the image
            prompt_override: Custom prompt (default uses comprehensive analysis)
            
        Returns:
            Tuple of (description, metadata)
        """
        try:
            # Read and encode image as base64
            with open(image_path, "rb") as img_file:
                image_data = base64.b64encode(img_file.read()).decode('utf-8')
            
            default_prompt = f"""Analyze this image/chart and provide:
1. What type of visual content is this (photo, chart, diagram, etc.)?
2. What information or data does it convey?
3. Key elements, patterns, or insights visible in the image
4. Any text, labels, or captions visible

{f'Image caption: {caption}' if caption else ''}

Provide a detailed but concise analysis."""

            prompt = prompt_override or default_prompt
            
            response = await self.vision_llm_func(
                prompt=prompt,
                image_data=image_data,
                system_prompt="You are an expert at analyzing visual content including charts, graphs, diagrams, and images."
            )
            
            metadata = {
                "type": "image",
                "caption": caption,
                "file_path": str(image_path),
                "processed": True
            }
            
            return response, metadata
            
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            fallback = f"Image: {caption}" if caption else f"Image from {image_path.name}"
            return fallback, {"type": "image", "processed": False, "error": str(e)}


class EquationProcessor:
    """Processor for mathematical equations and formulas"""
    
    def __init__(self, llm_func: Callable):
        self.llm_func = llm_func
    
    async def process_equation(self, equation_text: str, format_type: str = "LaTeX") -> Tuple[str, Dict[str, Any]]:
        """
        Process mathematical equation and provide explanation
        
        Args:
            equation_text: The equation/formula text
            format_type: Format (LaTeX, MathML, plain text)
            
        Returns:
            Tuple of (description, metadata)
        """
        try:
            prompt = f"""Analyze this mathematical equation/formula:

{equation_text}

Format: {format_type}

Provide:
1. What the equation represents
2. Explanation of variables and components
3. Context or application of this formula
4. Any key insights

Be clear and concise."""

            response = await self.llm_func(
                prompt=prompt,
                system_prompt="You are a mathematics expert skilled at explaining formulas and equations."
            )
            
            metadata = {
                "type": "equation",
                "format": format_type,
                "original": equation_text,
                "processed": True
            }
            
            return response, metadata
            
        except Exception as e:
            logger.error(f"Error processing equation: {e}")
            return equation_text, {"type": "equation", "processed": False, "error": str(e)}


class MultimodalContentExtractor:
    """Main extractor for detecting and processing multimodal content"""
    
    def __init__(
        self, 
        llm_func: Callable,
        vision_llm_func: Optional[Callable] = None,
        enable_tables: bool = True,
        enable_images: bool = True,
        enable_equations: bool = True
    ):
        self.llm_func = llm_func
        self.vision_llm_func = vision_llm_func or llm_func
        
        self.table_processor = TableProcessor(llm_func) if enable_tables else None
        self.image_processor = ImageProcessor(self.vision_llm_func) if enable_images else None
        self.equation_processor = EquationProcessor(llm_func) if enable_equations else None
        
    def detect_tables(self, text: str) -> list:
        """Detect table-like structures in text"""
        tables = []
        
        # Detect markdown tables
        markdown_table_pattern = r'\|.+\|[\r\n]+\|[-:\s|]+\|[\r\n]+(?:\|.+\|[\r\n]+)+'
        markdown_tables = re.findall(markdown_table_pattern, text, re.MULTILINE)
        tables.extend([{"type": "markdown", "content": t} for t in markdown_tables])
        
        # Detect tab-separated or aligned content that looks like a table
        lines = text.split('\n')
        potential_table = []
        for i, line in enumerate(lines):
            tab_count = line.count('\t')
            if tab_count >= 2:  # Likely a table row
                potential_table.append(line)
            elif potential_table and len(potential_table) >= 3:
                # Found a table with at least 3 rows
                tables.append({"type": "tab_separated", "content": '\n'.join(potential_table)})
                potential_table = []
            else:
                potential_table = []
                
        return tables
    
    def detect_equations(self, text: str) -> list:
        """Detect mathematical equations in text"""
        equations = []
        
        # LaTeX-style equations
        latex_patterns = [
            r'\$\$(.+?)\$\$',  # Display math
            r'\$(.+?)\$',  # Inline math
            r'\\begin\{equation\}(.+?)\\end\{equation\}',  # Equation environment
        ]
        
        for pattern in latex_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            equations.extend([{"type": "latex", "content": m.strip()} for m in matches])
            
        return equations
    
    async def enrich_content(self, text: str) -> Tuple[str, Dict[str, Any]]:
        """
        Detect and enrich multimodal content in text
        
        Args:
            text: Input text potentially containing tables, equations, etc.
            
        Returns:
            Tuple of (enriched_text, metadata)
        """
        enriched_text = text
        metadata = {
            "tables_processed": 0,
            "equations_processed": 0,
            "enrichments": []
        }
        
        try:
            # Process tables
            if self.table_processor:
                tables = self.detect_tables(text)
                for table_info in tables:
                    description, table_meta = await self.table_processor.process_table(
                        table_info["content"]
                    )
                    # Append enriched description after the table
                    enriched_text = enriched_text.replace(
                        table_info["content"],
                        f"{table_info['content']}\n\n[Table Analysis]: {description}\n"
                    )
                    metadata["tables_processed"] += 1
                    metadata["enrichments"].append(table_meta)
            
            # Process equations
            if self.equation_processor:
                equations = self.detect_equations(text)
                for eq_info in equations:
                    description, eq_meta = await self.equation_processor.process_equation(
                        eq_info["content"],
                        format_type=eq_info["type"]
                    )
                    # Add explanation near the equation
                    original = eq_info["content"]
                    if eq_info["type"] == "latex":
                        original = f"${original}$"  # Restore delimiters
                    enriched_text = enriched_text.replace(
                        original,
                        f"{original}\n[Equation Explanation]: {description}\n"
                    )
                    metadata["equations_processed"] += 1
                    metadata["enrichments"].append(eq_meta)
                    
        except Exception as e:
            logger.error(f"Error enriching content: {e}")
            metadata["error"] = str(e)
        
        return enriched_text, metadata
