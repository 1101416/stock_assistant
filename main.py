from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

# 自訂模組
from linebot_handler import handle_line_message, init_db, DB_PATH
from stock_info import get_stock_info
from stock_manager import get_user_stocks

# 載入環境變數
load_dotenv()
init_db() 
# 初始化 Flask 與 LINE Bot API
app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# 📍 根目錄測試
@app.route("/")
def home():
    return "✅ Stock LINE Bot is running on Render!"

# 📍 LINE Webhook callback
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

# 📍 LINE 訊息處理器（文字訊息）
@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    user_message = event.message.text
    reply_token = event.reply_token
    user_id = event.source.user_id
    handle_line_message(user_id, user_message, reply_token, line_bot_api)

# 📍 GitHub Actions 專用：定時推播 API
@app.route("/push_stock", methods=["POST"])
def push_stock_job():
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
            line_bot_api.push_message(user_id, messages[:5])  # 最多推播 5 則
            print(f"✅ 成功推播給 {user_id}")
        except Exception as e:
            print(f"❌ 推播失敗 {user_id}：{e}")

    return "✅ 推播完成", 200

# 📍 主程式進入點（Render 啟動）
if __name__ == "__main__":
    init_db()  
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
