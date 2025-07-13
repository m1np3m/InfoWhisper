# 🤖 Chatbot Hỏi Đáp RAG Hội Thoại (Conversational RAG)

Hệ thống chatbot này được xây dựng theo kiến trúc **Retrieval-Augmented Generation (RAG)**, hỗ trợ khả năng hội thoại tự nhiên với người dùng, sử dụng kết hợp:

- ✅ **Gemini LLM** (Google Generative AI)
- 🔍 **Qdrant** cho truy vấn vector ngữ nghĩa
- 🧠 **Semantic Cache** sử dụng Redis
- 📚 **Lịch sử hội thoại** và **Reranking** theo bối cảnh
- 🛡️ **Phát hiện Prompt Injection** qua Lakera Guard
- 🔎 **Theo dõi pipeline** với Langfuse (tracing)

---

## 🧱 Thành phần chính

### 1. `GeminiLLM`

Lớp trừu tượng cho Gemini LLM, hỗ trợ cấu hình `temperature`, `top_k`, `top_p` và tích hợp Langfuse để tracking các truy vấn.

```python
llm = GeminiLLM(model_name="gemini-pro", api_key="...", llm_config=config)
response = llm.generate(query="Explain RAG", system_prompt="You are a helpful assistant.")
```

### 2. RAGSingleVectorSearch

Pipeline chính cho RAG:
- Mã hóa truy vấn thành vector
- Truy vấn Qdrant
- Xây dựng prompt với ngữ cảnh phù hợp
- Sinh câu trả lời với Gemini LLM

```python
rag = RAGSingleVectorSearch(llm, embedding_model, qdrant_client, config)
response = rag.generate_response(query, context, system_prompt)
```

### 3. HistoryGuidedReranker

Cải thiện độ chính xác của tìm kiếm bằng cách sắp xếp lại kết quả dựa trên:
- Độ tương đồng với truy vấn
- Mức liên quan đến lịch sử hội thoại (theo thời gian)

```python
reranker = HistoryGuidedReranker(embedding_model)
reranked_contexts = reranker.rerank(query, contexts, history_texts)
```

### 4. SemanticPromptCache

Redis cache dùng để lưu các prompt tương tự theo nghĩa, giúp:
- Tránh gọi lại LLM không cần thiết
- Truy xuất nhanh với độ chính xác cao

```python
cached = semantic_cache.get_cached_response(prompt)
semantic_cache.cache_response(prompt, response)
```

### 5. ConversationalRAGChatbot

Hệ thống chatbot đầy đủ, tích hợp:
- Lưu lịch sử hội thoại (Redis)
- Kiểm tra cache semantic
- Tìm kiếm RAG và reranking
- Bảo mật prompt injection
- Truy vết pipeline với Langfuse

```python
bot = ConversationalRAGChatbot(
    rag_pipeline=rag,
    config=config,
    reranker=reranker,
    semantic_cache=semantic_cache,
    langfuse_client=...
)

response = bot.chat("Giải thích attention trong transformer?")
```

## 📦 Tính Năng Nổi Bật
| Tính năng                   | Mô tả                             |
| --------------------------- | --------------------------------- |
| Mô hình ngôn ngữ (LLM)      | Gemini của Google                 |
| Tìm kiếm vector             | Qdrant (single vector)            |
| Semantic Caching            | Redis + cosine similarity         |
| Ghi nhớ hội thoại           | Redis TTL, có nén gzip            |
| Kiểm tra prompt injection   | Lakera Guard API                  |
| Reranking ngữ cảnh          | Dựa vào lịch sử + vector truy vấn |
| Tracking & quan sát         | Langfuse tracing                  |
| Giới hạn chiều dài ngữ cảnh | Tự động cắt bớt theo token        |
| Gzip compression (tùy chọn) | Nén dữ liệu để tối ưu Redis       |

## 🧪 Ví dụ sử dụng
```python
query = "Cơ chế attention hoạt động như thế nào?"
response = bot.chat(query)
print(response)
```

## 💡 Mở Rộng Dễ Dàng
- Thay Gemini bằng OpenAI, Claude, hoặc mô hình local
- Thay Qdrant bằng FAISS hoặc Pinecone
- Tích hợp thêm multi-vector search hoặc hybrid search
