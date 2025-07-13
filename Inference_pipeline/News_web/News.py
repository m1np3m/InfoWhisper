import streamlit as st
import pymongo
from datetime import datetime
import pandas as pd
from urllib.parse import urlparse
from dotenv import load_dotenv
import os
from dateutil import parser
from datetime import datetime
from streamlit_markmap import markmap

load_dotenv()

# Cấu hình trang
st.set_page_config(
    page_title="Tech News Hub",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS tùy chỉnh (đã cải tiến phần tabs)
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem 0;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
        border-radius: 10px;
    }
    
    .news-card {
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        border: 1px solid #e1e8ed;
        height: 100%;
        position: relative;
        overflow: hidden;
    }
    
    .news-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
    }
    
    .news-image {
        width: 100%;
        height: 180px;
        object-fit: cover;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    
    .news-title {
        font-size: 1.1rem;
        font-weight: bold;
        color: #1a1a1a;
        margin-bottom: 0.8rem;
        line-height: 1.4;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    
    .news-meta {
        color: #666;
        font-size: 0.85rem;
        margin-bottom: 1rem;
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        align-items: center;
    }
    
    .news-description {
        color: #444;
        line-height: 1.5;
        margin-bottom: 1rem;
        font-size: 0.9rem;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    
    .category-badge {
        background: linear-gradient(45deg, #667eea, #764ba2);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .collection-badge {
        background: linear-gradient(45deg, #28a745, #20c997);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .source-badge {
        background: #f8f9fa;
        color: #495057;
        padding: 0.2rem 0.6rem;
        border-radius: 15px;
        font-size: 0.7rem;
        border: 1px solid #dee2e6;
    }
    
    .sidebar-filter {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    
    .filter-title {
        font-weight: bold;
        color: #495057;
        margin-bottom: 0.5rem;
    }
    
    .stats-container {
        display: flex;
        justify-content: space-around;
        margin: 1.5rem 0;
        padding: 1rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        color: white;
    }
    
    .stat-item {
        text-align: center;
    }
    
    .stat-number {
        font-size: 1.8rem;
        font-weight: bold;
        color: white;
    }
    
    .stat-label {
        color: rgba(255, 255, 255, 0.9);
        font-size: 0.8rem;
    }
    
    .card-actions {
        background: #f8f9fa;
        margin: 1rem -1.5rem -1.5rem -1.5rem;
        padding: 1rem 1.5rem;
        border-top: 1px solid #e9ecef;
        border-radius: 0 0 15px 15px;
    }
    
    .action-button {
        display: inline-block;
        padding: 0.5rem 1rem;
        margin: 0.2rem 0.5rem 0.2rem 0;
        border: none;
        border-radius: 8px;
        font-size: 0.85rem;
        font-weight: 500;
        text-decoration: none;
        cursor: pointer;
        transition: all 0.3s ease;
        text-align: center;
        min-width: 120px;
    }
    
    .summary-button {
        background: linear-gradient(45deg, #667eea, #764ba2);
        color: white;
    }
    
    .summary-button:hover {
        background: linear-gradient(45deg, #764ba2, #667eea);
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    
    .link-button {
        background: #28a745;
        color: white;
    }
    
    .link-button:hover {
        background: #218838;
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    
    .disabled-button {
        background: #6c757d;
        color: white;
        cursor: not-allowed;
        opacity: 0.6;
    }
    
    .summary-content {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
        border: 1px solid #e9ecef;
        max-width: 600px;
    }
    
    .summary-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem 1.5rem;
        margin: -1.5rem -1.5rem 1.5rem -1.5rem;
        border-radius: 12px 12px 0 0;
        font-weight: 600;
        font-size: 1.1rem;
    }
    
    .meta-info {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        border-left: 4px solid #667eea;
    }
    
    .summary-text {
        background: #f8fff4;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #28a745;
        font-style: italic;
        line-height: 1.6;
    }
    
    .original-link {
        background: linear-gradient(45deg, #28a745, #20c997);
        color: white;
        padding: 0.8rem 1.5rem;
        border-radius: 25px;
        text-decoration: none;
        font-weight: 600;
        display: inline-block;
        margin-top: 1rem;
        transition: all 0.3s ease;
    }
    
    .original-link:hover {
        background: linear-gradient(45deg, #20c997, #28a745);
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(40, 167, 69, 0.3);
        color: white;
        text-decoration: none;
    }
    
    /* Tab styling - ĐƯỢC CẢI TIẾN ĐỂ DÀN ĐỀU */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        display: flex !important;
        justify-content: space-between !important;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)) !important;
        width: 100% !important;
        flex-wrap: wrap !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        flex: 1 1 auto !important;
        min-width: 0 !important;
        max-width: none !important;
        height: 60px !important;
        padding: 12px 8px !important;
        background-color: #f8f9fa !important;
        border-radius: 12px !important;
        border: 2px solid #e9ecef !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        color: #495057 !important;
        transition: all 0.3s ease !important;
        text-align: center !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        margin: 0 !important;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #e9ecef !important;
        border-color: #667eea !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15) !important;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border-color: #667eea !important;
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.3) !important;
        transform: translateY(-2px) !important;
    }
    
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 2rem;
    }
    
    /* Responsive tabs */
    @media (max-width: 1200px) {
        .stTabs [data-baseweb="tab"] {
            font-size: 12px !important;
            padding: 10px 6px !important;
            height: 55px !important;
        }
    }
    
    @media (max-width: 768px) {
        .stTabs [data-baseweb="tab-list"] {
            flex-wrap: wrap !important;
            gap: 8px !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            flex: 1 1 calc(50% - 4px) !important;
            font-size: 11px !important;
            padding: 8px 4px !important;
            height: 50px !important;
            margin-bottom: 4px !important;
        }
    }
    
    @media (max-width: 480px) {
        .stTabs [data-baseweb="tab"] {
            flex: 1 1 100% !important;
            font-size: 12px !important;
            padding: 10px 8px !important;
            height: 45px !important;
        }
    }
    
    .tab-content {
        padding: 1rem 0;
    }
    
    .insight-container {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border-radius: 12px;
        padding: 2rem;
        margin-bottom: 2rem;
        border: 1px solid #dee2e6;
    }
    
    .insight-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem 1.5rem;
        margin: -2rem -2rem 1.5rem -2rem;
        border-radius: 12px 12px 0 0;
        font-weight: 600;
        font-size: 1.2rem;
    }
    
    @media (max-width: 768px) {
        .news-card {
            margin-bottom: 1rem;
        }
        
        .news-title {
            font-size: 1rem;
        }
        
        .news-meta {
            font-size: 0.8rem;
        }
        
        .action-button {
            font-size: 0.8rem;
            padding: 0.4rem 0.8rem;
            min-width: 100px;
        }
    }
</style>
""", unsafe_allow_html=True)

# Hàm kết nối MongoDB
@st.cache_resource
def init_connection():
    try:
        mongo_uri = os.getenv("MONGO_URI_NEWS")
        client = pymongo.MongoClient(mongo_uri)
        return client
    except Exception as e:
        st.error(f"Không thể kết nối MongoDB: {e}")
        return None

# Hàm lấy danh sách collections
@st.cache_data(ttl=600)  # Cache 10 phút
def get_collections(_client, database_name="deeplearning_ai_news"):
    try:
        db = _client[database_name]
        collections = db.list_collection_names()
        return collections
    except Exception as e:
        st.error(f"Lỗi khi lấy danh sách collections: {e}")
        return []

# Hàm lấy dữ liệu từ một collection cụ thể
@st.cache_data(ttl=300)  # Cache 5 phút
def load_collection_data(_client, collection_name, database_name="deeplearning_ai_news"):
    try:
        db = _client[database_name]
        collection = db[collection_name]
        articles = list(collection.find().sort("publish_date", -1))
        
        for article in articles:
            article['collection'] = collection_name
        
        def safe_date(article):
            pub = article.get("publish_date")
            if isinstance(pub, datetime):
                return pub
            try:
                return parser.parse(pub)
            except:
                return datetime.min
        
        articles.sort(key=safe_date, reverse=True)
        
        return articles
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu từ {collection_name}: {e}")
        return []

# Hàm lấy insight cho collection
@st.cache_data(ttl=3600, show_spinner=False)
def get_insight(_client, collection_name, month_str):
    try:
        db = _client["deeplearning_ai_insight"]
        col = db[collection_name]
        doc = col.find_one({"_id": month_str})
        return doc if doc else None
    except Exception as e:
        return None


# Hàm format ngày
def format_date(date_obj):
    if isinstance(date_obj, datetime):
        return date_obj.strftime("%d/%m/%Y")
    return str(date_obj)

# Hàm hiển thị summary trong popover
def show_summary_popover(article, key):
    with st.popover("📋 Xem tóm tắt", use_container_width=True):
        st.markdown(f"""
        <div class="summary-content">
            <div class="summary-header">
                📰 {article.get('title', 'Không có tiêu đề')}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Thông tin meta với collection
        st.markdown(f"""
        <div class="meta-info">
            <div style="display: flex; flex-wrap: wrap; gap: 1rem; margin-bottom: 0.5rem;">
                <div><strong>📅 Ngày xuất bản:</strong> {format_date(article.get('publish_date', ''))}</div>
                <div><strong>🏷️ Danh mục:</strong> <span style="color: #667eea; font-weight: 600;">{article.get('category', 'Khác').title()}</span></div>
            </div>
            <div style="display: flex; flex-wrap: wrap; gap: 1rem; margin-bottom: 0.5rem;">
                <div><strong>🌐 Nguồn:</strong> <span style="color: #28a745; font-weight: 600;">{article.get('source', 'Không rõ')}</span></div>
                <div><strong>🗂️ Collection:</strong> <span style="color: #dc3545; font-weight: 600;">{article.get('collection', 'Không rõ')}</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Summary
        if article.get('summary'):
            st.markdown("**📝 Tóm tắt nội dung:**")
            st.markdown(f"""
            <div class="summary-text">
                {article.get('summary')}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("**📋 Mô tả:**")
            st.markdown(f"""
            <div class="summary-text">
                {article.get('description', 'Không có mô tả')}
            </div>
            """, unsafe_allow_html=True)
        
        # Link bài viết gốc
        if article.get('url'):
            st.markdown(f"""
            <div style="text-align: center; margin-top: 1.5rem;">
                <a href="{article.get('url')}" target="_blank" class="original-link">
                    🔗 Đọc bài viết đầy đủ
                </a>
            </div>
            """, unsafe_allow_html=True)

# Hàm tạo card tin tức
def create_news_card(article, idx):
    with st.container():
        # Hiển thị ảnh
        if article.get('main_image'):
            try:
                st.image(
                    article.get('main_image'), 
                    use_container_width=True,
                    caption=None
                )
            except:
                st.image("https://via.placeholder.com/400x180?text=No+Image", use_container_width=True)
        else:
            st.image("https://via.placeholder.com/400x180?text=No+Image", use_container_width=True)
        
        # Hiển thị badge category
        st.markdown(f"""
        <span class="category-badge">
            {article.get('category', 'Khác').upper()}
        </span>
        """, unsafe_allow_html=True)
        
        # Tiêu đề
        st.markdown(f"""
        <h3 class="news-title">
            {article.get('title', 'Không có tiêu đề')}
        </h3>
        """, unsafe_allow_html=True)
        
        # Thông tin meta
        st.markdown(f"📅 **{format_date(article.get('publish_date', ''))}**")

        # Mô tả
        description = article.get('description', 'Không có mô tả')
        if len(description) > 120:
            description = description[:120] + '...'
        
        st.markdown(f"""
        <p class="news-description" style="margin-bottom: 0;">
            {description}
        </p>
        """, unsafe_allow_html=True)
    
    # Card actions
    st.markdown('<div class="card-actions">', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        show_summary_popover(article, f"summary_{idx}")
    with col2:
        if article.get('url'):
            st.link_button("🔗 Bài gốc", article.get('url'), use_container_width=True)
        else:
            st.button("🔗 Không có link", disabled=True, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Hàm hiển thị insights cho tất cả collections
def display_insights_tab(client, collections):
    st.markdown("### 📊 Tổng hợp tin tức 1 tháng gần đây")
    
    def get_current_month_str():
        now = datetime.utcnow()
        return now.replace(day=1).strftime("%Y-%m")
    
    month_key = get_current_month_str()
    st.info(f"📅 Insights cho tháng: **{month_key}**")
    
    insights_found = 0
    
    for collection_name in collections:
        insight = get_insight(client, collection_name, month_key)
        
        insight_doc = get_insight(client, collection_name, month_key)

        if insight_doc:
            insights_found += 1
            st.markdown(f"""
            <div class="insight-container">
                <div class="insight-header">
                    🗂️ {collection_name}
                </div>
                <div style="line-height: 1.6; font-size: 1.4rem; margin-bottom: 1rem;">
                    {insight_doc.get("insight", "Không có nội dung")}
                </div>
            """, unsafe_allow_html=True)

        if "markmap" in insight_doc:
            with st.popover("🧠 Xem Mindmap", use_container_width=True):
                st.markdown("#### 🧭 Mindmap minh hoạ:")
                markmap(insight_doc["markmap"], height=1000)


            st.markdown("</div>", unsafe_allow_html=True)

        else:
            st.markdown(f"""
            <div class="insight-container">
                <div class="insight-header">
                    🗂️ {collection_name}
                </div>
                <div style="padding: 1rem; text-align: center; color: #666;">
                    ⚠️ Không có insight cho collection này trong tháng {month_key}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    if insights_found == 0:
        st.warning(f"⚠️ Không tìm thấy insights nào cho tháng {month_key}")
    else:
        st.success(f"✅ Tìm thấy {insights_found}/{len(collections)} insights")

def display_hotkeyword_insights(client, db_name="Insight_from_hotkeyword"):
    st.markdown("## 🧠 Tổng hợp Insight từ các từ khoá nổi bật")

    try:
        db = client[db_name]
        topics = db.list_collection_names()

        if not topics:
            st.warning("⚠️ Không có topic nào trong database Insight_from_hotkeyword.")
            return

        # Chỉ xử lý topic đầu tiên
        topic = topics[0]
        collection = db[topic]

        keyword_docs = list(collection.find({}).sort("keyword"))

        if not keyword_docs:
            st.info("Không có từ khoá nào.")
            return

        for doc in keyword_docs:
            keyword = doc.get("keyword", "❓ Unknown")

            st.markdown(f"""
                <div class="insight-container">
                    <div class="insight-header">
                        🔑 {keyword}
                    </div>
                    <div style="line-height: 1.6; font-size: 1rem; margin-bottom: 1rem;">
                        {doc.get("vi_insight", "_Không có nội dung._")}
                    </div>
            """, unsafe_allow_html=True)

            if "markmap" in doc:
                # Không bọc container, và giữ layout đơn giản
                with st.popover("🧠 Xem Mindmap", use_container_width=True):
                    st.markdown("#### 🧭 Mindmap minh hoạ:")
                    markmap(doc["markmap"], height=1000)


            st.markdown("</div>", unsafe_allow_html=True)


    except Exception as e:
        st.error(f"Lỗi khi hiển thị insights: {e}")


# Hàm hiển thị collection content với search
def display_collection_content(client, collection_name):
    # Load dữ liệu cho collection
    articles = load_collection_data(client, collection_name)
    
    if not articles:
        st.warning(f"⚠️ Không có dữ liệu cho collection: {collection_name}")
        return
    
    # Search functionality
    col1, col2 = st.columns([3, 1])
    with col1:
        search_term = st.text_input(
            "🔍 Tìm kiếm trong collection này:", 
            placeholder="Nhập từ khóa để tìm kiếm...",
            help="Tìm kiếm trong tiêu đề, mô tả và tóm tắt",
            key=f"search_{collection_name}"
        )
    with col2:
        st.markdown(f"""
        <div class="stats-container" style="margin: 0;">
            <div class="stat-item">
                <div class="stat-number">{len(articles)}</div>
                <div class="stat-label">Tổng bài viết</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Filter articles based on search
    filtered_articles = []
    if search_term:
        for article in articles:
            title = article.get('title', '').lower()
            description = article.get('description', '').lower()
            summary = article.get('summary', '').lower()
            search_lower = search_term.lower()
            
            if (search_lower in title or 
                search_lower in description or 
                search_lower in summary):
                filtered_articles.append(article)
        
        if filtered_articles:
            st.success(f"🔍 Tìm thấy {len(filtered_articles)} bài viết phù hợp với '{search_term}'")
        else:
            st.warning(f"🔍 Không tìm thấy bài viết nào phù hợp với '{search_term}'")
            return
    else:
        filtered_articles = articles
    
    # Display articles in columns
    if filtered_articles:
        col1, col2 = st.columns([1, 1], gap="medium")
        
        for idx, article in enumerate(filtered_articles):
            with col1 if idx % 2 == 0 else col2:
                with st.container():
                    st.markdown("""
                    <style>
                    .stContainer > div {
                        background: white;
                        border-radius: 15px;
                        padding: 1.5rem;
                        margin-bottom: 1.5rem;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                        border: 1px solid #e1e8ed;
                        position: relative;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    create_news_card(article, f"{collection_name}_{idx}")

# Hàm chính
def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>📰 The Doms </h1>
        <p style="margin: 0; font-size: 1.1rem; opacity: 0.9;">Feel lost in tech headlines? Find insight at The Doms</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Kết nối MongoDB
    client = init_connection()
    
    if not client:
        st.error("❌ Không thể kết nối đến MongoDB")
        return
    
    # Lấy danh sách collections
    available_collections = get_collections(client)
    
    if not available_collections:
        st.warning("⚠️ Không tìm thấy collections nào")
        return
    
    # Sidebar với chatbot
    with st.sidebar:
        # Thống kê tổng quan
        st.markdown("### 📊 Thống kê tổng quan")
        st.markdown(f"""
        <div class="stats-container">
            <div class="stat-item">
                <div class="stat-number">{len(available_collections)}</div>
                <div class="stat-label">Collections</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Hiển thị danh sách collections
        with st.expander("📋 Danh sách Collections"):
            for i, coll in enumerate(available_collections, 1):
                st.write(f"{i}. **{coll}**")
        st.divider()
        
        st.markdown("### 🤖 AI Assistant")
        with st.popover("💬 Chat với AI", use_container_width=True):
            st.markdown("### 🤖 Chatbot Tin Tức")
            st.components.v1.html("""
                <iframe
                    src="http://localhost:8501/embed=true"
                    style="height: 500px; width: 100%; border: none; border-radius: 8px;"
                ></iframe>
            """, height=520)
    
    
    # Tạo tabs với tên rút gọn để hiển thị đẹp hơn
    tab_names = ["Insights","Hot"] + [f"📰 {coll[:15]}{'...' if len(coll) > 15 else ''}" for coll in available_collections]
    tabs = st.tabs(tab_names)
    
    # Tab Insights
    with tabs[0]:
        display_insights_tab(client, available_collections)

    with tabs[1]:
        display_hotkeyword_insights(client) 
    
    # Tabs cho từng collection
    for i, collection_name in enumerate(available_collections):
        with tabs[i + 2]:
            st.markdown(f"<div class='tab-content'>", unsafe_allow_html=True)
            st.markdown(f"### 📰 Collection: {collection_name}")
            display_collection_content(client, collection_name)
            st.markdown("</div>", unsafe_allow_html=True)
    
    # Footer
    st.markdown(f"""
    <div style="text-align: center; padding: 2rem; color: #666; border-top: 1px solid #eee; margin-top: 3rem;">
        <p>© 2024 Tech News Hub | Được phát triển với ❤️ bằng Streamlit</p>
        <p><small>Tổng cộng {len(available_collections)} collections - Cập nhật liên tục</small></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()