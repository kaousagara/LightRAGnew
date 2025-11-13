"""
Multimodal Processing Configuration for LightRAG

This module provides configuration and utilities for multimodal document processing
including tables, images, charts, and equations.
"""

import os
from typing import Optional


class MultimodalConfig:
    """Configuration for multimodal processing"""
    
    @staticmethod
    def is_enabled() -> bool:
        """Check if multimodal processing is enabled"""
        return os.getenv("ENABLE_MULTIMODAL_PROCESSING", "false").lower() == "true"
    
    @staticmethod
    def is_image_processing_enabled() -> bool:
        """Check if image processing is enabled"""
        return os.getenv("ENABLE_IMAGE_PROCESSING", "true").lower() == "true"
    
    @staticmethod
    def is_table_processing_enabled() -> bool:
        """Check if table processing is enabled"""
        return os.getenv("ENABLE_TABLE_PROCESSING", "true").lower() == "true"
    
    @staticmethod
    def is_equation_processing_enabled() -> bool:
        """Check if equation processing is enabled"""
        return os.getenv("ENABLE_EQUATION_PROCESSING", "true").lower() == "true"
    
    @staticmethod
    def get_vision_model() -> str:
        """Get the vision model to use for image/chart analysis"""
        return os.getenv("VISION_MODEL", "gpt-4o")
    
    @staticmethod
    def get_multimodal_llm_func(llm_model_func):
        """
        Get multimodal-capable LLM function for vision tasks
        
        This wraps the standard LLM function to support image inputs
        """
        def vision_model_func(prompt, system_prompt=None, history_messages=[], image_data=None, **kwargs):
            if image_data:
                # For multimodal requests with image data
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                })
                
                # Call LLM with vision-specific parameters
                return llm_model_func(
                    prompt="",
                    messages=messages,
                    **kwargs
                )
            else:
                # Regular text-only request
                return llm_model_func(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    history_messages=history_messages,
                    **kwargs
                )
        
        return vision_model_func


# Global configuration instance
multimodal_config = MultimodalConfig()
