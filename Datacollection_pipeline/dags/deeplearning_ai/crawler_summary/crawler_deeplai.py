import asyncio
import re
import json
import os
from urllib.parse import urljoin, urlparse
from datetime import datetime
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from bs4 import BeautifulSoup
import nest_asyncio
from pymongo import MongoClient
from dotenv import load_dotenv
import time
import logging
import pytz
from dateutil import parser
from deeplearning_ai.crawler_summary.summary_gemini import ArticleSummarizer

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()
nest_asyncio.apply()

class DeepLearningAICrawler:
    def __init__(self, base_url="https://www.deeplearning.ai/the-batch/tag/research/",
                 category_name="research", max_articles=50, min_articles_threshold=30,
                 mongo_uri=None, db_name=None, max_load_more_clicks=10, lf=None, handler =None):
        self.base_url = base_url
        self.category_name = category_name
        self.max_articles = max_articles
        self.min_articles_threshold = min_articles_threshold  # Số bài tối thiểu để wait_for
        self.max_load_more_clicks = max_load_more_clicks  # Số lần click Load More tối đa
        self.articles = []
        self.mongo_uri = mongo_uri or os.getenv('MONGO_URI','mongodb+srv://vinhthuanly210:Vinhthuanly123@cluster0.mznyroo.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
        self.db_name = db_name or os.getenv('MONGO_DB_NAME_DEEP', 'deeplearning_ai_news')
        self.mongo_client = None
        self.db = None
        self.lf= lf
        self.handler = handler
        self._connect_mongodb()
        self.summarizer = ArticleSummarizer(lf=self.lf,handler=self.handler)

    def _connect_mongodb(self):
        """Thiết lập kết nối MongoDB"""
        try:
            if self.mongo_uri:
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

    async def get_article_links_with_load_more(self):
        """Crawl trang với tự động nhấn Load More để lấy tất cả bài viết"""
        
        # JavaScript được tối ưu dựa trên code hoạt động
        js_code = f"""
        (async () => {{
            const maxClicks = {self.max_load_more_clicks};
            let clickCount = 0;

            function getLoadMoreButton() {{
                // Thử selector chính xác đầu tiên
                let btn = document.querySelector('div[class*="buttons_secondary"][class*="text-center"]');
                return btn;
            }}

            function countValidArticles() {{
                const links = Array.from(document.querySelectorAll('a[href*="/the-batch/"]'));
                const valid = links.filter(a =>
                    !a.href.includes('/tag/') &&
                    !a.href.includes('/category/') &&
                    !a.href.includes('/author/') &&
                    !a.href.includes('/page/') &&
                    !a.href.endsWith('/the-batch/') &&
                    !a.href.endsWith('/the-batch') &&
                    !a.href.includes('#') &&
                    !a.href.includes('mailto:') &&
                    !a.href.includes('tel:')
                );
                return valid.length;
            }}

            console.log('🚀 Bắt đầu quá trình load bài viết...');
            let initialCount = countValidArticles();
            console.log(`📊 Số bài viết ban đầu: ${{initialCount}}`);

            for (let i = 0; i < maxClicks; i++) {{
                const btn = getLoadMoreButton();
                
                if (!btn || btn.offsetParent === null) {{
                    console.log(`❌ Không tìm thấy nút Load More sau ${{i}} lần click`);
                    break;
                }}

                // Scroll đến nút và click
                btn.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                
                try {{
                    btn.click();
                    clickCount++;
                    console.log(`✅ Clicked Load More lần thứ ${{clickCount}}`);
                }} catch (e) {{
                    console.log("❌ Lỗi khi click:", e);
                    break;
                }}

                // Scroll xuống một chút để trigger loading
                window.scrollBy(0, 500);
                
                // Đợi content load
                await new Promise(r => setTimeout(r, 500));
                
                const currentCount = countValidArticles();
                console.log(`📊 Số bài viết hiện tại: ${{currentCount}}`);
                
                // Nếu không tăng thêm bài viết, có thể đã hết
                if (currentCount === initialCount && i > 0) {{
                    console.log('⚠️ Không có bài viết mới, có thể đã load hết');
                    break;
                }}
                
                initialCount = currentCount;
            }}

            const finalCount = countValidArticles();
            console.log(`🏆 Hoàn thành! Tổng số bài viết: ${{finalCount}}, Đã click: ${{clickCount}} lần`);
            
            // Scroll lên đầu để chuẩn bị crawl
            window.scrollTo(0, 0);

            return {{ 
                success: true, 
                totalArticles: finalCount, 
                clickCount: clickCount 
            }};
        }})();
        """

        # Wait for condition với threshold có thể config
        wait_for_condition = f"""js:() => {{
            const links = Array.from(document.querySelectorAll('a[href*="/the-batch/"]'));
            const valid = links.filter(a =>
                !a.href.includes('/tag/') &&
                !a.href.includes('/category/') &&
                !a.href.includes('/author/') &&
                !a.href.includes('/about') &&
                !a.href.includes('/page/') &&
                !a.href.endsWith('/the-batch/') &&
                !a.href.endsWith('/the-batch') &&
                !a.href.includes('#') &&
                !a.href.includes('mailto:') &&
                !a.href.includes('tel:')
            );
            console.log(`Wait for check: ${{valid.length}} valid articles found`);
            return valid.length >= {self.min_articles_threshold};
        }}"""

        config = CrawlerRunConfig(
            js_code=js_code,
            wait_for=wait_for_condition,
            delay_before_return_html=2,
            page_timeout=30000,  # 30s
        )

        async with AsyncWebCrawler(headless=True, verbose=True) as crawler:

            logger.info(f"🌐 Đang truy cập: {self.base_url}")
            logger.info(f"⚙️ Cấu hình: max_articles={self.max_articles}, min_threshold={self.min_articles_threshold}, max_clicks={self.max_load_more_clicks}")

            result = await crawler.arun(url=self.base_url, config=config)
            
            logger.info(f"📋 JavaScript execution result: {result.js_execution_result}")

            # Parse HTML để lấy links
            soup = BeautifulSoup(result.html, 'html.parser')
            all_links = set()

            # Tìm tất cả links theo cách đã được test
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if (
                    "/the-batch/" in href
                    and not any(x in href for x in ["/tag/", "/category/", "/author/","/about", "/page/", "#", "mailto:", "tel:"])
                    and href.strip() != "/the-batch/"
                    and not href.rstrip("/").endswith("/the-batch")
                ):
                    full_url = urljoin("https://www.deeplearning.ai", href)
                    all_links.add(full_url)

            # Sắp xếp và log kết quả
            links = sorted(all_links)
            logger.info(f"🎯 Tổng cộng tìm thấy {len(links)} link bài viết unique")

            # Log một vài URL đầu tiên để kiểm tra
            if links:
                logger.info("🔍 Một vài URL đầu tiên:")
                for i, link in enumerate(links[:5]):
                    logger.info(f"  {i+1}. {link}")

            # Trả về số lượng theo max_articles
            final_links = links[:self.max_articles] if self.max_articles else links
            logger.info(f"📊 Sẽ crawl {len(final_links)} bài viết")

            return final_links

    async def crawl_article(self, url):
        """Crawl một bài viết cụ thể với cải thiện"""
        try:
            config = CrawlerRunConfig(
                # headers={
                #     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                # },
                page_timeout=30000
            )

            async with AsyncWebCrawler(
                headless=True,
                verbose=False
            ) as crawler:
                
                result = await crawler.arun(url=url, config=config)
                soup = BeautifulSoup(result.html, 'html.parser')

                def get_text(selectors, default=""):
                    """Thử nhiều selector để tìm text"""
                    if isinstance(selectors, str):
                        selectors = [selectors]

                    for selector in selectors:
                        element = soup.select_one(selector)
                        if element:
                            text = element.get_text(strip=True)
                            if text:
                                return text
                    return default

                # Cải thiện cách lấy title
                    # Cải thiện cách lấy title và subtitle riêng biệt
                title = ""
                subtitle = ""

                h1_element = soup.select_one('h1')
                if h1_element:
                    # Lấy subtitle từ span bên trong h1
                    span_element = h1_element.find('span')
                    if span_element:
                        subtitle = span_element.get_text(strip=True)
                        # Xóa span để lấy title chính
                        span_element.decompose()
                        title = h1_element.get_text(strip=True)
                    else:
                        # Nếu không có span, fallback về cách cũ
                        full_title = h1_element.get_text(strip=True)
                        
                        # Tách title đơn giản: lấy từ sau "reveals" trở đi
                        if "reveals" in full_title.lower():
                            parts = full_title.split("reveals", 1)
                            if len(parts) == 2:
                                title = ("reveals" + parts[1]).strip()
                            else:
                                title = full_title
                        else:
                            title = full_title

                # Nếu vẫn không có title, thử các selector khác
                if not title:
                    title = get_text([
                        'h1.post-title',
                        'h1[class*="title"]',
                        '.entry-title',
                        '.title',
                        '[class*="headline"]'
                    ], "Không tìm thấy tiêu đề")

                # Làm sạch title và subtitle
                title = re.sub(r'\s+', ' ', title).strip()
                subtitle = re.sub(r'\s+', ' ', subtitle).strip()
                print(f"Title: {title}")
                print(f"Subtitle: {subtitle}")
                
                # Cải thiện cách lấy author
                author = get_text([
                    '.author-name',
                    '.byline .author',
                    '[class*="author"]',
                    '.post-author',
                    '.entry-author'
                ], "Không có thông tin tác giả")

                # Cải thiện cách lấy publish date
                publish_date = None

                # Thử các meta tag
                for meta_attr in ['article:published_time', 'datePublished', 'publishdate']:
                    meta_date = soup.select_one(f'meta[property="{meta_attr}"], meta[name="{meta_attr}"]')
                    if meta_date:
                        publish_date = meta_date.get('content')
                        break

                if not publish_date:
                    # Thử tìm trong time tag
                    time_elem = soup.select_one('time[datetime]')
                    if time_elem:
                        publish_date = time_elem.get('datetime')

                if not publish_date:
                    # Thử các class thường dùng cho date
                    publish_date = get_text([
                        '.publish-date',
                        '.post-date',
                        '.entry-date',
                        '[class*="date"]',
                        '.meta-date'
                    ])

                # Cải thiện cách lấy description
                description = ""

                # Thử meta description
                meta_desc = soup.select_one('meta[name="description"], meta[property="og:description"]')
                if meta_desc:
                    description = meta_desc.get('content', '').strip()

                if not description:
                    description = get_text([
                        '.post-excerpt',
                        '.entry-summary',
                        '.excerpt',
                        '[class*="summary"]',
                        '.lead'
                    ])

                # Lấy main image
                main_image = None

                # Thử og:image
                meta_image = soup.select_one('meta[property="og:image"]')
                if meta_image:
                    main_image = meta_image.get('content')

                if not main_image:
                    # Thử featured image
                    img_elem = soup.select_one('.featured-image img, .post-image img, .entry-image img, img')
                    if img_elem:
                        main_image = img_elem.get('src') or img_elem.get('data-src')

                if main_image and main_image.startswith('/'):
                    main_image = urljoin("https://www.deeplearning.ai", main_image)

                # Cải thiện cách lấy content
                content = "Không tìm thấy nội dung chi tiết"

                # Thử các selector khác nhau cho content
                content_selectors = [
                    '.post-content',
                    '.entry-content',
                    '.article-content',
                    '[class*="content"]',
                    '.post-body',
                    'article .content',
                    'main article'
                ]

                for selector in content_selectors:
                    content_div = soup.select_one(selector)
                    if content_div:
                        # Loại bỏ các element không cần thiết
                        for unwanted in content_div.select('.ad, .advertisement, .social, .share, script, style, .related, .comments'):
                            unwanted.decompose()

                        # Lấy text từ paragraphs
                        paragraphs = content_div.select('p')
                        if paragraphs:
                            content_parts = []
                            for p in paragraphs:
                                p_text = p.get_text(strip=True)
                                if p_text and len(p_text) > 20:  # Chỉ lấy đoạn có ý nghĩa
                                    content_parts.append(p_text)

                            if content_parts:
                                content = '\n\n'.join(content_parts)
                                break
                        else:
                            # Nếu không có p tag, lấy toàn bộ text
                            content_text = content_div.get_text(separator='\n\n', strip=True)
                            if content_text and len(content_text) > 100:
                                content = content_text
                                break

                # Parse publish date
                if publish_date:
                    try:
                        if isinstance(publish_date, str):
                            publish_date = parser.parse(publish_date).replace(tzinfo=None)
                    except:
                        logger.warning(f"Không thể parse ngày tháng: {publish_date}")
                        publish_date = None

                # Tạo unique ID từ URL
                parsed_url = urlparse(url)
                article_id = parsed_url.path.split('/')[-1] or parsed_url.path.split('/')[-2]
                if not article_id:
                    article_id = str(hash(url))

                combined_text = f"{title.strip()}\n\n{content.strip()}"
                summary = self.summarizer.create_bullet_summary(combined_text) if combined_text else "Không có nội dung để tóm tắt"

                return {
                    '_id': article_id,
                    'title': title,
                    'author': author,
                    'publish_date': publish_date,
                    'description': description,
                    'main_image': main_image,
                    'content': content,
                    'url': url,
                    'summary': summary,
                    'category': self.category_name,
                    'crawled_at': datetime.now(pytz.timezone("Asia/Ho_Chi_Minh")).isoformat(),
                    'source': 'deeplearning.ai',
                    "summary": summary

                }

        except Exception as e:
            logger.error(f"Lỗi khi crawl {url}: {str(e)}")
            return None

    def filter_existing_urls(self, urls):
        """Lọc bỏ các URL đã tồn tại trong database"""
        if self.db is None:
            logger.warning("Không thể kết nối tới MongoDB để lọc URLs")
            return urls

        collection = self.db[self.category_name]
        existing_urls = set()

        try:
            existing_docs = collection.find({}, {"url": 1})
            existing_urls = {doc["url"] for doc in existing_docs}
        except Exception as e:
            logger.error(f"Lỗi khi truy vấn existing URLs: {str(e)}")
            return urls

        filtered_urls = [url for url in urls if url not in existing_urls]
        logger.info(f"Đã lọc: {len(urls)} URLs ban đầu -> {len(filtered_urls)} URLs mới")
        return filtered_urls

    async def crawl_all_articles(self):
        """Crawl tất cả bài viết"""
        start_time = time.time()

        logger.info("🚀 Đang bắt đầu quá trình crawl với Load More...")
        article_links = await self.get_article_links_with_load_more()

        if not article_links:
            logger.warning("❌ Không tìm thấy bài viết nào!")
            return

        # Lọc các URL đã tồn tại
        filtered_links = self.filter_existing_urls(article_links)

        if not filtered_links:
            logger.info(f"ℹ️ Không có bài viết mới nào trong danh mục {self.category_name} cần crawl.")
            return

        logger.info(f"📝 Đang crawl {len(filtered_links)} bài viết mới...")

        # Crawl từng bài viết với concurrency control
        semaphore = asyncio.Semaphore(3)  # Giữ 3 để ổn định

        async def crawl_single_article(url, index):
            async with semaphore:
                logger.info(f"[{index}/{len(filtered_links)}] 🔄 Đang crawl: {url}")
                article_data = await self.crawl_article(url)
                if article_data:
                    self.articles.append(article_data)
                    logger.info(f"    ✅ {article_data['title'][:60]}...")
                else:
                    logger.warning(f"    ❌ Không thể crawl: {url}")

                # Delay giữa các request
                await asyncio.sleep(1)
                return article_data

        # Chạy crawl parallel
        tasks = [crawl_single_article(url, i+1) for i, url in enumerate(filtered_links)]
        await asyncio.gather(*tasks, return_exceptions=True)

        elapsed = time.time() - start_time
        logger.info(f"⏱️ Tổng thời gian crawl: {elapsed:.2f} giây")
        logger.info(f"📊 Thành công crawl: {len(self.articles)}/{len(filtered_links)} bài viết")

    def save_to_mongodb(self):
        """Lưu các bài viết vào MongoDB"""
        try:
            if self.db is None:
                self._connect_mongodb()
                if self.db is None:
                    logger.error("Không thể kết nối tới MongoDB để lưu dữ liệu")
                    return False

            collection = self.db[self.category_name]

            if self.articles:
                saved_count = 0
                for article in self.articles:
                    try:
                        result = collection.replace_one(
                            {"_id": article["_id"]},
                            article,
                            upsert=True
                        )
                        if result.upserted_id or result.modified_count > 0:
                            saved_count += 1
                    except Exception as e:
                        logger.error(f"Lỗi khi lưu bài viết {article.get('title', 'N/A')}: {str(e)}")

                logger.info(f"💾 Đã lưu thành công {saved_count}/{len(self.articles)} bài viết vào collection '{self.category_name}'")
            else:
                logger.info(f"ℹ️ Không có bài viết để lưu vào collection '{self.category_name}'")

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
                    json.dump(self.articles, f, ensure_ascii=False, indent=2, default=str)
                logger.info(f"📄 Đã lưu {len(self.articles)} bài viết vào {file_path}")
            except Exception as e:
                logger.error(f"Không thể lưu file: {str(e)}")

        return mongo_result
