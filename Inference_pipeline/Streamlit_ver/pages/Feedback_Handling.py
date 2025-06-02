import streamlit as st
from pymongo import MongoClient
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import pytz
from datetime import datetime
import re

# Cài đặt tiêu đề trang và bố cục
st.set_page_config(
    page_title="AI News - Báo Cáo Lỗi",
    layout="centered",
    page_icon="🔧",
    initial_sidebar_state="collapsed"
)

# Custom CSS để làm đẹp giao diện
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    .main-header p {
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
        opacity: 0.9;
    }
    
    .info-box {
        background-color: #f8f9fa;
        border-left: 4px solid #667eea;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
        text-align: center;
    }
    
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
        text-align: center;
    }
    
    .form-section {
        background-color: white;
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    
    .section-header {
        color: #667eea;
        font-size: 1.3rem;
        font-weight: 600;
        margin-bottom: 1rem;
        border-bottom: 2px solid #e9ecef;
        padding-bottom: 0.5rem;
    }
    
    .stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 25px;
        font-weight: 600;
        font-size: 1.1rem;
        transition: all 0.3s ease;
        width: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    
    .required-field {
        color: #dc3545;
    }
</style>
""", unsafe_allow_html=True)

# Kết nối MongoDB
@st.cache_resource
def init_mongodb():
    try:
        mongoclient = os.getenv("MONGO_CLIENT")
        if not mongoclient:
            st.error("🔧 Lỗi cấu hình: Không tìm thấy MONGO_CLIENT")
            return None, None
        client = MongoClient(mongoclient)
        db = client["AI_News_Error"]
        error_reports_collection = db["ErrorReportsDB"]
        return client, error_reports_collection
    except Exception as e:
        st.error(f"🔧 Lỗi kết nối MongoDB: {e}")
        return None, None

# Hàm validate email
def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# Hàm gửi email thông báo
def send_email_notification(user_name, user_email, error_description, error_type, error_data_type=None):
    sender_email = os.getenv("SENDER_MAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    receiver_email = os.getenv("RECEIVER_MAIL")
    
    if not all([sender_email, sender_password, receiver_email]):
        st.warning("⚠️ Cấu hình email chưa đầy đủ. Báo cáo đã được lưu nhưng không thể gửi email thông báo.")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = f"🔧 [News-Bot] Báo cáo lỗi mới từ {user_name}"
        
        # Xử lý description để tránh lỗi backslash trong f-string
        formatted_description = error_description.replace('\n', '<br>')
        data_type_html = f"<p><strong>Loại dữ liệu lỗi:</strong> {error_data_type}</p>" if error_data_type else ""
        
        body = f"""
        <html>
        <body>
        <h2 style="color: #667eea;">Báo cáo lỗi mới từ AI NEWs</h2>
        
        <p><strong>Người báo cáo:</strong> {user_name}</p>
        <p><strong>Email liên hệ:</strong> {user_email}</p>
        <p><strong>Loại lỗi:</strong> {error_type}</p>
        {data_type_html}
        
        <h3 style="color: #667eea;">Mô tả chi tiết:</h3>
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px;">
        {formatted_description}
        </div>
        
        <p style="margin-top: 20px; color: #6c757d;">
        <em>Email này được gửi tự động từ hệ thống AI NEWs</em>
        </p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        return True
        
    except Exception as e:
        st.error(f"❌ Không thể gửi email thông báo: {e}")
        return False

# Header chính
st.markdown("""
<div class="main-header">
    <h1>🔧 Báo Cáo Lỗi</h1>
    <p>AI NEWs - Hỗ trợ khắc phục sự cố</p>
</div>
""", unsafe_allow_html=True)

# Thông tin giới thiệu
st.markdown("""
<div class="info-box">
    <h4>📋 Hướng dẫn báo cáo lỗi</h4>
    <p><strong>AI NEWs</strong> luôn nỗ lực cung cấp dịch vụ tốt nhất. Nếu bạn gặp phải lỗi hoặc sự cố, 
    vui lòng báo cáo chi tiết để chúng tôi có thể khắc phục kịp thời.</p>
    <p>✨ <strong>Cam kết:</strong> Chúng tôi sẽ xem xét và phản hồi trong vòng 24 giờ.</p>
</div>
""", unsafe_allow_html=True)

# Form báo cáo lỗi
with st.container():
    st.markdown('<div class="form-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">👤 Thông tin liên hệ</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        user_name = st.text_input(
            "Họ và tên *",
            placeholder="Nhập họ tên của bạn",
            help="Thông tin này giúp chúng tôi liên hệ lại với bạn"
        )
    with col2:
        user_email = st.text_input(
            "Email liên hệ *",
            placeholder="example@email.com",
            help="Email để chúng tôi phản hồi kết quả xử lý"
        )
    
    st.markdown('</div>', unsafe_allow_html=True)

# Thông tin lỗi
with st.container():
    st.markdown('<div class="form-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">🐛 Thông tin lỗi</div>', unsafe_allow_html=True)
    
    error_type = st.selectbox(
        "Loại lỗi *",
        ["", "🖼️ Lỗi giao diện", "⚙️ Lỗi chức năng", "🌐 Lỗi kết nối", "📊 Lỗi thông tin", "❓ Khác"],
        help="Chọn loại lỗi phù hợp nhất với vấn đề bạn gặp phải"
    )
    
    error_data_type = None
    if error_type == "📊 Lỗi thông tin":
        error_data_type = st.selectbox(
            "Loại thông tin bị lỗi *",
            ["Chính trị",
             "Thời sự",
             "Kinh doanh",
             "Dân tộc và Tôn giáo",
             "Thể thao",
             "Giáo dục",
             "Thế giới",
             "Đời sống",
             "Văn hóa - Giải trí",
             "Sức khỏe",
             "Công nghệ",
             "Pháp luật",
             "Bất động sản",
             "Du lịch"
            ],
            help="Chi tiết loại thông tin có vấn đề"
        )
    
    error_description = st.text_area(
        "Mô tả chi tiết lỗi *",
        placeholder="Vui lòng mô tả chi tiết:\n- Bạn đang thực hiện thao tác gì?\n- Lỗi xuất hiện như thế nào?\n- Có thông báo lỗi nào không?\n- Bạn mong muốn điều gì xảy ra?",
        height=150,
        help="Mô tả càng chi tiết càng giúp chúng tôi khắc phục nhanh chóng"
    )
    
    st.markdown('</div>', unsafe_allow_html=True)

# Validation và gửi báo cáo
st.markdown("---")

# Kiểm tra validation
validation_errors = []
if st.button("🚀 Gửi báo cáo", key="submit_report"):
    if not user_name.strip():
        validation_errors.append("Vui lòng nhập họ tên")
    if not user_email.strip():
        validation_errors.append("Vui lòng nhập email")
    elif not validate_email(user_email):
        validation_errors.append("Email không hợp lệ")
    if not error_type or error_type == "":
        validation_errors.append("Vui lòng chọn loại lỗi")
    if error_type == "📊 Lỗi thông tin" and (not error_data_type or error_data_type == ""):
        validation_errors.append("Vui lòng chọn loại thông tin bị lỗi")
    if not error_description.strip():
        validation_errors.append("Vui lòng mô tả chi tiết lỗi")
    
    if validation_errors:
        st.markdown(f"""
        <div class="error-box">
            <h4>❌ Vui lòng kiểm tra lại thông tin:</h4>
            <ul style="text-align: left; margin-left: 20px;">
                {''.join([f"<li>{error}</li>" for error in validation_errors])}
            </ul>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Khởi tạo kết nối MongoDB
        client, error_reports_collection = init_mongodb()
        
        if error_reports_collection is not None:
            # Lấy múi giờ Việt Nam
            vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
            vn_time = datetime.now(vn_tz)
            
            # Tạo dữ liệu báo cáo
            report_data = {
                "name": user_name.strip(),
                "email": user_email.strip(),
                "description": error_description.strip(),
                "error_type": error_type,
                "error_data_type": error_data_type,
                "timestamp": vn_time.strftime('%Y-%m-%d %H:%M:%S'),
                "status": "new"
            }
            
            try:
                # Lưu vào MongoDB
                result = error_reports_collection.insert_one(report_data)
                
                # Gửi email thông báo
                email_sent = send_email_notification(
                    user_name, user_email, error_description, 
                    error_type, error_data_type
                )
                
                # Hiển thị thông báo thành công
                st.markdown(f"""
                <div class="success-box">
                    <h4>✅ Báo cáo đã được gửi thành công!</h4>
                    <p>Cảm ơn <strong>{user_name}</strong>, chúng tôi đã nhận được báo cáo của bạn.</p>
                    <p>📧 Mã báo cáo: <code>{str(result.inserted_id)[:8]}...</code></p>
                    <p>🕒 Chúng tôi sẽ xử lý và phản hồi trong vòng 24 giờ.</p>
                    {f"<p>📬 Email thông báo đã được gửi đến quản trị viên.</p>" if email_sent else ""}
                </div>
                """, unsafe_allow_html=True)
                
                # Auto refresh sau 3 giây
                time.sleep(3)
                st.rerun()
                
            except Exception as e:
                st.markdown(f"""
                <div class="error-box">
                    <h4>❌ Có lỗi xảy ra khi lưu báo cáo</h4>
                    <p>Lỗi: {str(e)}</p>
                    <p>Vui lòng thử lại sau ít phút.</p>
                </div>
                """, unsafe_allow_html=True)

# Footer
st.markdown("---")
