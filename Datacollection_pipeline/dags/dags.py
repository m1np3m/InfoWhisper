from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import asyncio
import os
from dotenv import load_dotenv
from crawler import VietnamnetCrawler

# Load environment variables from .env file
load_dotenv()

default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
}

DEFAULT_MAX_ARTICLES = int(os.getenv('DEFAULT_MAX_ARTICLES', 10))

NEWS_CATEGORIES = [
    {"url": "https://vietnamnet.vn/tin-tuc-24h?bydaterang=&cate=00MK8V", "category_name": "cong-nghe", "max_articles": DEFAULT_MAX_ARTICLES},
    {"url": "https://vietnamnet.vn/tin-tuc-24h?bydaterang=&cate=000001", "category_name": "chinh-tri", "max_articles": DEFAULT_MAX_ARTICLES},
    {"url": "https://vietnamnet.vn/tin-tuc-24h?bydaterang=&cate=000006", "category_name": "giao-duc", "max_articles": DEFAULT_MAX_ARTICLES},
    {"url": "https://vietnamnet.vn/tin-tuc-24h?bydaterang=&cate=000005", "category_name": "the-gioi", "max_articles": DEFAULT_MAX_ARTICLES},
    {"url": "https://vietnamnet.vn/tin-tuc-24h?bydaterang=&cate=000008", "category_name": "phap-luat", "max_articles": DEFAULT_MAX_ARTICLES},
    {"url": "https://vietnamnet.vn/tin-tuc-24h?bydaterang=&cate=000007", "category_name": "doi-song", "max_articles": DEFAULT_MAX_ARTICLES},
]

MONGO_URI = os.getenv('MONGO_URI')
DB_NAME = os.getenv('MONGO_DB_NAME')
ENABLE_SUMMARIZER = os.getenv('ENABLE_SUMMARIZER', 'True').lower() in ('true', '1', 'yes')

def crawl_category(category_url, category_name, max_articles, enable_summarizer=True):
    asyncio.run(_crawl_category(category_url, category_name, max_articles, enable_summarizer))

async def _crawl_category(category_url, category_name, max_articles, enable_summarizer=True):
    crawler = VietnamnetCrawler(
        base_url=category_url,
        category_name=category_name,
        max_articles=max_articles,
        mongo_uri=MONGO_URI,
        db_name=DB_NAME,
        enable_summarizer=enable_summarizer
    )
    await crawler.crawl_all_articles()
    crawler.save_results()

with DAG(
    dag_id='vietnamnet_crawler_24h',
    default_args=default_args,
    schedule_interval=timedelta(minutes=30),
    start_date=datetime(2025, 5, 1),
    catchup=False,
    tags=['crawler', 'vietnamnet', 'mongodb'],
    description='Crawl tin tức từ VietnamNet 24h theo danh mục, tạo tóm tắt sử dụng LLM và lưu vào MongoDB.',
) as dag:

    # Tạo danh sách tasks
    tasks = []

    for category in NEWS_CATEGORIES:
        task = PythonOperator(
            task_id=f"crawl_{category['category_name']}",
            python_callable=crawl_category,
            op_kwargs={
                'category_url': category['url'],
                'category_name': category['category_name'],
                'max_articles': category['max_articles'],
                'enable_summarizer': ENABLE_SUMMARIZER
            },
            execution_timeout=timedelta(minutes=15),
        )
        tasks.append(task)

    # Thiết lập tuần tự chạy: task1 >> task2 >> task3 ...
    for i in range(1, len(tasks)):
        tasks[i - 1] >> tasks[i]
