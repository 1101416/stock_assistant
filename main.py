from flask import Flask, request, abort
from dotenv import load_dotenv
from linebot.v3.webhook import WebhookHandler
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    PushMessageRequest, TextMessage
)
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import os
import sqlite3
from datetime import datetime

# 自訂模組
from linebot_handler import handle_line_message, init_db, DB_PATH
from stock_info import get_stock_info
from stock_manager import get_user_stocks, init_stock_table

# 載入環境變數
load_dotenv()

# 初始化 Flask 與 LINE Messaging API
app = Flask(__name__)
configuration = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# 根目錄測試
@app.route("/")
def home():
    return "✅ Stock LINE Bot is running on Render!"

# LINE Webhook callback
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

# LINE 訊息處理器
@handler.add(MessageEvent)
def handle_text_message(event):
    if not isinstance(event.message, TextMessageContent):
        return
    user_message = event.message.text
    reply_token = event.reply_token
    user_id = event.source.user_id

    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)
        handle_line_message(user_id, user_message, reply_token, messaging_api)

# GitHub Actions 專用：定時推播 API
@app.route("/push_stock", methods=["POST"])
def push_stock_job():
    init_db()
    def get_all_user_ids():
        print(f"📥 push_stock 使用資料庫：{DB_PATH}")
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT DISTINCT user_id FROM user_stocks")
        rows = c.fetchall()
        conn.close()
        return [row[0] for row in rows]

    print(f"[{datetime.now()}] 🔔 GitHub Scheduler 推播啟動")
    user_ids = get_all_user_ids()

    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)
        for user_id in user_ids:
            stocks = get_user_stocks(user_id)
            if not stocks:
                continue
            messages = []
            for stock_id in stocks:
                info, error = get_stock_info(stock_id)
                text = info if info else f"{stock_id} 查詢失敗：{error}"
                messages.append(TextMessage(text=text))
            try:
                req = PushMessageRequest(to=user_id, messages=messages[:5])
                messaging_api.push_message(req)
                print(f"✅ 成功推播給 {user_id}")
            except Exception as e:
                print(f"❌ 推播失敗 {user_id}：{e}")

    return "✅ 推播完成", 200

# 主程式進入點
if __name__ == "__main__":
    print("🚀 Flask App 啟動中")
    init_db()
    init_stock_table()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
