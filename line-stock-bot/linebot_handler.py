import sqlite3
from linebot.models import TextSendMessage
from news_scraper import fetch_stock_news
from linebot.models import TextSendMessage
from stock_info import get_stock_info
DB_PATH = "./users.db"
from gemini_helper import ask_gemini  # 新增這行

# 初始化資料庫（第一次使用可呼叫）
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_stocks (
            user_id TEXT,
            stock_id TEXT,
            PRIMARY KEY (user_id, stock_id)
        )
    """)
    conn.commit()
    conn.close()

# 查詢使用者關注清單
def get_user_stocks(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT stock_id FROM user_stocks WHERE user_id = ?", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

# 新增股票到關注清單
def add_stock(user_id, stock_id):
    stocks = get_user_stocks(user_id)
    if stock_id in stocks:
        return False, "你已經關注過這檔股票了。"
    if len(stocks) >= 5:
        return False, "最多只能關注5檔股票喔，請先刪除其他股票。"

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO user_stocks (user_id, stock_id) VALUES (?, ?)", (user_id, stock_id))
        conn.commit()
    except Exception as e:
        conn.close()
        return False, "新增失敗：" + str(e)
    conn.close()
    return True, f"成功新增關注股票：{stock_id}"

# 刪除股票關注
def remove_stock(user_id, stock_id):
    stocks = get_user_stocks(user_id)
    if stock_id not in stocks:
        return False, "你並未關注這檔股票。"

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM user_stocks WHERE user_id = ? AND stock_id = ?", (user_id, stock_id))
    conn.commit()
    conn.close()
    return True, f"成功刪除關注股票：{stock_id}"

# 處理使用者訊息邏輯
def handle_line_message(user_id, message, reply_token, line_bot_api):
    message = message.strip()

    if message.startswith("新增"):
        stock_id = message[2:].strip()
        success, reply_text = add_stock(user_id, stock_id)
        line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text))
    elif message.startswith("刪除"):
        stock_id = message[2:].strip()
        success, reply_text = remove_stock(user_id, stock_id)
        line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text))
    elif message == "清單":
        stocks = get_user_stocks(user_id)
        if not stocks:
            reply_text = "你還沒有關注任何股票。"
        else:
            reply_text = "你關注的股票有：\n" + "\n".join(stocks)
        line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text))
        
    elif message == "查詢清單":
        stocks = get_user_stocks(user_id)
        if not stocks:
            line_bot_api.reply_message(reply_token, TextSendMessage(text="你尚未關注任何股票。"))
            return
        
        reply_texts = []
        for stock_id in stocks:
            info, error = get_stock_info(stock_id)
            reply_texts.append(info if info else f"{stock_id} 查詢失敗：{error}")

        # LINE 最多一次只能回傳 5 則訊息（也就是 5 則 TextSendMessage）
        messages = [TextSendMessage(text=text) for text in reply_texts[:5]]
        line_bot_api.reply_message(reply_token, messages)

    elif message == "新聞":
        stocks = get_user_stocks(user_id)
        if not stocks:
            reply_text = "你還沒有關注任何股票，請先使用「新增 股票代號」加入。"
            line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text))
        else:
            result_lines = ["📰 你的股票新聞推薦："]
            for stock_id in stocks:
                title, link = fetch_stock_news(stock_id)
                if title and link:
                    result_lines.append(f"{title}\n{link}")
                else:
                    result_lines.append(f"{stock_id}：找不到相關新聞。")
            reply_text = "\n\n".join(result_lines)
            line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text))


    elif message.startswith("查詢 ") and len(message.split()) == 2:
        stock_id = message.split()[1]
        if stock_id.isdigit() and len(stock_id) >= 4 and len(stock_id) <= 6:
            info, error = get_stock_info(stock_id)
            reply_text = info if info else error
            line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text))
        else:
            line_bot_api.reply_message(reply_token, TextSendMessage(text="請輸入正確的 4~6 碼股票代號，如：查詢 2330"))
    else:
        # ⭐ 預設為 Gemini 問答處理
        reply_text = ask_gemini(message)
    line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text))
