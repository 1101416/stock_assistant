from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime
import sqlite3
from stock_info import get_stock_info
from linebot import LineBotApi
from linebot.models import TextSendMessage
from stock_manager import get_user_stocks
import os
from dotenv import load_dotenv

load_dotenv()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)

DB_PATH = "./users.db"

def get_all_user_ids():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT user_id FROM user_stocks")
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

def job_send_stock_report():
    print(f"[{datetime.now()}] ⏰ 執行定時推播任務...")
    user_ids = get_all_user_ids()

    for user_id in user_ids:
        stocks = get_user_stocks(user_id)
        if not stocks:
            continue
        messages = []
        for stock_id in stocks:
            info, error = get_stock_info(stock_id)
            text = info if info else f"{stock_id} 查詢失敗：{error}"
            messages.append(TextSendMessage(text=text))

        try:
            line_bot_api.push_message(user_id, messages[:5])
            print(f"✅ 成功推播給 {user_id}")
        except Exception as e:
            print(f"❌ 推播失敗 {user_id}：{e}")

if __name__ == "__main__":
    print("📆 啟動排程服務...")
    scheduler = BlockingScheduler()
    scheduler.add_job(job_send_stock_report, 'cron', day_of_week='mon-fri', hour=11, minute=0)
    scheduler.add_job(job_send_stock_report, 'cron', day_of_week='mon-fri', hour=13, minute=0)
    scheduler.start()
