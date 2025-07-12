import os
import streamlit as st
from pymongo import MongoClient
from datetime import datetime

# Cấu hình trang
st.set_page_config(
    page_title="AI News Error Report Manager", 
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS đơn giản và ổn định
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #4CAF50, #45a049);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
    }
    
    .report-card {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 15px;
        border-left: 4px solid #007bff;
        position: relative;
    }
    
    .report-actions {
        position: absolute;
        top: 15px;
        right: 15px;
        display: flex;
        gap: 10px;
    }
    
    .stat-card {
        background: white;
        padding: 20px;
        border-radius: 8px;
        text-align: center;
        border: 1px solid #dee2e6;
        margin: 10px 0;
    }
    
    .stat-number {
        font-size: 2em;
        font-weight: bold;
        color: #007bff;
    }
    
    .welcome-box {
        background: #e3f2fd;
        padding: 40px;
        border-radius: 10px;
        text-align: center;
        margin: 20px 0;
    }
    
    .delete-button {
        background-color: #dc3545;
        color: white;
        border: none;
        padding: 5px 10px;
        border-radius: 5px;
        cursor: pointer;
        font-size: 12px;
    }
    
    .delete-button:hover {
        background-color: #c82333;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'error_reports_collection' not in st.session_state:
    st.session_state.error_reports_collection = None
if 'reports' not in st.session_state:
    st.session_state.reports = []
if 'selected_reports' not in st.session_state:
    st.session_state.selected_reports = []
if 'connection_success' not in st.session_state:
    st.session_state.connection_success = False
if 'delete_confirmation' not in st.session_state:
    st.session_state.delete_confirmation = {}

# Sidebar
st.sidebar.title("🛠️ AI News Report Manager")
st.sidebar.markdown("---")

st.sidebar.markdown("### 📋 Giới thiệu")
st.sidebar.info("""
Ứng dụng quản lý báo cáo lỗi từ người dùng:
• Xem tất cả báo cáo
• Xóa báo cáo trực tiếp
• Thống kê tổng quan
• Làm mới dữ liệu
""")

st.sidebar.markdown("### 🔐 Đăng nhập MongoDB")
mongodb_user = st.sidebar.text_input("Username", placeholder="Nhập username")
mongodb_password = st.sidebar.text_input("Password", type="password", placeholder="Nhập password")

# Function to connect to MongoDB
def connect_to_mongodb(user, password):
    if user and password:
        try:
            connection_string = f"mongodb+srv://{user}:{password}@cluster0.awwcmy7.mongodb.net/"
            client = MongoClient(connection_string)
            st.session_state.error_reports_collection = client["AI_News_Error"]["ErrorReportsDB"]
            st.session_state.connection_success = True
            st.sidebar.success("✅ Kết nối thành công!")
            return True
        except Exception as e:
            st.session_state.connection_success = False
            st.sidebar.error(f"❌ Lỗi: {str(e)}")
            return False
    else:
        st.sidebar.warning("⚠️ Nhập đầy đủ thông tin!")
        return False

# Function to delete report
def delete_report(report_id, report_name):
    try:
        result = st.session_state.error_reports_collection.delete_one({"_id": report_id})
        if result.deleted_count > 0:
            st.success(f"✅ Đã xóa báo cáo của {report_name}!")
            # Refresh reports list
            st.session_state.reports = list(st.session_state.error_reports_collection.find())
            # Clear confirmation state
            if str(report_id) in st.session_state.delete_confirmation:
                del st.session_state.delete_confirmation[str(report_id)]
            st.rerun()
        else:
            st.error("❌ Không thể xóa báo cáo!")
    except Exception as e:
        st.error(f"❌ Lỗi khi xóa: {e}")

# Connection button
if st.sidebar.button("🔗 Kết nối", use_container_width=True):
    connect_to_mongodb(mongodb_user, mongodb_password)

# Main content
st.markdown('<div class="main-header"><h1>🛠️ AI News Error Report Manager</h1><p>Hệ thống quản lý báo cáo lỗi</p></div>', unsafe_allow_html=True)

if not st.session_state.connection_success:
    # Welcome screen
    st.markdown("""
    <div class="welcome-box">
        <h2>🔐 Chào mừng đến với hệ thống quản lý báo cáo lỗi</h2>
        <p>Vui lòng đăng nhập MongoDB ở sidebar để tiếp tục</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Feature cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="stat-card">
            <div class="stat-number">📊</div>
            <h4>Thống kê</h4>
            <p>Xem thống kê chi tiết</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="stat-card">
            <div class="stat-number">🚀</div>
            <h4>Nhanh chóng</h4>
            <p>Xử lý báo cáo hiệu quả</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="stat-card">
            <div class="stat-number">🔒</div>
            <h4>Bảo mật</h4>
            <p>Dữ liệu được bảo vệ</p>
        </div>
        """, unsafe_allow_html=True)

else:
    # Dashboard sau khi đăng nhập
    st.markdown("## 📋 Dashboard Quản Lý Báo Cáo")
    
    # Load reports
    if not st.session_state.reports:
        try:
            st.session_state.reports = list(st.session_state.error_reports_collection.find())
        except Exception as e:
            st.error(f"Lỗi khi tải dữ liệu: {e}")
            st.session_state.reports = []
    
    reports = st.session_state.reports
    
    # Statistics
    total_reports = len(reports)
    error_reports = len([r for r in reports if 'error_data_type' in r])
    
    # Stats row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{total_reports}</div>
            <h4>Tổng báo cáo</h4>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{error_reports}</div>
            <h4>Báo cáo lỗi</h4>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        unique_emails = len(set([r.get('email', '') for r in reports if r.get('email')]))
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{unique_emails}</div>
            <h4>Người dùng</h4>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="stat-card">
            <div class="stat-number">✅</div>
            <h4>Đã kết nối</h4>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Refresh button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 Làm mới dữ liệu"):
            try:
                st.session_state.reports = list(st.session_state.error_reports_collection.find())
                st.success("✅ Đã làm mới!")
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi khi làm mới: {e}")
    
    # Reports section
    if reports:
        st.markdown("### 📝 Danh sách báo cáo")
        st.markdown("*💡 Tip: Nhấn nút 🗑️ để xóa báo cáo trực tiếp*")
        
        # Display reports with individual delete buttons
        for i, report in enumerate(reports):
            report_id = report["_id"]
            report_id_str = str(report_id)
            name = report.get('name', 'Không xác định')
            email = report.get('email', 'Không có email')
            description = report.get('description', 'Không có mô tả')
            timestamp = report.get('timestamp', 'Không xác định')
            error_type = report.get('error_data_type', '')
            
            # Create container for each report
            with st.container():
                # Create columns for content and buttons
                col_content, col_actions = st.columns([5, 1])
                
                with col_content:
                    st.markdown(f"""
                    <div class="report-card">
                        <h4>👤 {name}</h4>
                        <p><strong>📧 Email:</strong> {email}</p>
                        <p><strong>🕒 Thời gian:</strong> {timestamp}</p>
                        <p><strong>📝 Nội dung:</strong> {description}</p>
                        {f'<p><strong>🚨 Loại lỗi:</strong> <span style="background: #ff6b6b; color: white; padding: 2px 8px; border-radius: 4px;">{error_type}</span></p>' if error_type else ''}
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_actions:
                    # Check if waiting for confirmation
                    if report_id_str in st.session_state.delete_confirmation:
                        st.write("⚠️ **Xác nhận xóa?**")
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("✅", key=f"confirm_{report_id_str}", help="Xác nhận xóa"):
                                delete_report(report_id, name)
                        with col_no:
                            if st.button("❌", key=f"cancel_{report_id_str}", help="Hủy bỏ"):
                                del st.session_state.delete_confirmation[report_id_str]
                                st.rerun()
                    else:
                        # Show delete button
                        if st.button("🗑️ Xóa", key=f"delete_{report_id_str}", help=f"Xóa báo cáo của {name}"):
                            st.session_state.delete_confirmation[report_id_str] = True
                            st.rerun()
                
                st.markdown("---")
    
    else:
        st.markdown("""
        <div class="welcome-box">
            <h3>📭 Không có báo cáo nào</h3>
            <p>Hiện tại chưa có báo cáo lỗi từ người dùng</p>
        </div>
        """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("*AI News Error Report Manager - Phiên bản 2.1*")