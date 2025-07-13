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


import pymongo
from qdrant_client import QdrantClient
from pymongo import MongoClient

from deeplearning_ai.Keyword_Insight.config import Config
from deeplearning_ai.Keyword_Insight.services.summarizer import BulletPointSummarizer
from deeplearning_ai.Keyword_Insight.services.keyword_extractor import KeywordMaker
from deeplearning_ai.Keyword_Insight.services.trend_analyzer import AITrendAnalyzer
from deeplearning_ai.Keyword_Insight.services.translator import Translator
from deeplearning_ai.Keyword_Insight.utils.database import get_mongodb_data, generate_embeddings_from_field

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


import json
import logging
import pymongo
from qdrant_client import QdrantClient
from pymongo import MongoClient

from deeplearning_ai.Keyword_Insight.config import Config
from deeplearning_ai.Keyword_Insight.services.summarizer import BulletPointSummarizer
from deeplearning_ai.Keyword_Insight.services.keyword_extractor import KeywordMaker
from deeplearning_ai.Keyword_Insight.services.trend_analyzer import AITrendAnalyzer
from deeplearning_ai.Keyword_Insight.services.translator import Translator
from deeplearning_ai.Keyword_Insight.utils.database import get_mongodb_data, generate_embeddings_from_field

def extract_source_data():
    """
    Extract data from source MongoDB collection.
    
    Returns:
        tuple: (titles, abstracts, contents, publish_dates)
    """
    logger.info("Extracting data from source MongoDB...")
    
    # Connect to source MongoDB
    client = pymongo.MongoClient(Config.get_mongodb_source_uri())
    db = client[Config.SOURCE_DB_NAME]
    collection = db[Config.SOURCE_COLLECTION_NAME]
    
    # Extract data
    docs = collection.find()
    titles, abstracts, contents, publish_dates = [], [], [], []
    
    for doc in docs:
        titles.append(doc["title"])
        abstracts.append(doc["abstract"])
        contents.append(doc["content"])
        publish_dates.append(doc["published"])
    
    logger.info(f"Extracted {len(titles)} documents from source")
    return titles, abstracts, contents, publish_dates

def process_content(contents):
    """
    Process content by generating summaries and keywords.
    
    Args:
        contents (list): List of content strings
        
    Returns:
        tuple: (summaries, keywords)
    """
    logger.info("Processing content: generating summaries...")
    
    # Generate summaries
    summarizer = BulletPointSummarizer()
    summaries = []
    for i, content in enumerate(contents):
        logger.info(f"Processing summary {i+1}/{len(contents)}")
        summary = summarizer.create_summary(content)
        summaries.append(summary)
    
    logger.info("Processing content: extracting keywords...")
    
    # Extract keywords
    keyword_maker = KeywordMaker()
    keywords = []
    for i, summary in enumerate(summaries):
        logger.info(f"Processing keywords {i+1}/{len(summaries)}")
        keyword_list = keyword_maker.create_keywords_from_content(summary)
        keywords.append(keyword_list)
    
    return summaries, keywords

def save_processed_data(titles, abstracts, contents, summaries, keywords, publish_dates):
    """
    Save processed data to JSON file and target MongoDB.
    
    Args:
        titles, abstracts, contents, summaries, keywords, publish_dates: Data lists
    """
    logger.info("Saving processed data...")
    
    # Prepare data structure
    data = []
    for t, a, c, s, k, p in zip(titles, abstracts, contents, summaries, keywords, publish_dates):
        data.append({
            "title": t,
            "abstract": a,
            "content": c,
            "summary": s,
            "keywords": k,
            "published": p
        })
    
    # Save to JSON file
    with open(Config.OUTPUT_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    logger.info(f"Data saved to {Config.OUTPUT_JSON_FILE}")
    
    # Save to target MongoDB
    client = pymongo.MongoClient(Config.get_mongodb_target_uri())
    db = client[Config.TARGET_DB_NAME]
    collection = db[Config.TARGET_COLLECTION_NAME]
    
    # Clear existing data and insert new data
    collection.delete_many({})
    collection.insert_many(data)
    logger.info(f"Data saved to MongoDB: {Config.TARGET_DB_NAME}.{Config.TARGET_COLLECTION_NAME}")

def generate_embeddings():
    """
    Generate and store embeddings in Qdrant.
    
    Returns:
        tuple: (qdrant_content, embeddings)
    """
    logger.info("Generating embeddings...")
    
    # Get data from MongoDB
    data = get_mongodb_data(Config.get_mongodb_target_uri())
    
    # Generate embeddings
    qdrant_content, embeddings = generate_embeddings_from_field(
        data,
        field_name="content",
        collection_name=Config.QDRANT_COLLECTION_NAME,
        qdrant_url=Config.QDRANT_URL,
        qdrant_api_key=Config.QDRANT_API_KEY
    )
    
    return qdrant_content, embeddings

def generate_insights(embeddings):
    """
    Generate insights for each keyword.
    
    Args:
        embeddings: Embedding model instance
    """
    logger.info("Generating insights...")
    
    # Initialize clients
    qdrant_client = QdrantClient(url=Config.QDRANT_URL, api_key=Config.QDRANT_API_KEY)
    mongo_client = MongoClient(Config.get_mongodb_target_uri())
    insight_db = mongo_client[Config.INSIGHT_DB_NAME]
    
    # Initialize services
    analyzer = AITrendAnalyzer()
    translator = Translator()
    
    for k, keyword in enumerate(Config.ANALYSIS_KEYWORDS):
        logger.info(f"Processing keyword: {keyword}")
        
        # Search for relevant content
        query_vector = embeddings.embed_query(f"Most relevant contents with keyword {keyword}")
        results = qdrant_client.search(
            collection_name=Config.QDRANT_COLLECTION_NAME,
            query_vector=query_vector,
            limit=Config.SEARCH_LIMIT
        )
        
        # Extract content and dates
        contents, dates = [], []
        for result in results:
            contents.append(result.payload["page_content"])
            dates.append(result.payload["metadata"]["date"])
        
        # Sort by date
        zipped = sorted(zip(dates, contents), key=lambda x: x[0])
        formatted_content = "\n\n".join([f"Date: {d}\nContent: {c}" for d, c in zipped])
        
        # Generate insights
        insight = analyzer.analyze(formatted_content, keyword)
        vi_insight = translator.translate(insight)
        
        # Prepare document
        doc = {
            "llms": Config.OPENAI_MODEL,
            "keyword": keyword,
            "content": contents,
            "date": dates,
            "en_insight": insight,
            "vi_insight": vi_insight
        }
        
        # Save to MongoDB
        collection_name = f"Topic{k+1}"
        insight_db[collection_name].insert_one(doc)
        logger.info(f"Insight saved to collection: {collection_name}")


default_args = {
    'owner': 'ai_news_pipeline',
    'depends_on_past': False,
    'start_date': datetime(2025, 7, 13),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='ai_news_insight_pipeline',
    default_args=default_args,
    schedule_interval='@daily',  # hoặc cron: '0 3 * * *'
    catchup=False,
) as dag:

    def extract_and_push(**context):
        titles, abstracts, contents, publish_dates = extract_source_data()
        context['ti'].xcom_push(key='titles', value=titles)
        context['ti'].xcom_push(key='abstracts', value=abstracts)
        context['ti'].xcom_push(key='contents', value=contents)
        context['ti'].xcom_push(key='publish_dates', value=publish_dates)

    def process_and_push(**context):
        contents = context['ti'].xcom_pull(key='contents')
        summaries, keywords = process_content(contents)
        context['ti'].xcom_push(key='summaries', value=summaries)
        context['ti'].xcom_push(key='keywords', value=keywords)

    def save_data(**context):
        save_processed_data(
            context['ti'].xcom_pull(key='titles'),
            context['ti'].xcom_pull(key='abstracts'),
            context['ti'].xcom_pull(key='contents'),
            context['ti'].xcom_pull(key='summaries'),
            context['ti'].xcom_pull(key='keywords'),
            context['ti'].xcom_pull(key='publish_dates')
        )

    extract_task = PythonOperator(
        task_id='extract_source_data',
        python_callable=extract_and_push,
        provide_context=True,
    )

    process_task = PythonOperator(
        task_id='process_content',
        python_callable=process_and_push,
        provide_context=True,
    )

    save_task = PythonOperator(
        task_id='save_processed_data',
        python_callable=save_data,
        provide_context=True,
    )

    embedding_task = PythonOperator(
        task_id='generate_embeddings',
        python_callable=generate_embeddings
    )

    insight_task = PythonOperator(
        task_id='generate_insights',
        python_callable=generate_insights
    )

    # Define task order
    extract_task >> process_task >> save_task >> embedding_task >> insight_task