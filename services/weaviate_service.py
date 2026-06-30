import os
import time
from typing import List, Dict, Any
import weaviate
from sentence_transformers import SentenceTransformer
from config import settings  #  Unified Configurations Injection

class WeaviateIngestionService:
    def __init__(self):
        """
        Initializes the local embedding model and establishes a secure 
        connection with the remote Weaviate Cloud Cluster using unified configurations.
        """
        # 1. Load the lightweight local embedding model
        print(f"[{time.strftime('%X')}] Loading local SentenceTransformer model ('all-MiniLM-L6-v2')...")
        self.embed_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        # 2. Extract cluster configurations from unified global settings contract
        cluster_url = settings.WEAVIATE_URL
        api_key = settings.WEAVIATE_API_KEY
        
        if not cluster_url or not api_key:
            raise ValueError("Missing WEAVIATE_URL or WEAVIATE_API_KEY in configuration mappings.")
            
        #  Sanitizing URL context boundaries carefully
        clean_url = cluster_url.replace("https://", "").replace("http://", "").strip().rstrip('/')
        
        print(f"[{time.strftime('%X')}] Establishing secure connection link to: {clean_url}")
        
        #  FIXED: Kept ONLY the single sanitized client instantiation handshake
        self.client = weaviate.connect_to_weaviate_cloud(
            cluster_url=clean_url,
            auth_credentials=weaviate.auth.AuthApiKey(api_key=api_key),
            additional_config=weaviate.config.AdditionalConfig(
                timeout=weaviate.config.Timeout(connection=30, read=60) # Gives up to 60s for slow cloud payloads
            )
        )
        
        # Define our unique target Collection (Class) name
        self.collection_name = "Judgments"
        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        """
        Checks if the 'Judgments' collection is configured in the cluster.
        If missing, creates it with explicit structural property configurations.
        """
        if not self.client.collections.exists(self.collection_name):
            print(f"[{time.strftime('%X')}] Class '{self.collection_name}' not found. Initializing schema index definition...")
            
            # Creating collection without any default vectorizer since we pass custom vectors
            self.client.collections.create(
                name=self.collection_name,
                description="Storage for segmented Peshawar High Court judgments mapped with dynamic metadata vectors.",
            )
            print(f"[{time.strftime('%X')}] Collection '{self.collection_name}' created successfully.")

    def case_exists(self, case_id: str) -> bool:
        """
        Queries the Weaviate Cloud Index to check if chunks for the given 
        case_id are already ingested. Returns True if found, False otherwise.
        """
        try:
            collection = self.client.collections.get(self.collection_name)
            
            # Formulating a high-speed metadata property filter query
            response = collection.query.fetch_objects(
                filters=weaviate.classes.query.Filter.by_property("case_id").equal(case_id),
                limit=1,
                return_properties=[]  # We don't need properties data, just the existence check
            )
            
            # If objects array length is greater than 0, it means it already exists
            if len(response.objects) > 0:
                return True
            return False
            
        except Exception as e:
            print(f"[WARNING] Database check failed for case_id {case_id}: {str(e)}")
            return False  # Fallback to False to prevent breaking the pipeline if DB drops

    def batch_ingest_chunks(self, processed_payloads: List[Dict[str, Any]]):
        """
        Generates text embedding vectors locally and injects the array bundles 
        into the Weaviate Cloud cluster using optimized batch operations.
        """
        print(f"[{time.strftime('%X')}] Initializing high-speed batch upload transaction...")
        collection = self.client.collections.get(self.collection_name)
        
        # Open an optimized batch insertion execution layer
        with collection.batch.dynamic() as batch:
            for idx, payload in enumerate(processed_payloads):
                text_to_vectorize = payload["text_content"]
                
                # A. Generate vector embeddings representation locally
                vector = self.embed_model.encode(text_to_vectorize).tolist()
                
                # B. Compile property metadata object excluding technical track fields
                properties = {
                    "case_id": payload["case_id"],
                    "case_title": payload["case_title"],
                    "google_drive_url": payload["google_drive_url"],
                    "text_content": payload["text_content"],
                    "chunk_index": payload["chunk_index"]
                }
                
                # C. Stage structural entity into the current transactional container safely
                batch.add_object(
                    properties=properties,
                    vector=vector,
                    uuid=None  # Weaviate will auto-generate unique hashes automatically
                )
                
        print(f"[{time.strftime('%X')}] Successfully pushed {len(processed_payloads)} vectors to Weaviate Cloud Index.")

    def close(self):
        """
         Added missing closure hook contract for smooth Starlette lifecycle teardown routines.
        """
        if hasattr(self, "client") and self.client:
            print(f"[{time.strftime('%X')}] Terminating connection socket pool link to Weaviate Cloud...")
            self.client.close()