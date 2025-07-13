from pymongo import MongoClient
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

def get_mongodb_data(mongo_uri):
    client = MongoClient(mongo_uri)
    return list(client["Content"]["Content"].find())

def generate_embeddings_from_field(data, field_name, collection_name, qdrant_url, qdrant_api_key):
    documents = [
        Document(page_content=item[field_name], metadata={"date": item["publish_date"]})
        for item in data
    ]
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    texts = text_splitter.split_documents(documents)

    print(f"✅ [{collection_name}] Original documents: {len(documents)} | Chunks: {len(texts)}")

    embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")
    qdrant = QdrantVectorStore.from_documents(
        texts,
        embeddings,
        url=qdrant_url,
        prefer_grpc=True,
        api_key=qdrant_api_key,
        collection_name=collection_name,
    )

    count_result = qdrant.client.count(collection_name=collection_name, exact=True)
    print(f"✅ Qdrant stored [{collection_name}]: {count_result.count}")
    return qdrant, embeddings
