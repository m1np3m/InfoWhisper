from langchain.chains import create_retrieval_chain
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from langchain_qdrant import QdrantVectorStore
from langchain.chains.combine_documents import create_stuff_documents_chain
import os

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from dotenv import load_dotenv
from modules.query_manager import QueryGenerator
from modules.redis_manager import RedisManager



load_dotenv() 
os.environ["LANGFUSE_SECRET_KEY"]
os.environ["LANGFUSE_PUBLIC_KEY"]
os.environ["LANGFUSE_HOST"] 
lf = Langfuse()        # hoặc lf = get_client()
handler = CallbackHandler() 


class RAGPipelineSetup:
    def __init__(self, qdrant_url, qdrant_api_key, gemini_api_key, hf_api_key, 
                 hf_model_name="BAAI/bge-m3",redis_url="redis://localhost:6379"):
        self.QDRANT_URL = qdrant_url
        self.QDRANT_API_KEY = qdrant_api_key
        self.GEMINI_API_KEY = gemini_api_key
        self.HF_API_KEY = hf_api_key
        self.HF_MODEL_NAME = hf_model_name
        self.embeddings = self.load_embeddings()
        self.pipe = self.load_model_pipeline()
        self.prompt = self.load_prompt_template()
        self.current_source = None  # Initialize current source as None
        self.redis_manager = RedisManager(redis_url)
        self.query_generator = QueryGenerator(gemini_api_key)
    def load_embeddings(self):
        # Use HuggingFaceEndpointEmbeddings for API-based embeddings
        embeddings = HuggingFaceEndpointEmbeddings(
             model=self.HF_MODEL_NAME,
             task="feature-extraction",
             huggingfacehub_api_token=self.HF_API_KEY
        )
        #embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")
        return embeddings

    def load_retriever(self, retriever_name):
        # Initialize Qdrant client
        client = QdrantClient(
            url=self.QDRANT_URL,
            api_key=self.QDRANT_API_KEY,
            prefer_grpc=False
        )

        # Create vector store for querying
        db = QdrantVectorStore(
            client=client,
            embedding=self.embeddings,
            collection_name=retriever_name,
            content_payload_key="page_content",  # Key for content
    
        )

        # Configure retriever to get up to 5 results with MMR search
        retriever = db.as_retriever(
            search_kwargs={"k": 5}
        )
        return retriever

    def load_model_pipeline(self, max_output_tokens=1024):
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-lite",
            temperature=0,
            max_output_tokens=max_output_tokens,
            api_key=self.GEMINI_API_KEY,  # đổi từ google_api_key thành api_key
            #client_options={"api_endpoint": "https://gateway.helicone.ai"},
            # additional_headers={
            #     "helicone-auth": f"Bearer sk-helicone-7z6guyy-scsul3i-sdoousq-gwjriui",
            #     "helicone-target-url": "https://generativelanguage.googleapis.com"
            # },
            #transport="rest",
            name="Generation"
        )


        return llm

    def load_prompt_template(self):
        # Structure prompt for assistant
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
        # Create Retrieval Augmented Generation chain
        rag_chain = create_retrieval_chain(
            retriever=retriever,
            combine_docs_chain=create_stuff_documents_chain(llm, prompt)
        ).with_config({
        "run_name": "RAG_FullPipeline_Onrender",
        "callbacks": [handler]
        })
        
        return rag_chain

    def rag(self, source):
        # If current source hasn't changed, return existing pipeline
        if source == self.current_source:
            return self.rag_pipeline
        else:
            # If source changed, recreate pipeline components
            self.retriever = self.load_retriever(retriever_name=source)
            self.pipe = self.load_model_pipeline()
            self.prompt = self.load_prompt_template()
            self.rag_pipeline = self.load_rag_pipeline(llm=self.pipe, retriever=self.retriever, prompt=self.prompt)
            self.current_source = source  # Update current source
            return self.rag_pipeline
    
    # Function to debug retrieved documents
    def debug_retrieve(self, source, query):
        if source != self.current_source:
            self.retriever = self.load_retriever(retriever_name=source)
            self.current_source = source
            
        docs = self.retriever.get_relevant_documents(query)
        return docs
    
    def rag_with_history(self, source, user_question, session_id):
        """
        RAG with chat history optimization
        
        Args:
            source: Data source name
            user_question: User's question
            session_id: Session identifier
            
        Returns:
            Response with optimized query
        """
        try:
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
            
            # Save to Redis
            self.redis_manager.save_message(session_id, "user", user_question)
            
            # Format sources for saving
            sources = self._format_sources_for_redis(response)
            self.redis_manager.save_message(session_id, "assistant", response["answer"], sources)
            
            return response, optimized_query
            
        except Exception as e:
            logger.error(f"Error in RAG with history: {e}")
            # Fallback to regular RAG
            rag_pipeline = self.rag(source)
            inputs = {"input": user_question}
            response = rag_pipeline.invoke(inputs)
            return response, user_question
    
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

