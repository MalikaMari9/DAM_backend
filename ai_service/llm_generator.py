"""Ollama LLM Generator for natural language responses.

This module takes structured data from the inference engines and
passes it to a local Ollama instance to generate rich, conversational
Markdown responses.
"""

import json
import requests
from typing import Optional

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"

class OllamaGenerator:
    def __init__(self):
        self.model = self._get_best_model()
        if self.model:
            print(f"  [OK] Ollama LLM connected! Using model: {self.model}")
        else:
            print("  [WARN] Ollama not detected or no models found. Will fall back to standard text.")

    def _get_best_model(self) -> Optional[str]:
        """Detect available models and pick the best one for fast chat."""
        try:
            resp = requests.get(OLLAMA_TAGS_URL, timeout=2)
            if resp.status_code == 200:
                models = [m['name'] for m in resp.json().get('models', [])]
                if not models:
                    return None
                
                # Preferred order: fast but capable models
                preferences = ['llama3.2', 'llama3.1', 'llama3', 'mistral', 'gemma2']
                for pref in preferences:
                    for m in models:
                        if pref in m.lower():
                            return m
                return models[0]  # Just pick the first one if no preference matches
        except Exception:
            return None
        return None

    def is_available(self) -> bool:
        return self.model is not None

    def generate_response(self, intent: str, structured_data: dict, user_message: str, fallback_answer: str, messages: Optional[list] = None) -> str:
        """Generate a conversational response using Ollama."""
        if not self.is_available():
            return fallback_answer

        prompt = self._build_prompt(intent, structured_data, user_message, messages)

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.4, # Keep it factual
                "top_p": 0.9
            }
        }

        try:
            resp = requests.post(OLLAMA_URL, json=payload, timeout=60)
            if resp.status_code == 200:
                return resp.json().get('response', fallback_answer).strip()
        except Exception as e:
            print(f"Ollama generation failed: {e}")
            
        return fallback_answer

    def _build_prompt(self, intent: str, data: dict, user_message: str, messages: Optional[list] = None) -> str:
        """Construct the LLM prompt based on the intent and data."""
        
        system_instructions = (
            "You are a strict data reporting API. You do not speak conversationally. You only output raw Markdown facts.\n\n"
            "CRITICAL RULES:\n"
            "1. NEVER use the words 'I', 'me', 'my', 'you', 'here is', 'I am sorry', 'as an AI'.\n"
            "2. DO NOT write introductory or concluding paragraphs. If the first word of your response is not a fact or a bullet point, you have failed.\n"
            "3. BE EXTREMELY CONCISE. Present everything as short bullet points (•).\n"
            "4. Separate every single bullet point with double newlines (\\n\\n).\n"
            "5. NO Markdown tables.\n"
            "6. ONLY use the numbers provided in the JSON data. Do not hallucinate."
        )

        prompt = f"{system_instructions}\n\n"
        
        if messages:
            prompt += "CONVERSATION HISTORY:\n"
            for msg in messages[-5:]:  # Include up to the last 5 messages for context
                role = "AI" if msg.get("role") == "ai" else "USER"
                prompt += f"{role}: {msg.get('content')}\n"
            prompt += "\n"
            
        prompt += f"CURRENT USER QUESTION: \"{user_message}\"\n\n"
        prompt += f"DATA TO USE (JSON):\n{json.dumps(data, indent=2)}\n\n"

        if intent == 'best_month':
            prompt += "GUIDANCE: List the best and worst months using bullet points. Explain why in one short sentence."
        elif intent == 'worst_month':
            prompt += "GUIDANCE: List the most polluted months using bullet points. Give one short safety tip."
        elif intent == 'trend':
            prompt += "GUIDANCE: State if pollution is better or worse. Use bullet points to show the trend data."
        elif intent == 'comparison':
            prompt += "GUIDANCE: Compare the countries using bullet points. State clearly which is worse."
        elif intent in ('predict_pm25', 'predict_pm25_monthly'):
            prompt += "GUIDANCE: State the PM2.5 level and AQI category immediately using bullet points. Do not write filler text."
        elif intent == 'health_risk':
            prompt += "GUIDANCE: List total deaths and the top 3 diseases using bullet points. Do not write a concluding summary paragraph."

        prompt += "\n\nYOUR RESPONSE:\n"
        return prompt
