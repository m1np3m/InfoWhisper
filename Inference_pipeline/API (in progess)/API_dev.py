from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import os
from dotenv import load_dotenv
from RAG import RAGPipelineSetup

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="RAG API Service",
    description="API for Retrieval Augmented Generation using LangChain, Qdrant and Gemini",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Input models
class RAGQuery(BaseModel):
    query: str
    source: str  # Collection name in Qdrant

class DebugQuery(BaseModel):
    query: str
    source: str

# Response models
class RAGResponse(BaseModel):
    answer: str
    context_used: Optional[bool] = True

class Document(BaseModel):
    content: str
    metadata: Dict[str, Any]

class DebugResponse(BaseModel):
    query: str
    documents: List[Document]

# # API endpoints
# @app.get("/")
# async def root():
#     return {"message": "RAG API is running", "status": "ok"}

@app.post("/rag", response_model=RAGResponse)
async def process_rag_query(query_input: RAGQuery, rag_pipeline: RAGPipelineSetup = Depends(get_rag_pipeline)):
    try:
        # Process query using RAG pipeline
        result = rag_pipeline.rag(source=query_input.source).invoke({"input": query_input.query})
        
        # Return answer
        return RAGResponse(
            answer=result["answer"],
            context_used=True
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

# @app.post("/debug", response_model=DebugResponse)
# async def debug_retrieval(debug_input: DebugQuery, rag_pipeline: RAGPipelineSetup = Depends(get_rag_pipeline)):
#     try:
#         # Get relevant documents
#         docs = rag_pipeline.debug_retrieve(source=debug_input.source, query=debug_input.query)
        
#         # Convert documents to response format
#         documents = []
#         for doc in docs:
#             documents.append(Document(
#                 content=doc.page_content,
#                 metadata=doc.metadata
#             ))
        
#         # Return debug response
#         return DebugResponse(
#             query=debug_input.query,
#             documents=documents
#         )
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error debugging retrieval: {str(e)}")

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Run the application using Uvicorn when script is executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)