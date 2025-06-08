from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
from dotenv import load_dotenv
from linebot_handler import handle_line_message, init_db

# 載入 .env 檔案
load_dotenv()

# 初始化 Flask App
app = Flask(__name__)

# 初始化 LINE Bot API
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 根目錄測試用
@app.route("/")
def home():
    return "✅ Stock LINE Bot is running on Render!"

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

# 初始化資料庫
init_db()

# 使用 waitress 部署到 Render，綁定 PORT（必要）
if __name__ == "__main__":
    from waitress import serve
    port = int(os.environ.get("PORT", 10000))  # Render 預設傳入 PORT 變數
    print(f"🚀 啟動 Flask Web Server on port {port} ...")
    serve(app, host="0.0.0.0", port=port)
