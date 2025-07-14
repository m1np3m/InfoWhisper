import streamlit as st
from dotenv import load_dotenv
import os
import logging
import time
import pandas as pd
import plotly.express as px
from modules.RAG import RAGPipelineSetup
from datetime import datetime
#from phoenix_set import setup_tracer
from modules.redis_manager import RedisManager
from modules.query_manager import QueryGenerator





# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="AI NEWS",
    page_icon="logo.jpg",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better appearance with improved color scheme
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Color palette */
    :root {
        --primary-blue: #2563eb;
        --primary-blue-dark: #1d4ed8;
        --primary-blue-light: #3b82f6;
        --secondary-purple: #7c3aed;
        --accent-teal: #0d9488;
        --accent-emerald: #059669;
        --neutral-50: #f8fafc;
        --neutral-100: #f1f5f9;
        --neutral-200: #e2e8f0;
        --neutral-300: #cbd5e1;
        --neutral-500: #64748b;
        --neutral-600: #475569;
        --neutral-700: #334155;
        --neutral-800: #1e293b;
        --neutral-900: #0f172a;
        --white: #ffffff;
        --success: #10b981;
        --warning: #f59e0b;
        --error: #ef4444;
    }
    
    /* Base styling */
    .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, segoe ui, Roboto, sans-serif;
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
    }
    
    /* Main container styles */
    .main-container {
        padding: 2rem;
        border-radius: 16px;
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        margin-bottom: 1rem;
        border: 1px solid var(--neutral-200);
    }
    
    /* Chat container */
    .chat-container {
        border-radius: 16px;
        padding: 1.5rem;
        background: var(--white);
        border: 1px solid var(--neutral-200);
        height: 75vh;
        overflow-y: auto;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
    }
    
    /* Message bubbles */
    .user-message {
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--primary-blue-light) 100%);
        color: var(--white);
        border-radius: 18px 18px 4px 18px;
        padding: 12px 18px;
        margin: 8px 0;
        max-width: 80%;
        align-self: flex-end;
        margin-left: auto;
        box-shadow: 0 2px 8px rgba(37, 99, 235, 0.2);
        font-weight: 500;
    }
    
    .assistant-message {
        background: linear-gradient(135deg, var(--neutral-50) 0%, var(--neutral-100) 100%);
        color: var(--neutral-800);
        border-radius: 18px 18px 18px 4px;
        padding: 12px 18px;
        margin: 8px 0;
        max-width: 80%;
        border: 1px solid var(--neutral-200);
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
    
    /* Header styling */
    h1, h2, h3, h4, h5, h6 {
        color: var(--neutral-800);
        font-family: 'Inter', sans-serif;
        font-weight: 600;
    }
    
    h1 {
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--secondary-purple) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    /* Logo styling */
    .logo-container {
        text-align: center;
        margin-bottom: 1.5rem;
        padding: 1rem;
        background: linear-gradient(135deg, var(--white) 0%, var(--neutral-50) 100%);
        border-radius: 16px;
        border: 1px solid var(--neutral-200);
    }
    
    .logo-image {
        border-radius: 50%;
        box-shadow: 0 8px 32px rgba(37, 99, 235, 0.2);
        border: 3px solid var(--white);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        padding: 2rem 1rem;
        background: linear-gradient(180deg, var(--white) 0%, var(--neutral-50) 100%);
    }
    
    /* Sidebar header */
    .sidebar-header {
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--secondary-purple) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
        margin-bottom: 1.5rem;
        font-weight: 700;
    }
    
    /* Input field styling */
    .stTextInput>div>div>input {
        border-radius: 24px;
        border: 2px solid var(--neutral-200);
        padding: 12px 20px;
        font-size: 16px;
        transition: all 0.3s ease;
        background: var(--white);
    }
    
    .stTextInput>div>div>input:focus {
        border-color: var(--primary-blue);
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        outline: none;
    }
    
    /* Button styling */
    .stButton>button {
        border-radius: 24px;
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--primary-blue-light) 100%);
        color: var(--white);
        border: none;
        padding: 12px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
    }
    
    .stButton>button:hover {
        background: linear-gradient(135deg, var(--primary-blue-dark) 0%, var(--primary-blue) 100%);
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.4);
    }
    
    /* Select box styling */
    .stSelectbox>div>div {
        border-radius: 12px;
        border: 2px solid var(--neutral-200);
        background: var(--white);
    }
    
    /* Metrics styling */
    .stMetric {
        background: var(--white);
        padding: 1rem;
        border-radius: 12px;
        border: 1px solid var(--neutral-200);
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
    
    .stMetric [data-testid="metric-container"] {
        background: linear-gradient(135deg, var(--accent-teal) 0%, var(--accent-emerald) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    /* Hide default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Status icons */
    .status-icon {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 8px;
    }
    
    .status-online {
        background: linear-gradient(135deg, var(--success) 0%, var(--accent-emerald) 100%);
        box-shadow: 0 0 8px rgba(16, 185, 129, 0.4);
    }
    
    /* Response metrics */
    .metrics-container {
        display: flex;
        justify-content: space-between;
        background: linear-gradient(135deg, var(--neutral-50) 0%, var(--white) 100%);
        padding: 1.5rem;
        border-radius: 16px;
        margin-top: 1rem;
        border: 1px solid var(--neutral-200);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    .metric {
        text-align: center;
        padding: 0 1rem;
    }
    
    .metric-value {
        font-size: 1.75rem;
        font-weight: 700;
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--secondary-purple) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .metric-label {
        font-size: 0.875rem;
        color: var(--neutral-500);
        font-weight: 500;
    }
    
    /* Source sections */
    .source-section {
        background: linear-gradient(135deg, var(--white) 0%, var(--neutral-50) 100%);
        border: 1px solid var(--neutral-200);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        transition: all 0.3s ease;
    }
    
    .source-section:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
        border-color: var(--primary-blue);
    }
    
    .source-header {
        display: flex;
        align-items: center;
        margin-bottom: 1rem;
        font-weight: 600;
        color: var(--primary-blue);
    }
    
    .source-title {
        font-size: 18px;
        margin-bottom: 8px;
        color: var(--neutral-800);
        font-weight: 600;
        line-height: 1.5;
    }
    
    .source-meta {
        font-size: 14px;
        color: var(--neutral-500);
        margin-bottom: 12px;
        font-weight: 500;
    }
    
    .source-image {
        max-width: 220px;
        height: auto;
        border-radius: 12px;
        margin: 12px 0;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease;
    }
    
    .source-image:hover {
        transform: scale(1.05);
    }
    
    .source-url {
        font-size: 14px;
        color: var(--accent-teal);
        text-decoration: none;
        font-weight: 500;
        display: inline-flex;
        align-items: center;
        padding: 8px 16px;
        background: var(--neutral-50);
        border-radius: 20px;
        border: 1px solid var(--neutral-200);
        transition: all 0.3s ease;
    }
    
    .source-url:hover {
        background: var(--accent-teal);
        color: var(--white);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(13, 148, 136, 0.3);
    }
    
    /* Response answer section */
    .response-answer {
        background: linear-gradient(135deg, var(--white) 0%, var(--neutral-50) 100%);
        border: 1px solid var(--neutral-200);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        color: var(--neutral-800);
        line-height: 1.7;
    }
    
    .sources-container {
        background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%);
        border: 2px solid var(--accent-emerald);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 12px rgba(5, 150, 105, 0.1);
    }
    
    .sources-title {
        color: var(--accent-emerald);
        font-weight: 700;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        font-size: 1.125rem;
    }
    
    .sources-title::before {
        content: "📚";
        margin-right: 10px;
        font-size: 1.25rem;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, var(--white) 0%, var(--neutral-50) 100%);
        border-radius: 12px;
        border: 1px solid var(--neutral-200);
        padding: 12px 16px;
        margin-bottom: 8px;
        font-weight: 600;
        color: var(--neutral-800);
    }
    
    .streamlit-expanderContent {
        background: var(--white);
        border-radius: 12px;
        border: 1px solid var(--neutral-200);
        padding: 1rem;
        margin-top: 8px;
    }
    
    /* Chat input styling */
    .stChatInput>div>div>div>div>input {
        border-radius: 24px;
        border: 2px solid var(--neutral-200);
        padding: 12px 20px;
        font-size: 16px;
        background: var(--white);
        transition: all 0.3s ease;
    }
    
    .stChatInput>div>div>div>div>input:focus {
        border-color: var(--primary-blue);
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
    }
    
    /* Spinner styling */
    .stSpinner>div {
        border-top-color: var(--primary-blue);
    }
    
    /* Scrollbar styling */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--neutral-100);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, var(--primary-blue) 0%, var(--secondary-purple) 100%);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(180deg, var(--primary-blue-dark) 0%, var(--secondary-purple) 100%);
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# Initialize session state variables
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "response_times" not in st.session_state:
    st.session_state.response_times = []
# if 'tracer_initialized' not in st.session_state:
#     setup_tracer()
#     st.session_state['tracer_initialized'] = True


# Function to initialize RAG pipeline
@st.cache_resource

def initialize_redis():
    return RedisManager(redis_url=os.getenv("REDIS_URL", "redis://localhost:6380"))

# Initialize session ID
if "session_id" not in st.session_state:
    redis_manager = initialize_redis()
    st.session_state.session_id = redis_manager.generate_session_id()

# Load chat history from Redis on startup
if "redis_loaded" not in st.session_state:
    redis_manager = initialize_redis()
    chat_history = redis_manager.get_chat_history(st.session_state.session_id)
    
    # Convert Redis format to Streamlit format
    st.session_state.messages = []
    for msg in chat_history:
        st.session_state.messages.append({
            "role": msg["role"],
            "content": msg["content"],
            "sources": msg.get("sources", [])
        })
    
    st.session_state.redis_loaded = True
@st.cache_resource
def initialize_rag_pipeline():
    # Initialize RAG pipeline object
    rag_pipeline_setup = RAGPipelineSetup(
        qdrant_url=os.getenv("QDRANT_URL"),
        qdrant_api_key=os.getenv("QDRANT_API_KEY"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        hf_api_key=os.getenv("HUGGINGFACE_API_KEY"),
        hf_model_name=os.getenv("EMBEDDINGS_MODEL_NAME", "BAAI/bge-m3")
    )
    return rag_pipeline_setup

# Function to extract and format sources from response
def format_sources(response):
    """Extract and format source documents from response"""
    if not hasattr(response, 'get') or 'context' not in response:
        return []
    
    sources = []
    seen_titles = set()  # To avoid duplicate sources
    
    for doc in response.get('context', []):
        if hasattr(doc, 'metadata'):
            metadata = doc.metadata
            title = metadata.get('title', 'Không có tiêu đề')
            
            # Skip duplicates based on title
            if title in seen_titles:
                continue
            seen_titles.add(title)
            
            source_info = {
                'title': title,
                'author': metadata.get('author', 'Không có thông tin tác giả'),
                'category': metadata.get('category', ''),
                'url': metadata.get('url', ''),
                'publish_date': metadata.get('publish_date', ''),
                'description': metadata.get('description', ''),
                'main_image': metadata.get('main_image', ''),
                'document_id': metadata.get('document_id', '')
            }
            sources.append(source_info)
    
    return sources

def display_sources(sources):
    """Display sources in a formatted way"""
    if not sources:
        return
    
    st.markdown('<div class="sources-container">', unsafe_allow_html=True)
    st.markdown('<div class="sources-title">Nguồn tham khảo</div>', unsafe_allow_html=True)
    
    for i, source in enumerate(sources, 1):
        with st.expander(f"📰 {source['title'][:80]}{'...' if len(source['title']) > 80 else ''}"):
            # Create columns for image and content
            col1, col2 = st.columns([1, 3])
            
            with col1:
                # Display image if available
                if source['main_image'] and source['main_image'].strip():
                    try:
                        st.image(source['main_image'], 
                               caption="Hình ảnh bài viết", 
                              use_container_width=True)
                    except:
                        st.write("🖼️ *Không thể tải hình ảnh*")
                else:
                    st.write("🖼️ *Không có hình ảnh*")
            
            with col2:
                # Display article information
                st.markdown(f"**Tiêu đề:** {source['title']}")
                st.markdown(f"**Tác giả:** {source['author']}")
                
                if source['category']:
                    st.markdown(f"**Danh mục:** {source['category'].title()}")
                
                if source['publish_date']:
                    try:
                        # Format date
                        date_obj = datetime.strptime(source['publish_date'], '%Y-%m-%d %H:%M:%S')
                        formatted_date = date_obj.strftime('%d/%m/%Y %H:%M')
                        st.markdown(f"**Ngày xuất bản:** {formatted_date}")
                    except:
                        st.markdown(f"**Ngày xuất bản:** {source['publish_date']}")
                
                if source['description']:
                    st.markdown(f"**Mô tả:** {source['description']}")
                
                if source['url']:
                    st.markdown(f"**Liên kết:** [Đọc bài viết đầy đủ]({source['url']})")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Initialize RAG pipeline
rag_pipeline_setup = initialize_rag_pipeline()

# Define the source collection name
source_collection = "deeplearning_ai_news_embeddings"

def clear_chat_history():
    redis_manager = initialize_redis()
    redis_manager.clear_session_history(st.session_state.session_id)
    st.session_state.messages = []
    st.session_state.chat_history = []
    st.session_state.session_id = redis_manager.generate_session_id()


# Sidebar content
with st.sidebar:
    # Logo and app title
    st.markdown('<div class="logo-container">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-header">🤖 AI NEWS ASSISTANT</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # System status
    # st.markdown("### 🔄 Trạng thái hệ thống")
    # status_col1, status_col2 = st.columns(2)
    # with status_col1:
    #     st.markdown('<span class="status-icon status-online"></span>**Đang hoạt động**', unsafe_allow_html=True)
    # with status_col2:
    #     st.markdown(f"🗂️ **{source_collection}**")
    
    # Usage statistics
    if len(st.session_state.response_times) > 0:
        avg_response_time = sum(st.session_state.response_times) / len(st.session_state.response_times)
        st.markdown("### 📊 Thống kê sử dụng")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Số câu hỏi", len(st.session_state.response_times), delta=None)
        with col2:
            st.metric("Thời gian TB", f"{avg_response_time:.2f}s", delta=None)
            
        # Create response time chart if we have enough data
        if len(st.session_state.response_times) >= 2:
            st.markdown("### 📈 Biểu đồ thời gian phản hồi")
            df = pd.DataFrame({
                "Câu hỏi": range(1, len(st.session_state.response_times) + 1),
                "Thời gian (s)": st.session_state.response_times
            })
            fig = px.line(df, x="Câu hỏi", y="Thời gian (s)", 
                         title="", 
                         color_discrete_sequence=["#2563eb"])
            fig.update_layout(
                height=250,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Inter", size=12),
                margin=dict(l=40, r=40, t=20, b=40)
            )
            fig.update_traces(line=dict(width=3))
            st.plotly_chart(fig, use_container_width=True)
    
    # Information section
    st.markdown("### 💡 Hướng dẫn sử dụng")
    st.markdown("""
    - 🔍 Đặt câu hỏi về tin tức
    - 📚 Xem nguồn tham khảo
    - 📊 Theo dõi thống kê
    - 🗑️ Xóa lịch sử khi cần
    """)
    
    # Clear chat button
    if st.button("🗑️ Xóa lịch sử trò chuyện", use_container_width=True):
        clear_chat_history()
        st.rerun()

# Main app header
st.markdown("# 🤖 AI News Assistant")

# Initialize RAG pipeline with fixed source
rag_pipeline = rag_pipeline_setup.rag(source=source_collection)

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"], 
                        avatar='https://raw.githubusercontent.com/ThuanLy-0092/Sindia_House_Price_Regression/refs/heads/main/user.png' if message["role"] == "user" else 'logo.jpg'):
        if message["role"] == "assistant" and "sources" in message:
            # Display sources first
            display_sources(message["sources"])
            # Then display the answer
            st.markdown('<div class="response-answer">', unsafe_allow_html=True)
            st.markdown(message["content"])
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown(message["content"])

# # Function to generate response with timing
# def generate_response(prompt):
#     try:
#         start_time = time.time()
        
#         # Prepare input
#         inputs = {"input": prompt}
        
#         # Execute pipeline
#         response = rag_pipeline.invoke(inputs)
        
#         # Calculate response time
#         elapsed_time = time.time() - start_time
#         st.session_state.response_times.append(elapsed_time)
        
#         # Extract sources from response
#         sources = format_sources(response)
        
#         return response["answer"], sources
            
#     except Exception as e:
#         logger.error(f"Error generating response: {str(e)}")
#         return f"Xảy ra lỗi khi xử lý câu hỏi: {str(e)}", []
    
# def generate_response_with_redis(prompt):
#     try:
#         start_time = time.time()
        
#         # Use RAG with history
#         response, optimized_query = rag_pipeline_setup.rag_with_history(
#             source=source_collection,
#             user_question=prompt,
#             session_id=st.session_state.session_id
#         )
        
#         # Calculate response time
#         elapsed_time = time.time() - start_time
#         st.session_state.response_times.append(elapsed_time)
        
#         # Extract sources from response
#         sources = format_sources(response)
        
#         # Display optimization info in sidebar
#         if optimized_query != prompt:
#             st.sidebar.info(f"🔍 Câu hỏi được tối ưu: {optimized_query}")
        
#         return response["answer"], sources
            
#     except Exception as e:
#         logger.error(f"Error generating response: {str(e)}")
#         return f"Xảy ra lỗi khi xử lý câu hỏi: {str(e)}", []
    
def generate_response_with_redis_and_cache(prompt, use_cache=True, cache_ttl=600):
    """
    Generate response with Redis history and caching
    
    Args:
        prompt: User question
        use_cache: Whether to use cache
        cache_ttl: Cache time to live in seconds
    """
    try:
        start_time = time.time()
        
        # Use RAG with history and cache
        response, optimized_query, cache_hit = rag_pipeline_setup.rag_with_history_and_cache(
            source=source_collection,
            user_question=prompt,
            session_id=st.session_state.session_id,
            use_cache=use_cache,
            cache_ttl=cache_ttl
        )
        
        # Calculate response time
        elapsed_time = time.time() - start_time
        st.session_state.response_times.append(elapsed_time)
        
        # Extract sources from response
        sources = response.get("sources", format_sources(response))

        
        # Display optimization and cache info in sidebar
        if cache_hit:
            st.sidebar.success(f"✅ Cache hit! Thời gian phản hồi: {elapsed_time:.2f}s")
        else:
            st.sidebar.info(f"⚡ Generated response in {elapsed_time:.2f}s")
            
        if optimized_query != prompt:
            st.sidebar.info(f"🔍 Câu hỏi được tối ưu: {optimized_query}")
        
        return response["answer"], sources, cache_hit
            
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        return f"Xảy ra lỗi khi xử lý câu hỏi: {str(e)}", [], False

# Chat input
prompt = st.chat_input("💬 Nhập câu hỏi của bạn về tin tức...")
if prompt:
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user", avatar='https://raw.githubusercontent.com/ThuanLy-0092/Sindia_House_Price_Regression/refs/heads/main/user.png'):
        st.markdown(prompt)
    
    # Generate and display assistant response
    with st.chat_message("assistant", avatar='logo.jpg'):
        with st.spinner("🔍 Đang xử lý câu hỏi của bạn..."):
            response, sources,_ = generate_response_with_redis_and_cache(prompt)
            
            # Display sources first if available
            if sources:
                display_sources(sources)
            
            # Display the answer
            st.markdown('<div class="response-answer">', unsafe_allow_html=True)
            st.markdown(response)
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Add assistant response to chat history with sources
    st.session_state.messages.append({
        "role": "assistant", 
        "content": response,
        "sources": sources
    })
    st.session_state.chat_history.append({
        "role": "assistant", 
        "content": response,
        "sources": sources
    })
    
    # Force a rerun to update sidebar statistics
    st.rerun()