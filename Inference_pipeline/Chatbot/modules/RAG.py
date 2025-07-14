from langchain.chains import create_retrieval_chain
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from langchain_qdrant import QdrantVectorStore
from langchain.chains.combine_documents import create_stuff_documents_chain
import os
import logging

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from dotenv import load_dotenv
from modules.query_manager import QueryGenerator
from modules.redis_manager import RedisManager
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

load_dotenv() 
os.environ["LANGFUSE_SECRET_KEY"]
os.environ["LANGFUSE_PUBLIC_KEY"]
os.environ["LANGFUSE_HOST"] 
lf = Langfuse()        
handler = CallbackHandler() 

class RAGPipelineSetup:
    def __init__(self, qdrant_url, qdrant_api_key, gemini_api_key, hf_api_key, 
                 hf_model_name="BAAI/bge-m3", redis_url="redis://localhost:6380"):
        self.QDRANT_URL = qdrant_url
        self.QDRANT_API_KEY = qdrant_api_key
        self.GEMINI_API_KEY = gemini_api_key
        self.HF_API_KEY = hf_api_key
        self.HF_MODEL_NAME = hf_model_name
        self.embeddings = self.load_embeddings()
        self.pipe = self.load_model_pipeline()
        self.prompt = self.load_prompt_template()
        self.current_source = None
        self.redis_manager = RedisManager(redis_url)
        self.query_generator = QueryGenerator(gemini_api_key)
        
    def load_embeddings(self):
        embeddings = HuggingFaceEndpointEmbeddings(
             model=self.HF_MODEL_NAME,
             task="feature-extraction",
             huggingfacehub_api_token=self.HF_API_KEY
        )
        return embeddings

    def load_retriever(self, retriever_name):
        client = QdrantClient(
            url=self.QDRANT_URL,
            api_key=self.QDRANT_API_KEY,
            prefer_grpc=False
        )

        db = QdrantVectorStore(
            client=client,
            embedding=self.embeddings,
            collection_name=retriever_name,
            content_payload_key="page_content",
        )

        retriever = db.as_retriever(
            search_kwargs={"k": 5}
        )
        return retriever

    def load_model_pipeline(self, max_output_tokens=1024):
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-lite",
            temperature=0,
            max_output_tokens=max_output_tokens,
            api_key=self.GEMINI_API_KEY,
            name="Generation"
        )
        return llm

    def load_prompt_template(self):
        query_template = '''
      ### Bối cảnh tin tức:
      {context}

      ### Câu hỏi của người dùng:
      {input}

      ### Hướng dẫn cho Trợ lý:
      1. Đọc kỹ câu hỏi và xác định rõ mục đích của người dùng.
      2. Tìm kiếm thông tin chính xác và liên quan nhất trong phần bối cảnh phía trên.
      3. Trả lời ngắn gọn, rõ ràng và đúng trọng tâm để giải đáp câu hỏi.
      4. Nếu không thể tìm thấy câu trả lời trực tiếp từ bối cảnh, hãy lịch sự thông báo và có thể gợi ý hướng tìm hiểu thêm.
      5. Luôn trả lời bằng tiếng Việt.
      6. Nếu phần bối cảnh không có thông tin hoặc quá ít, hãy thông báo cho người dùng một cách khéo léo.

      ### Trả lời:
        '''
        
        prompt = PromptTemplate(template=query_template, input_variables=["context", "input"])
        return prompt

    def load_rag_pipeline(self, llm, retriever, prompt):
        rag_chain = create_retrieval_chain(
            retriever=retriever,
            combine_docs_chain=create_stuff_documents_chain(llm, prompt)
        ).with_config({
        "run_name": "RAG_FullPipeline_Onrender",
        "callbacks": [handler]
        })
        
        return rag_chain

    def rag(self, source):
        if source == self.current_source:
            return self.rag_pipeline
        else:
            self.retriever = self.load_retriever(retriever_name=source)
            self.pipe = self.load_model_pipeline()
            self.prompt = self.load_prompt_template()
            self.rag_pipeline = self.load_rag_pipeline(llm=self.pipe, retriever=self.retriever, prompt=self.prompt)
            self.current_source = source
            return self.rag_pipeline
    
    def debug_retrieve(self, source, query):
        if source != self.current_source:
            self.retriever = self.load_retriever(retriever_name=source)
            self.current_source = source
            
        docs = self.retriever.get_relevant_documents(query)
        return docs
    
    def rag_with_history_and_cache(self, source: str, user_question: str, session_id: str, 
                                  use_cache: bool = True, cache_ttl: int = 600) -> Tuple[Dict, str, bool]:
        """
        RAG with chat history optimization and caching
        
        Args:
            source: Data source name
            user_question: User's question
            session_id: Session identifier
            use_cache: Whether to use cache
            cache_ttl: Cache time to live in seconds (default: 10 minutes)
            
        Returns:
            Tuple of (response, optimized_query, cache_hit)
        """
        try:
            cache_hit = False
            
            # 1. Check cache first if enabled
            if use_cache:
                cached_response = self.redis_manager.get_cached_response(user_question, source)
                if cached_response:
                    logger.info(f"Cache hit for query: {user_question[:50]}...")
                    
                    # Return cached response
                    response = {
                    "answer": cached_response["response"],
                    "context": [],  # Nếu bạn không muốn context, vẫn để rỗng
                    "sources": cached_response.get("sources", [])
                    }

                    
                    # Save to chat history
                    self.redis_manager.save_message(session_id, "user", user_question)
                    self.redis_manager.save_message(session_id, "assistant", 
                                                  cached_response["response"], 
                                                  cached_response["sources"])
                    
                    return response, cached_response.get("optimized_query", user_question), True
                
                # 2. Check for similar queries if no exact match
                similar_queries = self.redis_manager.find_similar_cached_queries(user_question, source, limit=3)
                if similar_queries:
                    logger.info(f"Found {len(similar_queries)} similar cached queries")
                    # For now, we'll use the first similar query
                    # You can implement more sophisticated similarity scoring here
                    similar_data = similar_queries[0]["cached_data"]
                    
                    response = {
                        "answer": similar_data["response"],
                        "context": []
                    }
                    
                    # Save to chat history
                    self.redis_manager.save_message(session_id, "user", user_question)
                    self.redis_manager.save_message(session_id, "assistant", 
                                                  similar_data["response"], 
                                                  similar_data["sources"])
                    
                    return response, similar_data.get("optimized_query", user_question), True
            
            # 3. No cache hit, proceed with normal RAG
            logger.info(f"No cache hit, processing query: {user_question[:50]}...")
            
            # Get recent chat history
            recent_conversations = self.redis_manager.get_last_n_conversations(session_id, n=5)
            
            # Generate optimized query if we have chat history
            if recent_conversations:
                optimized_query = self.query_generator.generate_optimized_query(
                    user_question, recent_conversations
                )
            else:
                optimized_query = user_question
            
            # Get RAG pipeline
            rag_pipeline = self.rag(source)
            
            # Execute with optimized query
            inputs = {"input": optimized_query}
            response = rag_pipeline.invoke(inputs)
            
            # Format sources for saving
            sources = self._format_sources_for_redis(response)
            
            # Save to chat history
            self.redis_manager.save_message(session_id, "user", user_question)
            self.redis_manager.save_message(session_id, "assistant", response["answer"], sources)
            
            # Cache the response if enabled
            if use_cache:
                self.redis_manager.cache_response(
                    query=user_question,
                    source=source,
                    response=response["answer"],
                    sources=sources,
                    optimized_query=optimized_query,
                    ttl=cache_ttl
                )
                logger.info(f"Response cached for query: {user_question[:50]}...")
            
            return response, optimized_query, cache_hit
            
        except Exception as e:
            logger.error(f"Error in RAG with history and cache: {e}")
            # Fallback to regular RAG
            rag_pipeline = self.rag(source)
            inputs = {"input": user_question}
            response = rag_pipeline.invoke(inputs)
            return response, user_question, False
    
    def rag_with_history(self, source, user_question, session_id):
        """
        Backward compatibility method - uses cache by default
        """
        response, optimized_query, cache_hit = self.rag_with_history_and_cache(
            source, user_question, session_id, use_cache=True
        )
        return response, optimized_query
    
    def _format_sources_for_redis(self, response):
        """Format sources for Redis storage"""
        if not isinstance(response, dict) or "context" not in response:
            return []

        sources = []
        for doc in response["context"]:
            if hasattr(doc, 'metadata') and isinstance(doc.metadata, dict):
                metadata = doc.metadata
                source_info = {
                    'title': metadata.get('title', ''),
                    'author': metadata.get('author', ''),
                    'category': metadata.get('category', ''),
                    'url': metadata.get('url', ''),
                    'publish_date': metadata.get('publish_date', ''),
                    'description': metadata.get('description', ''),
                    'main_image': metadata.get('main_image', ''),
                    'document_id': metadata.get('document_id', '')
                }
                sources.append(source_info)
        return sources
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        return self.redis_manager.get_cache_stats()
    
    def clear_cache(self) -> None:
        """Clear all cached queries"""
        self.redis_manager.clear_cache()
    
    def clear_expired_cache(self) -> int:
        """Clear expired cache entries"""
        return self.redis_manager.clear_expired_cache()