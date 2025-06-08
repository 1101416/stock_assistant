from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

import os
from dotenv import load_dotenv

from linebot_handler import handle_line_message

# 載入 .env 檔案（如需）
load_dotenv()

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# 根目錄測試用
@app.route("/")
def home():
    return "Stock LINE Bot is running!"

# LINE Webhook 路由
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")

    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

# 處理文字訊息事件
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    reply_token = event.reply_token
    user_id = event.source.user_id

    # 呼叫自訂邏輯處理器
    handle_line_message(user_id, user_message, reply_token, line_bot_api)


from linebot_handler import init_db

# 啟動前先初始化資料庫
init_db()

from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime
import sqlite3
from stock_info import get_stock_info
from linebot import LineBotApi
from linebot.models import TextSendMessage

# 替換為你的 LINE Channel Access Token
LINE_CHANNEL_ACCESS_TOKEN = "你的_LINE_CHANNEL_ACCESS_TOKEN"
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)

# SQLite 資料庫路徑
DB_PATH = "./users.db"

# 取得所有使用者 ID
def get_all_user_ids():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT user_id FROM user_stocks")
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

# 定時工作：推播股票資訊
def job_send_stock_report():
    print(f"[{datetime.now()}] ⏰ 執行定時推播任務...")

    user_ids = get_all_user_ids()
    for user_id in user_ids:
        from main import get_user_stocks  # 避免循環匯入，放在函數內
        stocks = get_user_stocks(user_id)
        if not stocks:
            continue

        messages = []
        for stock_id in stocks:
            info, error = get_stock_info(stock_id)
            text = info if info else f"{stock_id} 查詢失敗：{error}"
            messages.append(TextSendMessage(text=text))

        try:
            line_bot_api.push_message(user_id, messages[:5])  # 最多 5 則訊息
            print(f"✅ 成功推播給 {user_id}")
        except Exception as e:
            print(f"❌ 推播失敗 {user_id}：{e}")

# 啟動 APScheduler
if __name__ == "__main__":
    print("📆 啟動定時排程服務...")
    scheduler = BlockingScheduler()
    scheduler.add_job(job_send_stock_report, 'cron', day_of_week='mon-fri', hour=11, minute=0)
    scheduler.add_job(job_send_stock_report, 'cron', day_of_week='mon-fri', hour=13, minute=0)
    scheduler.start()
