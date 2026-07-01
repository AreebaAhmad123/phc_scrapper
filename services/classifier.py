from groq import Groq
from config import settings
import json

class QueryClassifierService:
    def __init__(self):
        """
        Initializes the Groq client for low-latency query domain classification.
        """
        groq_key = settings.LLM_API_KEY
        if not groq_key:
            raise ValueError("Missing LLM_API_KEY or GROQ_API_KEY inside configuration settings.")
        self.client = Groq(api_key=groq_key)
        self.model_name = settings.LLM_MODEL if settings.LLM_MODEL else "llama-3.3-70b-versatile"

    def classify_query(self, user_query: str) -> dict:
        """
        Classifies an incoming user query to defend the legal domain firewall.
        Categorizes query into: 'RELEVANT_LEGAL', 'IRRELEVANT', or 'SYSTEM_META'.
        """
        system_instructions = (
            "You are an automated security routing firewall for the Peshawar High Court Legal AI System.\n"
            "Your sole task is to classify incoming user queries into exactly one of three categories.\n\n"
            "CRITERIA DEFINITIONS:\n"
            "1. 'RELEVANT_LEGAL': Queries asking about judicial precedents, case statuses, judgments, "
            "Peshawar High Court operations, constitutional law, FIRs, legal provisions, or Pakistani jurisprudence.\n"
            "2. 'IRRELEVANT': Generic questions, chit-chat, programming, math, recipes, logic puzzles, or non-legal topics "
            "outside the scope of high court judgments.\n"
            "3. 'SYSTEM_META': Inquiries testing the system's capabilities, version numbers, uptime, or metadata rules.\n\n"
            "STRICT OUTPUT FORMAT:\n"
            "You must return a raw JSON object with exactly two keys: 'category' and 'reason'. Do not include any markdown wrappers, backticks, or extra prose.\n"
            "Example:\n"
            "{\"category\": \"IRRELEVANT\", \"reason\": \"The query asks about a cooking recipe which is completely off-domain for judicial records.\"}"
        )

        try:
            completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_instructions},
                    {"role": "user", "content": f"Query to classify: '{user_query}'"}
                ],
                model=self.model_name,
                temperature=0.0,  # Absolute determinism
                response_format={"type": "json_object"}
            )
            
            raw_response = completion.choices[0].message.content.strip()
            parsed_result = json.loads(raw_response)
            return parsed_result

        except Exception as e:
            # Fallback to safe pass-through in case of API glitch
            print(f"[CLASSIFIER WARNING] Classification failed: {str(e)}. Falling back to safe routing.")
            return {"category": "RELEVANT_LEGAL", "reason": "Fallback allowed due to parser exception."}