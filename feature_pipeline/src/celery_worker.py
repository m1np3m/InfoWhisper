import os
import json
import logging
from celery import Celery
from dotenv import load_dotenv
import pymongo
from pymongo.errors import PyMongoError
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer
from datetime import datetime
from qdrant_client.http.models import Filter, FieldCondition, MatchValue, FilterSelector
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore

# LangChain imports for text chunking
from langchain_text_splitters import RecursiveCharacterTextSplitter
#from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
import uuid

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("celery_worker.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CeleryWorker")

# Load biến môi trường
load_dotenv()

# Thiết lập Celery
app = Celery('celery_worker')
app.config_from_object('celery_config')

# Thiết lập MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://vinhthuanly210:Vinhthuanly123@cluster0.mznyroo.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "News")

# Thiết lập Qdrant
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "news_embeddings")
VECTOR_SIZE = 1024
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "your_qdrant_api_key")
QDRANT_ENDPOINT = os.getenv("QDRANT_ENDPOINT")

# Cấu hình chunking
CHUNK_SIZE = 500  # Kích thước mỗi chunk (ký tự)
CHUNK_OVERLAP = 50 

# Khởi tạo MongoDB client
try:
    mongo_client = pymongo.MongoClient(MONGO_URI)
    db = mongo_client[MONGO_DB_NAME]
    logger.info("Kết nối MongoDB thành công.")
except PyMongoError as e:
    logger.error(f"Lỗi kết nối MongoDB: {e}")
    raise

# Khởi tạo Qdrant client
try:
    qdrant_client = QdrantClient(
        url=QDRANT_ENDPOINT,
        api_key=QDRANT_API_KEY,
    )
    
    collections = qdrant_client.get_collections()
    collection_names = [collection.name for collection in collections.collections]
    
    if QDRANT_COLLECTION not in collection_names:
        qdrant_client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=models.VectorParams(
                size=VECTOR_SIZE, 
                distance=models.Distance.COSINE
            )
        )
        logger.info(f"Đã tạo collection {QDRANT_COLLECTION} trong Qdrant.")
    else:
        # Kiểm tra kích thước vector của collection hiện tại
        collection_info = qdrant_client.get_collection(collection_name=QDRANT_COLLECTION)
        current_vector_size = collection_info.config.params.vectors.size
        
        if current_vector_size != VECTOR_SIZE:
            logger.warning(f"Kích thước vector hiện tại ({current_vector_size}) khác với kích thước yêu cầu ({VECTOR_SIZE})!")
            logger.warning(f"Bạn có thể cần tạo một collection mới với kích thước vector phù hợp.")
        
        logger.info(f"Collection {QDRANT_COLLECTION} đã tồn tại trong Qdrant.")

except Exception as e:
    logger.error(f"Lỗi kết nối Qdrant: {e}")
    raise

try:
    qdrant_client.create_payload_index(
        collection_name=QDRANT_COLLECTION,
        field_name="metadata.document_id",
        field_schema=models.PayloadSchemaType.KEYWORD
    )
    qdrant_client.create_payload_index(
        collection_name=QDRANT_COLLECTION,
        field_name="metadata.url",
        field_schema=models.PayloadSchemaType.KEYWORD
    )
    qdrant_client.create_payload_index(
        collection_name=QDRANT_COLLECTION,
        field_name="metadata.chunk_id",
        field_schema=models.PayloadSchemaType.KEYWORD
    )

    logger.info("Đã tạo index cho document_id trong Qdrant.")
except Exception as e:
    if "already exists" in str(e):
        logger.info("Index cho document_id đã tồn tại.")
    else:
        logger.warning(f"Lỗi khi tạo index cho document_id: {e}")


# Biến toàn cục lưu model embedding, khởi tạo khi cần (lazy load)
model = None
text_splitter = None

def preprocess_text(text):
    """
    Tiền xử lý text: lowercase, loại bỏ khoảng trắng thừa
    """
    if not text:
        return ""
    return text.lower().strip()

def chunk_document(doc):
    """
    Chia nhỏ nội dung văn bản thành các phần sử dụng LangChain
    """
    global text_splitter
    
    # Lazy load text splitter
    if text_splitter is None:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    content = doc.get('content', '')
    if content == "Không tìm thấy nội dung chi tiết":
        title = doc.get('title', '')
        description = doc.get('description', '')
        content = f"{title}\n\n{description}"
    
    # Tạo LangChain Document với metadata
    metadata = {
        "document_id": str(doc.get('_id')),
        "title": doc.get('title', ''),
        "author": doc.get('author', 'Không có thông tin tác giả'),
        "category": doc.get('category', ''),
        "url": doc.get('url', ''),
        "publish_date": doc.get('publish_date', ''),
        "description": doc.get('description', ''),
        "tags": doc.get('tags', []),
        "main_image": doc.get('main_image', ''),
        "bullet_summary": doc.get('bullet_summary', '')
    }
    
    langchain_doc = Document(page_content=content, metadata=metadata)
    
    # Chia nhỏ document thành chunks
    chunks = text_splitter.split_documents([langchain_doc])
    
    return chunks

@app.task(name="process_mongodb_change")
def process_mongodb_change(message):
    """
    Xử lý thay đổi từ MongoDB, tạo embedding và lưu vào Qdrant sử dụng langchain_qdrant
    """
    try:
        operation = message.get('operation')
        collection_name = message.get('collection')
        document_id = message.get('documentId')
        
        logger.info(f"Đang xử lý {operation} cho document {document_id} từ collection {collection_name}")
        
        if operation in ['insert', 'update']:
            # Lấy document
            if operation == 'insert' and 'document' in message:
                doc = message['document']
                doc['_id'] = document_id  # Thêm _id vào document
            else:
                collection = db[collection_name]
                doc = collection.find_one({'_id': document_id})
                if not doc:
                    logger.warning(f"Không tìm thấy document {document_id} trong collection {collection_name}")
                    return
            
            # Xóa các chunks hiện tại của document (nếu có)
            try:
                qdrant_client.delete(
                    collection_name=QDRANT_COLLECTION,
                    points_selector=models.FilterSelector(
                        filter=models.Filter(
                            must=[
                                models.FieldCondition(
                                    key="metadata.document_id",
                                    match=models.MatchValue(value=str(document_id))
                                )
                            ]
                        )
                    )
                )
                logger.info(f"Đã xóa các chunks cũ của document {document_id}")
            except Exception as e:
                logger.warning(f"Lỗi khi xóa chunks cũ: {e}")
            
            # Chia document thành chunks
            chunks = chunk_document(doc)
            if not chunks:
                logger.warning(f"Không có content để embedding cho document {document_id}")
                return
                
            logger.info(f"Đã chia document {document_id} thành {len(chunks)} chunks")
             
            # Khởi tạo vector store với HuggingFaceEmbeddings
            embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")
            vector_store = QdrantVectorStore(
                client=qdrant_client,
                collection_name=QDRANT_COLLECTION,
                embedding=embeddings
            )
            
            # Thêm metadata cho mỗi chunk
            for i, chunk in enumerate(chunks):
                chunk.metadata.update({
                    "document_id": str(document_id),
                    "chunk_id": f"{document_id}_{i}",
                    "chunk_index": i,
                    "chunk_total": len(chunks),
                    "chunk_content": chunk.page_content,  # Lưu nội dung chunk
                    "processed_at": datetime.now().isoformat()
                })
            
            # Tạo unique IDs cho từng chunk
            ids = [str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{document_id}_{i}")) for i in range(len(chunks))]
            
            # Lưu vào Qdrant qua LangChain interface
            vector_store.add_documents(documents=chunks, ids=ids)
            
            logger.info(f"Hoàn thành lưu embedding cho document {document_id}")
        
        elif operation == 'delete':
            # Xóa tất cả chunks của document khỏi Qdrant
            try:
                qdrant_client.delete(
                    collection_name=QDRANT_COLLECTION,
                    points_selector=models.FilterSelector(
                        filter=models.Filter(
                            must=[
                                models.FieldCondition(
                                    key="metadata.document_id",
                                    match=models.MatchValue(value=str(document_id))
                                )
                            ]
                        )
                    )
                )
                logger.info(f"Đã xóa các chunks của document {document_id} khỏi Qdrant.")
            except Exception as e:
                logger.error(f"Lỗi khi xóa document {document_id} từ Qdrant: {e}")
        
        else:
            logger.warning(f"Không hỗ trợ operation: {operation}")
        
    except Exception as e:
        logger.error(f"Lỗi khi xử lý document {document_id}: {e}")
       