import time
from typing import Dict, Any, List
import weaviate
from sentence_transformers import SentenceTransformer
from groq import Groq
from config import settings 

class RAGEngineService:
    def __init__(self):
        """
        Initializes the shared local embedding engine, connects to the Weaviate Cloud index,
        and boots up the ultra-fast Groq API client instance utilizing central configurations.
        """
        print(f"[{time.strftime('%X')}] Booting RAG Ingestion & Inference components...")
        
        # 1. Local Vectorizer Setup
        self.embed_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        # 2. Weaviate Cloud Sanitization & Sockets
        cluster_url = settings.WEAVIATE_URL
        api_key = settings.WEAVIATE_API_KEY
        
        if not cluster_url or not api_key:
            raise ValueError("Missing WEAVIATE_URL or WEAVIATE_API_KEY in system settings mappings.")
            
        clean_url = cluster_url.replace("https://", "").replace("http://", "").strip().rstrip('/')
        
        self.weaviate_client = weaviate.connect_to_weaviate_cloud(
            cluster_url=clean_url,
            auth_credentials=weaviate.auth.AuthApiKey(api_key=api_key)
        )
        self.collection_name = "Judgments"
        
        # 3. Groq Architecture Authentication Engine
        groq_key = settings.LLM_API_KEY or settings.LLM_API_KEY
        if not groq_key:
            raise ValueError("Missing LLM_API_KEY variable configuration profile inside settings.")
        self.groq_client = Groq(api_key=groq_key)
        
        # Store model state as an instance property dynamically mapped to configurations
        self.model_name = settings.LLM_MODEL if settings.LLM_MODEL else "llama-3.3-70b-versatile"

    def retrieve_relevant_contexts(self, user_query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Converts the prompt to a dense semantic vector representation and extracts
        the top matched structural chunks from the cloud index.
        """
        # Vectorize the question locally
        query_vector = self.embed_model.encode(user_query).tolist()
        
        collection = self.weaviate_client.collections.get(self.collection_name)
        
        # Query Weaviate via near_vector calculation
        response = collection.query.near_vector(
            near_vector=query_vector,
            limit=top_k,
            return_properties=["case_id", "case_title", "google_drive_url", "text_content", "chunk_index"]
        )
        
        extracted_contexts = []
        for obj in response.objects:
            extracted_contexts.append(obj.properties)
            
        return extracted_contexts

    def generate_grounded_answer(self, question: str) -> Dict[str, Any]:
        """
        Main pipeline coordinator orchestrates chunk match constraints, constructs fully cited prompt 
        structures, and commands Groq Llama model arrays to answer securely without hallucinating.
        """
        # Phase A: Database extraction vector layer
        contexts = self.retrieve_relevant_contexts(question, top_k=3)
        
        if not contexts:
            return {
                "answer": "Based on the current indexed records, I am unable to locate specific precedent facts for this inquiry.",
                "citations": []
            }
            
        # FIXED: Reset broken indentation alignment blocks for compilation
        context_str = ""
        citations_tracker = []
        
        for idx, ctx in enumerate(contexts):
            context_str += f"\n--- [DOCUMENT REFERENCE KEY #{idx+1}] ---\n"
            context_str += f"Case ID: {ctx.get('case_id')}\n"
            context_str += f"Title: {ctx.get('case_title')}\n"
            context_str += f"Content: {ctx.get('text_content')}\n"
            
            # Record structural variables to map source references to user interface
            citations_tracker.append({
                "source_index": idx + 1,
                "case_id": ctx.get("case_id"),
                "case_title": ctx.get("case_title"),
                "document_backup_link": ctx.get("google_drive_url")
            })

        # Phase C: Constructing Strict Legal Grounding Prompts (Strict Anti-Hallucination)
        system_instructions = (
            "You are an expert Judicial Research AI Assistant serving the Peshawar High Court. "
            "Your task is to analyze the user's legal inquiry based ONLY on the provided document references.\n\n"
            "STRICT GROUNDING DIRECTIVES:\n"
            "1. Answer the query thoroughly using legal facts found directly in the text snippets.\n"
            "2. Cite your sources directly inside the text paragraphs using matching bracket reference indices (e.g., [DOCUMENT REFERENCE KEY #1]).\n"
            "3. If the provided references do not contain the answer, state clearly: 'Based on the current indexed records, I am unable to locate specific precedent facts for this inquiry.' Do NOT synthesize answers or hallucinate legal provisions outside the provided context."
        )
        
        user_prompt = f"PROVIDED CONTEXT DOCUMENTS:\n{context_str}\n\nUSER QUESTION: {question}\n\nGROUNDED LEGAL RESPONSE:"

        # Phase D: Trigger Groq ultra-fast active model block configuration
        completion = self.groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": user_prompt}
            ],
            model=self.model_name,
            temperature=0.1,  # Kept minimal to enforce absolute factual precision
            max_tokens=1024
        )
        
        return {
            "answer": completion.choices[0].message.content,
            "citations": citations_tracker
        }

    def close(self):
        """Clean connection pool closures."""
        if hasattr(self, "weaviate_client") and self.weaviate_client:
            print(f"[{time.strftime('%X')}] Closing RAG service connection to Weaviate Cloud...")
            self.weaviate_client.close()