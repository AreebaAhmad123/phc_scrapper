import time
from typing import Dict, Any, List
import weaviate
from sentence_transformers import SentenceTransformer, CrossEncoder
from groq import Groq
from config import settings 

class RAGEngineService:
    def __init__(self):
        """
        Initializes local embeddings, boots a local Cross-Encoder reranker model,
        connects to Weaviate Cloud with solid timeouts, and sets up the Groq client.
        """
        print(f"[{time.strftime('%X')}] Booting Advanced Stage 3 RAG Ingestion & Inference components...")
        
        # 1. Local Vectorizer & Reranker Setups
        self.embed_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        # Loading a highly optimized local cross-encoder model for deep semantic interaction scoring
        self.reranker_model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        
        # 2. Weaviate Cloud Sanitization & Sockets
        cluster_url = settings.WEAVIATE_URL
        api_key = settings.WEAVIATE_API_KEY
        
        if not cluster_url or not api_key:
            raise ValueError("Missing WEAVIATE_URL or WEAVIATE_API_KEY in system settings mappings.")
            
        clean_url = cluster_url.replace("https://", "").replace("http://", "").strip().rstrip('/')
        
        # Injected explicit Timeout profiles to cushion high-volume advanced queries
        self.weaviate_client = weaviate.connect_to_weaviate_cloud(
            cluster_url=clean_url,
            auth_credentials=weaviate.auth.AuthApiKey(api_key=api_key),
            additional_config=weaviate.config.AdditionalConfig(
                timeout=weaviate.config.Timeout(connection=30, read=60)
            )
        )
        self.collection_name = "Judgments"
        
        # 3. Groq Architecture Authentication Engine
        groq_key = settings.LLM_API_KEY
        if not groq_key:
            raise ValueError("Missing LLM_API_KEY variable configuration profile inside settings.")
        self.groq_client = Groq(api_key=groq_key)
        
        # Store model state as an instance property dynamically mapped to configurations
        self.model_name = settings.LLM_MODEL if settings.LLM_MODEL else "llama-3.3-70b-versatile"

    def retrieve_relevant_contexts(self, user_query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Executes a native Hybrid Search combining Vector + BM25 keyword matching,
        then processes candidate hits through a Cross-Encoder Reranker layer.
        """
        # Vectorize the question locally for the dense part of hybrid search
        query_vector = self.embed_model.encode(user_query).tolist()
        
        collection = self.weaviate_client.collections.get(self.collection_name)
        
        #  STEP 1: Execute Hybrid Search (50% Sparse BM25 Keyword, 50% Dense Vector)
        # We poll a larger pool (10 candidates) to allow the reranker space to filter effectively
        response = collection.query.hybrid(
            query=user_query,
            vector=query_vector,
            alpha=0.5,  # Balanced split between text matching and semantic vectors
            limit=10,
            return_properties=["case_id", "case_title", "google_drive_url", "text_content", "chunk_index"]
        )
        
        candidates = [obj.properties for obj in response.objects]
        
        if not candidates:
            return []
            
        #  STEP 2: Cross-Encoder Reranking Layer
        # Prepare pairs of (Query, Content Text) for cross-attention scoring
        rerank_pairs = [[user_query, doc.get("text_content", "")] for doc in candidates]
        
        # Compute exact interaction relevance scores natively
        scores = self.reranker_model.predict(rerank_pairs)
        
        # Bind scores back onto their parent properties matrices
        for idx, score in enumerate(scores):
            candidates[idx]["_rerank_score"] = float(score)
            
        # Sort candidates descending according to their computed cross-encoder interaction score
        candidates.sort(key=lambda x: x["_rerank_score"], reverse=True)
        
        # Return only the top_k requested configurations
        return candidates[:top_k]

    def generate_grounded_answer(self, question: str) -> Dict[str, Any]:
        """
        Main pipeline coordinator orchestrates advanced hybrid chunk extractions, 
        constructs cited prompt structures, and commands Groq to answer accurately.
        """
        # Phase A: Advanced Database extraction via Hybrid + Rerank flow
        contexts = self.retrieve_relevant_contexts(question, top_k=3)
        
        if not contexts:
            return {
                "answer": "Based on the current indexed records, I am unable to locate specific precedent facts for this inquiry.",
                "citations": []
            }
            
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