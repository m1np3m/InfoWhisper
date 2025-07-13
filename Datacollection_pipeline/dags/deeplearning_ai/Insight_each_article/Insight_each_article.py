import pandas as pd
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime
from dateutil.relativedelta import relativedelta
from nltk.tokenize import word_tokenize
import nltk
from langchain_google_genai import ChatGoogleGenerativeAI

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler


load_dotenv() 
lf = Langfuse()        # hoặc lf = get_client()
handler = CallbackHandler() 
# nltk.download("punkt")
import tiktoken
class InsightSummarizer:
    def __init__(self, mongo_uri, source_db_name, collections, insight_db_name="deeplearning_ai_insight"):
        self.client = MongoClient(mongo_uri)
        self.source_db = self.client[source_db_name]  # Database chứa dữ liệu gốc
        self.insight_db = self.client[insight_db_name]  # Database chứa insights
        self.collections = collections

    def count_tokens(self, text):
        if not isinstance(text, str):
            return 0
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))

    def filter_summaries_last_k_months(self, k=1, reference_date=None):
        if reference_date is None:
            reference_date = datetime.utcnow()

        start_date = reference_date - relativedelta(months=k)
        all_data = []

        for col in self.collections:
            collection = self.source_db[col]  # Lấy từ source database
            query = {
                "publish_date": {
                    "$gte": start_date,
                    "$lte": reference_date
                }
            }
            projection = {"summary": 1, "title": 1, "publish_date": 1, "_id": 0}
            results = list(collection.find(query, projection))

            for item in results:
                item["collection"] = col
                item["tokens"] = self.count_tokens(item.get("summary", ""))
                all_data.append(item)

        df = pd.DataFrame(all_data)
        return df.sort_values(by="publish_date")

    def generate_llm_prompt(self, df, k=1, max_tokens=100_000):
        """
        Ghép các summary thành một prompt dài để gửi vào LLM
        """
        if df.empty:
            return "Không có dữ liệu summary trong khoảng thời gian đã chọn."
    
        content_blocks = []
        token_total = 0
    
        for _, row in df.iterrows():
            block = f"- ({row['collection']}, {row['publish_date'].date()}): {row['summary']}"
            block_tokens = row["tokens"]
    
            if token_total + block_tokens > max_tokens:
                break
    
            content_blocks.append(block)
            token_total += block_tokens
    
        prompt = (
            f"Bạn là một trợ lý AI đang theo dõi các bài viết trong lĩnh vực này. "
            f"Dưới đây là các đoạn tóm tắt từ các bài viết được xuất bản trong {k} tháng gần đây:\n\n"
            + "\n".join(content_blocks)
            + "\n\nDựa vào các thông tin trên, hãy viết một bản tóm tắt tự nhiên, súc tích và có ngữ điệu giống như một phóng viên hoặc biên tập viên chuyên mục công nghệ đang tổng kết các sự kiện nổi bật. "
            "Chỉ tập trung vào những điểm đáng chú ý, tránh liệt kê dài dòng. "
            "Hãy kết thúc bằng 1–2 câu tổng kết cô đọng xu hướng chính."
        )

        return prompt

    def summarize_last_k_months(self, k=1, max_tokens=100_000, return_df=False):
        df = self.filter_summaries_last_k_months(k)
        prompt = self.generate_llm_prompt(df, k=k, max_tokens=max_tokens)
        return (prompt, df) if return_df else prompt

    def call_gemini_summary(self, prompt, model="gemini-2.0-flash", temperature=0.4):
        genai = ChatGoogleGenerativeAI(
            model=model,
            google_api_key="AIzaSyBKX9Qe8lC8Iqma3LDia_NM0LFCaz7GBt0",
            temperature=temperature,
            callbacks      = [handler],
            name = "monthly summary insight"
        )

        response = genai.invoke(prompt)
        return response.content

    def generate_prompt_for_collection(self, df, k=1, max_tokens=100_000):
        if df.empty:
            return None

        content_blocks = []
        token_total = 0

        for _, row in df.iterrows():
            block = f"- ({row['publish_date'].date()}): {row['summary']}"
            block_tokens = row["tokens"]

            if token_total + block_tokens > max_tokens:
                break

            content_blocks.append(block)
            token_total += block_tokens

        prompt = (
            f"Dưới đây là các đoạn tóm tắt từ các bài viết được xuất bản trong {k} tháng gần đây:\n\n"
            + "\n".join(content_blocks)
            + "\n\nHãy viết một đoạn tổng kết ngắn gọn, khách quan và rõ ràng. "
            "Tập trung vào các diễn biến nổi bật, xu hướng chính và bất kỳ thay đổi đáng chú ý nào. "
            "Không cần mở đầu hoa mỹ hay trình bày theo kiểu phóng viên, chỉ cần nội dung insight rõ và đầy đủ, cô đọng trong một đoạn duy nhất."
        )

        return prompt
    
    def generate_markmap_from_text(self, text, model="gemini-2.0-flash-lite", temperature=0.3):
        prompt = f"""
    Tôi sẽ đưa bạn một đoạn văn bản tổng hợp tin tức công nghệ. Nhiệm vụ của bạn là chuyển nội dung này sang dạng **Markdown mindmap** để có thể sử dụng với thư viện [Markmap](https://markmap.js.org/).

    ❗ Trả về chỉ phần nội dung markdown hợp lệ (KHÔNG bao gồm dòng ```markdown hoặc ```), KHÔNG thêm giải thích.

    Đây là nội dung:

    {text}
    """
        genai = ChatGoogleGenerativeAI(
            model=model,
            google_api_key="AIzaSyBKX9Qe8lC8Iqma3LDia_NM0LFCaz7GBt0",
            temperature=temperature
        )

        response = genai.invoke(prompt)
        content = response.content.strip()

        if content.startswith("```markdown"):
            content = content.removeprefix("```markdown").strip()
        if content.startswith("```"):
            content = content.removeprefix("```").strip()
        if content.endswith("```"):
            content = content.removesuffix("```").strip()

        # ✅ Thêm frontmatter YAML cho markmap
        prefix = "---\nmarkmap:\n  initialExpandLevel: 999\n  colorFreezeLevel: 2\n---\n\n"
        return prefix + content



    def summarize_each_collection(self, k=1, max_tokens=100_000, return_prompt_only=False):
        from collections import defaultdict
        collection_insights = {}

        reference_date = datetime.utcnow()
        start_date = reference_date - relativedelta(months=k)

        for col in self.collections:
            collection = self.source_db[col]  # Lấy từ source database
            query = {
                "publish_date": {"$gte": start_date, "$lte": reference_date}
            }
            projection = {"summary": 1, "title": 1, "publish_date": 1, "_id": 0}
            results = list(collection.find(query, projection))

            if not results:
                continue

            for item in results:
                item["tokens"] = self.count_tokens(item.get("summary", ""))

            df = pd.DataFrame(results).sort_values(by="publish_date")
            prompt = self.generate_prompt_for_collection(df, k=k, max_tokens=max_tokens)

            if not prompt:
                continue

            if return_prompt_only:
                collection_insights[col] = prompt
            else:
                response = self.call_gemini_summary(prompt)
                markmap_md = self.generate_markmap_from_text(response)

                collection_insights[col] = {
                    "insight": response,
                    "markmap": markmap_md
                }


        return collection_insights

    def generate_month_year_string(self, reference_date=None):
        """Tạo string month-year format YYYY-MM"""
        if reference_date is None:
            reference_date = datetime.utcnow()
        return reference_date.strftime("%Y-%m")

    def save_insights_to_db(self, k=1, max_tokens=1000, reference_date=None):
        """
        Sinh insight cho từng collection và lưu vào database riêng biệt
        Mỗi collection sẽ có collection name giống với tên collection gốc
        """
        if reference_date is None:
            reference_date = datetime.utcnow()
        
        month_year = self.generate_month_year_string(reference_date)
        insights = self.summarize_each_collection(k=k, max_tokens=max_tokens, return_prompt_only=False)
        
        saved_count = 0
        
        for collection_name, insight_content in insights.items():
            # Sử dụng tên collection gốc
            insight_collection = self.insight_db[collection_name]
            
            # Tạo document ID theo định dạng month_year
            document_id = month_year
            
            insight_doc = {
                "_id": document_id,
                "source_collection": collection_name,
                "month": month_year,
                "insight": insight_content["insight"],
                "markmap": insight_content["markmap"],
                "generated_at": datetime.utcnow(),
                "period_months": k,
                "max_tokens_used": max_tokens
            }
            
            try:
                # Sử dụng upsert để tránh lỗi duplicate key
                insight_collection.update_one(
                    {"_id": document_id},
                    {"$set": insight_doc},
                    upsert=True
                )
                saved_count += 1
                print(f"✅ Đã lưu insight cho collection '{collection_name}' (ID: {document_id})")
                
            except Exception as e:
                print(f"❌ Lỗi khi lưu insight cho collection '{collection_name}': {e}")
        
        print(f"\n📊 Tổng kết: Đã lưu thành công {saved_count}/{len(insights)} insights vào database '{self.insight_db.name}'")
        return saved_count

    def get_insights_by_month(self, month_year=None, source_collection=None):
        """
        Lấy insights theo tháng, có thể lọc theo source collection cụ thể
        """
        if month_year is None:
            month_year = self.generate_month_year_string()
        
        results = {}
        collections_to_check = [source_collection] if source_collection else self.collections
        
        for col in collections_to_check:
            insight_collection = self.insight_db[col]
            
            try:
                doc = insight_collection.find_one({"_id": month_year})
                if doc:
                    results[col] = doc
            except Exception as e:
                print(f"⚠️ Lỗi khi lấy insight từ collection '{col}': {e}")
        
        return results

    def get_insights_by_collection(self, collection_name, limit=5):
        """
        Lấy insights theo collection (mới nhất trước)
        """
        insight_collection = self.insight_db[collection_name]
        
        try:
            results = list(insight_collection.find().sort("generated_at", -1).limit(limit))
            return results
        except Exception as e:
            print(f"⚠️ Lỗi khi lấy insights từ collection '{collection_name}': {e}")
            return []

    def delete_insights_by_month(self, month_year, source_collection=None):
        """
        Xóa insights của một tháng cụ thể, có thể chỉ định collection cụ thể
        """
        deleted_total = 0
        collections_to_delete = [source_collection] if source_collection else self.collections
        
        for col in collections_to_delete:
            insight_collection = self.insight_db[col]
            
            try:
                result = insight_collection.delete_one({"_id": month_year})
                if result.deleted_count > 0:
                    deleted_total += result.deleted_count
                    print(f"🗑️ Đã xóa insight tháng {month_year} từ collection '{col}'")
            except Exception as e:
                print(f"⚠️ Lỗi khi xóa insight từ collection '{col}': {e}")
        
        print(f"🗑️ Tổng cộng đã xóa {deleted_total} insights của tháng {month_year}")
        return deleted_total

    def list_all_insight_collections(self):
        """
        Liệt kê tất cả collections insight có trong database
        """
        collections = self.insight_db.list_collection_names()
        # Lọc chỉ những collection nằm trong danh sách collections định nghĩa
        insight_collections = [col for col in collections if col in self.collections]
        return insight_collections

    def get_database_stats(self):
        """
        Thống kê thông tin về insight database
        """
        stats = {
            "database_name": self.insight_db.name,
            "collections": {},
            "total_insights": 0
        }
        
        insight_collections = self.list_all_insight_collections()
        
        for col_name in insight_collections:
            collection = self.insight_db[col_name]
            count = collection.count_documents({})
            stats["collections"][col_name] = count
            stats["total_insights"] += count
        
        return stats
