import asyncio
import re
import json
import os
from urllib.parse import urljoin, urlparse, parse_qs
from datetime import datetime
from crawl4ai import AsyncWebCrawler
from bs4 import BeautifulSoup
import nest_asyncio
from pymongo import MongoClient
from dotenv import load_dotenv
import time
from llm_summary import ArticleSummarizer
import logging
import pytz
from dateutil import parser
# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

nest_asyncio.apply()

class VietnamnetCrawler:
    def __init__(self, base_url, category_name, max_articles=5, 
                 mongo_uri=None, db_name=None, enable_summarizer=True):
        self.base_url = base_url
        self.category_name = category_name  # Tên category được truyền vào trực tiếp
        self.max_articles = max_articles
        self.articles = []
        self.mongo_uri = mongo_uri or os.getenv('MONGO_URI')
        self.db_name = db_name or os.getenv('MONGO_DB_NAME', 'vietnamnet_news')
        self.mongo_client = None
        self.db = None
        self._connect_mongodb()
        
        # Thiết lập ArticleSummarizer nếu được kích hoạt
        self.enable_summarizer = enable_summarizer
        self.summarizer = None
        if enable_summarizer:
            try:
                self.summarizer = ArticleSummarizer()
                logger.info("ArticleSummarizer đã được khởi tạo thành công")
            except Exception as e:
                logger.error(f"Không thể khởi tạo ArticleSummarizer: {str(e)}")
                self.enable_summarizer = False
    
    def _connect_mongodb(self):
        """Thiết lập kết nối MongoDB"""
        try:
            self.mongo_client = MongoClient(self.mongo_uri)
            self.db = self.mongo_client[self.db_name]
            logger.info(f"Đã kết nối thành công với MongoDB: {self.db_name}")
        except Exception as e:
            logger.error(f"Lỗi kết nối MongoDB: {str(e)}")
            self.mongo_client = None
            self.db = None

    def _close_mongodb(self):
        """Đóng kết nối MongoDB"""
        if self.mongo_client is not None:
            self.mongo_client.close()
            self.mongo_client = None
            self.db = None

    async def get_article_links(self):
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=self.base_url)
            soup = BeautifulSoup(result.html, 'html.parser')

            links = []

            # Quét toàn bộ thẻ <a> có href
            all_a_tags = soup.find_all('a', href=True)
            for a in all_a_tags:
                href = a['href']
                # Lọc link theo định dạng bài viết
                if re.search(r'-\d+\.html?$', href) and '#comment' not in href:
                    full_url = urljoin("https://vietnamnet.vn", href)
                    if full_url not in links:
                        links.append(full_url)

            logger.info(f"Tìm thấy {len(links)} link bài viết cho danh mục {self.category_name}")
            return list(set(links))[:self.max_articles]

    def filter_existing_urls(self, urls):
        if self.db is None:
            logger.warning("Không thể kết nối tới MongoDB để lọc URLs")
            return urls

        collection = self.db[self.category_name]
        url_id_map = {}
        for url in urls:
            match = re.search(r'-(\d+)\.html?$', url)
            if match:
                _id = match.group(1)
                url_id_map[url] = _id

        all_ids = list(url_id_map.values())
        existing_docs = list(collection.find({"_id": {"$in": all_ids}}, {"_id": 1, "is_live": 1, "url": 1}))
        existing_ids_set = set(doc["_id"] for doc in existing_docs)

        filtered_urls = [url for url, _id in url_id_map.items() if _id not in existing_ids_set]

        # Gọi hàm xử lý live URLs
        filtered_urls += self.handle_live_duplicates(collection, url_id_map, existing_docs)

        logger.info(f"Đã lọc: {len(urls)} URLs ban đầu -> {len(filtered_urls)} URLs sau xử lý live")
        return filtered_urls


    def handle_live_duplicates(self, collection, url_id_map, existing_docs):
        urls_to_crawl = []
        id_to_doc = {doc["_id"]: doc for doc in existing_docs}

        for url, _id in url_id_map.items():
            if _id in id_to_doc:
                doc = id_to_doc[_id]
                if doc.get("is_live") == 1 and doc.get("url") != url:
                    # Xóa bản cũ trong DB
                    collection.delete_one({"_id": _id})
                    # Thêm URL mới để crawl lại
                    urls_to_crawl.append(url)

        return urls_to_crawl



    async def crawl_article(self, url):
        try:
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=url)
                soup = BeautifulSoup(result.html, 'html.parser')

                def get_text(selector, default=""):
                    element = soup.select_one(selector)
                    return element.get_text(strip=True) if element else default

                title = get_text('h1.content-detail-title') or get_text('h1', "Không tìm thấy tiêu đề")
                author = get_text('.content-detail-author, .author-wrapper, .author', "Không có thông tin tác giả")

                publish_date = None
                meta_date = soup.select_one('meta[property="article:published_time"]')
                if meta_date:
                    publish_date = meta_date.get('content')
                if not publish_date:
                    publish_date = get_text('.content-detail-time, .publish-time, .time-now, .news-time')

                views = None
                view_el = soup.select_one('.view-count, .page-view, .article-views')
                if view_el:
                    views_match = re.search(r'(\d+[,\.]?\d*)', view_el.get_text())
                    if views_match:
                        views = views_match.group(1).replace(',', '').replace('.', '')

                tags = list({tag.get_text(strip=True) for tag in soup.select('.tags a, .article-tags a, .tag-item')})

                description = None
                meta_desc = soup.select_one('meta[name="description"]')
                if meta_desc:
                    description = meta_desc.get('content')
                if not description:
                    description = get_text('.article-sapo, .article-description, .content-detail-sapo')

                main_image = None
                meta_image = soup.select_one('meta[property="og:image"]')
                if meta_image:
                    main_image = meta_image.get('content')
                if not main_image:
                    img_el = soup.select_one('.content-detail-img img, .featured-image img')
                    if img_el:
                        main_image = img_el.get('src')
                        if main_image and main_image.startswith('/'):
                            main_image = urljoin("https://vietnamnet.vn", main_image)

                content_div = soup.select_one('.content-detail-body, .content-detail, .article-body')
                content = "Không tìm thấy nội dung chi tiết"
                if content_div:
                    for unwanted in content_div.select('.banner, .ads, .related, script, style'):
                        unwanted.decompose()
                    paragraphs = content_div.select('p')
                    content = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])

                schema_data = None
                for script in soup.select('script[type="application/ld+json"]'):
                    try:
                        data = json.loads(script.string)
                        if data.get('@type') in ['NewsArticle', 'Article', 'BlogPosting']:
                            schema_data = data
                            break
                    except:
                        pass

                if schema_data:
                    if not publish_date and 'datePublished' in schema_data:
                        publish_date = schema_data['datePublished']
                    if not author and 'author' in schema_data:
                        author_info = schema_data['author']
                        if isinstance(author_info, dict):
                            author = author_info.get('name', author)
                        elif isinstance(author_info, str):
                            author = author_info

                if publish_date:
                    publish_date = parser.parse(publish_date).replace(tzinfo=None)

                # Tạo tóm tắt nếu tính năng được kích hoạt và nội dung đủ dài
                bullet_summary = "Không có tóm tắt dạng bullet points"
                
                if self.enable_summarizer and self.summarizer is not None and content and len(content) > 100:
                    try:
                        logger.info(f"Đang tạo tóm tắt cho bài viết: {title}")
                        bullet_summary = self.summarizer.create_bullet_summary(content)
                        logger.info("Đã tạo tóm tắt thành công")
                    except Exception as e:
                        logger.error(f"Lỗi khi tạo tóm tắt: {str(e)}")

                is_live = 0
                if 'trực tiếp' in title.lower() or 'truc-tiep' in url.lower():
                    is_live = 1

                return {
                    'title': title,
                    'author': author,
                    'publish_date': publish_date,
                    'views': views,
                    'tags': tags,
                    'description': description,
                    'main_image': main_image,
                    'content': content,
                    #'bullet_summary': bullet_summary,
                    'url': url,
                    'category': self.category_name,
                    'crawled_at': datetime.now(pytz.timezone("Asia/Ho_Chi_Minh")).isoformat(),
                    'is_live': is_live
                }

        except Exception as e:
            logger.error(f"Lỗi khi crawl {url}: {str(e)}")
            return None

    async def crawl_all_articles(self):
        start_time = time.time()  # Bắt đầu đo thời gian
        article_links = await self.get_article_links()
        
        # Lọc các URL đã tồn tại trong database
        filtered_links = self.filter_existing_urls(article_links)
        
        if not filtered_links:
            logger.info(f"Không có bài viết mới nào trong danh mục {self.category_name} cần crawl.")
            return
            
        logger.info(f"Đang crawl {len(filtered_links)} bài viết mới từ danh mục {self.category_name}...")

        for url in filtered_links:
            logger.info(f"--> Crawl: {url}")
            article_data = await self.crawl_article(url)
            if article_data:
                self.articles.append(article_data)
                logger.info(f"    ✓ {article_data['title'][:60]}...\n")

        elapsed = time.time() - start_time
        logger.info(f"⏱️  Tổng thời gian crawl: {elapsed:.2f} giây")

    def save_to_mongodb(self):
        """Lưu các bài viết vào MongoDB theo collection tương ứng với danh mục"""
        try:
            if self.db is None:
                self._connect_mongodb()
                if self.db is None:
                    logger.error("Không thể kết nối tới MongoDB để lưu dữ liệu")
                    return False
                    
            collection = self.db[self.category_name]
            collection.create_index("publish_date", expireAfterSeconds=2678400)

            
            # Thêm trường ID từ URL (lấy phần số trong URL)
            for article in self.articles:
                # Lấy id từ url: ví dụ url: ...-123456.html
                match = re.search(r'-(\d+)\.html?$', article['url'])
                if match:
                    article['_id'] = match.group(1)
                else:
                    # Nếu không tìm thấy id, fallback dùng toàn bộ url (hoặc xử lý khác)
                    article['_id'] = article['url']
            
            if self.articles:
                result = collection.insert_many(self.articles, ordered=False)
                logger.info(f"Đã lưu {len(result.inserted_ids)} bài viết vào collection '{self.category_name}'")
            else:
                logger.info(f"Không có bài viết để lưu vào collection '{self.category_name}'")
                
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu dữ liệu vào MongoDB: {str(e)}")
            return False
        finally:
            self._close_mongodb()

    
    def save_results(self, file_path=None):
        """Lưu kết quả ra file JSON (nếu cần) và vào MongoDB"""
        # Lưu vào MongoDB
        mongo_result = self.save_to_mongodb()
        
        # Nếu có yêu cầu lưu file JSON
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(self.articles, f, ensure_ascii=False, indent=2)
                logger.info(f"Đã lưu {len(self.articles)} bài viết vào {file_path}")
            except Exception as e:
                logger.error(f"Không thể lưu file: {str(e)}")
        
        return mongo_result