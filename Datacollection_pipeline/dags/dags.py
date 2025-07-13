from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import asyncio
import os
from dotenv import load_dotenv
from deeplearning_ai.crawler_deeplai import DeepLearningAICrawler
from deeplearning_ai.Insight import InsightSummarizer
import logging
from langfuse import get_client
from langfuse.langchain import CallbackHandler
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os
from langfuse import get_client
import logging
import json
# Load environment variables from .env file
load_dotenv()

lf = get_client()
handler = CallbackHandler()

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

default_args = {
    'owner': 'airflow',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
}

# Cấu hình từ environment variables
DEFAULT_MAX_ARTICLES = int(os.getenv('DEFAULT_MAX_ARTICLES', 30))
DEFAULT_MIN_ARTICLES_THRESHOLD = int(os.getenv('DEFAULT_MIN_ARTICLES_THRESHOLD', 5))
DEFAULT_MAX_LOAD_MORE_CLICKS = int(os.getenv('DEFAULT_MAX_LOAD_MORE_CLICKS', 1))
MONGO_URI = os.getenv('MONGO_URI', 'mongodb+srv://vinhthuanly210:Vinhthuanly123@cluster0.mznyroo.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
SOURCE_DB_NAME = os.getenv('MONGO_DB_NAME_DEEP', 'deeplearning_ai_news')
INSIGHT_DB_NAME = os.getenv('INSIGHT_DB_NAME', 'deeplearning_ai_insight')

# Danh sách các categories với URLs tương ứng
DEEPAI_CATEGORIES = [
    {
        "url": "https://www.deeplearning.ai/the-batch/tag/hardware/",
        "category_name": "hardware",
        "max_articles": DEFAULT_MAX_ARTICLES,
        "min_articles_threshold": DEFAULT_MIN_ARTICLES_THRESHOLD,
        "max_load_more_clicks": DEFAULT_MAX_LOAD_MORE_CLICKS
    },
    {
        "url": "https://www.deeplearning.ai/the-batch/tag/culture/",
        "category_name": "culture",
        "max_articles": DEFAULT_MAX_ARTICLES,
        "min_articles_threshold": DEFAULT_MIN_ARTICLES_THRESHOLD,
        "max_load_more_clicks": DEFAULT_MAX_LOAD_MORE_CLICKS
    },
    {
        "url": "https://www.deeplearning.ai/the-batch/tag/science/",
        "category_name": "science",
        "max_articles": DEFAULT_MAX_ARTICLES,
        "min_articles_threshold": DEFAULT_MIN_ARTICLES_THRESHOLD,
        "max_load_more_clicks": DEFAULT_MAX_LOAD_MORE_CLICKS
    },
    {
        "url": "https://www.deeplearning.ai/the-batch/tag/business/",
        "category_name": "business",
        "max_articles": DEFAULT_MAX_ARTICLES,
        "min_articles_threshold": DEFAULT_MIN_ARTICLES_THRESHOLD,
        "max_load_more_clicks": DEFAULT_MAX_LOAD_MORE_CLICKS
    },
    {
        "url": "https://www.deeplearning.ai/the-batch/tag/research/",
        "category_name": "ml-research",
        "max_articles": DEFAULT_MAX_ARTICLES,
        "min_articles_threshold": DEFAULT_MIN_ARTICLES_THRESHOLD,
        "max_load_more_clicks": DEFAULT_MAX_LOAD_MORE_CLICKS
    },
    {
        "url": "https://www.deeplearning.ai/the-batch/tag/data-points/",
        "category_name": "data-points",
        "max_articles": DEFAULT_MAX_ARTICLES,
        "min_articles_threshold": DEFAULT_MIN_ARTICLES_THRESHOLD,
        "max_load_more_clicks": DEFAULT_MAX_LOAD_MORE_CLICKS
    }
]

def crawl_deepai_category(category_url, category_name, max_articles, min_articles_threshold, max_load_more_clicks):
    """Crawl một category từ DeepLearning.AI"""
    try:
        logger.info(f"Bắt đầu crawl category: {category_name}")
        
        # Chạy async crawler
        asyncio.run(_crawl_deepai_category(category_url, category_name, max_articles, min_articles_threshold, max_load_more_clicks))
        
        logger.info(f"Hoàn thành crawl category: {category_name}")
        
    except Exception as e:
        logger.error(f"Lỗi khi crawl category {category_name}: {str(e)}")
        raise

async def _crawl_deepai_category(category_url, category_name, max_articles, min_articles_threshold, max_load_more_clicks):
    """Async function để crawl category"""
    load_dotenv()
    crawler = DeepLearningAICrawler(
        base_url=category_url,
        category_name=category_name,
        max_articles=max_articles,
        mongo_uri=MONGO_URI,
        db_name=SOURCE_DB_NAME,
        max_load_more_clicks=max_load_more_clicks,
        min_articles_threshold=min_articles_threshold,
        lf=lf,
        handler=handler
    )
    
    # Crawl tất cả bài viết
    await crawler.crawl_all_articles()
    
    # Lưu kết quả vào MongoDB
    crawler.save_results()


    

def generate_monthly_insights():
    """Tạo insights riêng cho từng collection từ dữ liệu đã crawl trong tháng qua"""
    try:
        logger.info("Bắt đầu tạo insights cho từng category từ dữ liệu tháng qua")
        
        # Lấy danh sách các collection từ categories
        collections = [cat["category_name"] for cat in DEEPAI_CATEGORIES]
        
        # Khởi tạo InsightSummarizer với database riêng biệt
        summarizer = InsightSummarizer(
            mongo_uri=MONGO_URI,
            source_db_name=SOURCE_DB_NAME,
            collections=collections,
            insight_db_name=INSIGHT_DB_NAME
        )
        
        # Sử dụng method save_insights_to_db để lưu insights cho từng collection
        logger.info("Tạo insights riêng cho từng category và lưu vào database...")
        saved_count = summarizer.save_insights_to_db(
            k=1,  # 1 tháng
            max_tokens=10000,
            reference_date=datetime.now()
        )
        
        if saved_count > 0:
            logger.info(f"Đã tạo và lưu thành công {saved_count} insights vào database '{INSIGHT_DB_NAME}'")
            
            # Log thống kê database
            stats = summarizer.get_database_stats()
            logger.info(f"Thống kê Insight Database: {stats['total_insights']} insights trong {len(stats['collections'])} collections")
            
        else:
            logger.warning("Không có insights nào được tạo. Có thể không có dữ liệu trong tháng qua.")
        
        logger.info("Hoàn thành tạo insights tháng")
        
    except Exception as e:
        logger.error(f"Lỗi khi tạo insights: {str(e)}")
        raise



# Định nghĩa DAG cho crawler (chạy mỗi 10 phút)
with DAG(
    dag_id='deepai_crawler_10min',
    default_args=default_args,
    schedule_interval=timedelta(minutes=10),
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['crawler', 'deeplearning.ai', 'mongodb'],
    description='Crawl bài viết từ DeepLearning.AI mỗi 10 phút theo danh mục và lưu vào MongoDB.',
) as crawler_dag:

    # Tạo tasks cho từng category
    crawler_tasks = []

    for category in DEEPAI_CATEGORIES:
        task = PythonOperator(
            task_id=f"crawl_{category['category_name']}",
            python_callable=crawl_deepai_category,
            op_kwargs={
                'category_url': category['url'],
                'category_name': category['category_name'],
                'max_articles': category['max_articles'],
                'min_articles_threshold': category['min_articles_threshold'],
                'max_load_more_clicks': category['max_load_more_clicks']
            },
            execution_timeout=timedelta(minutes=20),  # Timeout cho mỗi task
        )
        crawler_tasks.append(task)

    # Thiết lập dependencies: chạy tuần tự để tránh overload
    for i in range(1, len(crawler_tasks)):
        crawler_tasks[i - 1] >> crawler_tasks[i]

# Định nghĩa DAG riêng cho insights (chạy mỗi tháng)
with DAG(
    dag_id='deepai_monthly_insights',
    default_args=default_args,
    schedule_interval='@monthly',  # Chạy vào ngày đầu tiên của mỗi tháng
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['insights', 'deeplearning.ai', 'monthly', 'collection-specific'],
    description='Tạo insights riêng cho từng collection từ dữ liệu DeepLearning.AI mỗi tháng.',
) as insights_dag:

    insights_task = PythonOperator(
        task_id='generate_monthly_insights_per_collection',
        python_callable=generate_monthly_insights,
        execution_timeout=timedelta(minutes=45),  # Tăng timeout vì xử lý nhiều collection
    )
