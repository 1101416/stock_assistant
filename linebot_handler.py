import sqlite3
import os
from linebot.models import TextSendMessage
from news_scraper import fetch_stock_news
from linebot.models import TextSendMessage
from stock_info import get_stock_info
DB_PATH = "./line_gemini.db"
from gemini_helper import ask_gemini

from linebot.models import QuickReply, QuickReplyButton, MessageAction

def get_quick_reply():
    return QuickReply(items=[
        QuickReplyButton(action=MessageAction(label="查詢股票", text="請輸入：查詢 股票代號（如：查詢 2330）")),
        QuickReplyButton(action=MessageAction(label="新增 2330", text="新增 2330")),
        QuickReplyButton(action=MessageAction(label="刪除 2330", text="刪除 2330")),
        QuickReplyButton(action=MessageAction(label="清單", text="清單")),
        QuickReplyButton(action=MessageAction(label="查詢清單", text="查詢清單")),
        QuickReplyButton(action=MessageAction(label="新聞", text="新聞")),
    ])

def get_help_message():
    return (
        "🤖 指令提示：\n"
        "📈 查股價：查詢 2330(股票代號)\n"
        "🧾 關注股票：新增 2330(股票代號)\n"
        "❌ 移除關注：刪除 2330(股票代號)\n"
        "📋 查看關注清單：清單\n"
        "🔎 批次查詢清單股價：查詢清單(須先建立清單)\n"
        "📰 查詢新聞：新聞(須先建立清單)\n"
        "🤖 問 AI：直接輸入問題，例如『台積電是做什麼的？』"
    )

# 初始化資料庫（第一次使用可呼叫）
def init_db():
    is_new_db = not os.path.exists(DB_PATH)
    print(f"📦 資料庫路徑：{DB_PATH}（{'新建' if is_new_db else '已存在'}）")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    try:
        c.execute('''
            CREATE TABLE IF NOT EXISTS user_stocks (
                user_id TEXT NOT NULL,
                stock_id TEXT NOT NULL,
                PRIMARY KEY (user_id, stock_id)
            )
        ''')
        conn.commit()
        print("✅ 資料表 user_stocks 確認建立完成")
    except Exception as e:
        print(f"❌ 建立資料表失敗：{e}")
    finally:
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
        reply_text += get_help_message()
        line_bot_api.reply_message(reply_token, TextSendMessage(
            text=reply_text,
            quick_reply=get_quick_reply()
        ))

    elif message.startswith("刪除"):
        stock_id = message[2:].strip()
        success, reply_text = remove_stock(user_id, stock_id)
        reply_text += get_help_message()
        line_bot_api.reply_message(reply_token, TextSendMessage(
            text=reply_text,
            quick_reply=get_quick_reply()
        ))

    elif message == "清單":
        stocks = get_user_stocks(user_id)
        if not stocks:
            reply_text = "你還沒有關注任何股票。"
        else:
            reply_text = "你關注的股票有：\n" + "\n".join(stocks)
        reply_text += get_help_message()
        line_bot_api.reply_message(reply_token, TextSendMessage(
            text=reply_text,
            quick_reply=get_quick_reply()
        ))

    elif message == "查詢清單":
        stocks = get_user_stocks(user_id)
        if not stocks:
            reply_text = "你尚未關注任何股票。" + get_help_message()
            line_bot_api.reply_message(reply_token, TextSendMessage(
                text=reply_text,
                quick_reply=get_quick_reply()
            ))
            return
        
        reply_texts = []
        for stock_id in stocks:
            info, error = get_stock_info(stock_id)
            reply_texts.append(info if info else f"{stock_id} 查詢失敗：{error}")
        
        reply_texts.append(get_help_message())
        messages = [TextSendMessage(text=text, quick_reply=get_quick_reply()) for text in reply_texts[:5]]
        line_bot_api.reply_message(reply_token, messages)

    elif message == "新聞":
        stocks = get_user_stocks(user_id)
        if not stocks:
            reply_text = "你還沒有關注任何股票，請先使用「新增 股票代號」加入。"
            reply_text += get_help_message()
            line_bot_api.reply_message(reply_token, TextSendMessage(
                text=reply_text,
                quick_reply=get_quick_reply()
            ))
        else:
            result_lines = ["📰 你的股票新聞推薦："]
            for stock_id in stocks:
                title, link = fetch_stock_news(stock_id)
                if title and link:
                    result_lines.append(f"{title}\n{link}")
                else:
                    result_lines.append(f"{stock_id}：找不到相關新聞。")
            result_lines.append(get_help_message())
            reply_text = "\n\n".join(result_lines)
            line_bot_api.reply_message(reply_token, TextSendMessage(
                text=reply_text,
                quick_reply=get_quick_reply()
            ))

    elif message.startswith("查詢 ") and len(message.split()) == 2:
        stock_id = message.split()[1]
        if stock_id.isdigit() and 4 <= len(stock_id) <= 6:
            info, error = get_stock_info(stock_id)
            reply_text = info if info else error
        else:
            reply_text = "請輸入正確的 4~6 碼股票代號，如：查詢 2330"
        reply_text += get_help_message()
        line_bot_api.reply_message(reply_token, TextSendMessage(
            text=reply_text,
            quick_reply=get_quick_reply()
        ))

    else:
        # Gemini 問答處理
        reply_text = ask_gemini(message)
        reply_text += get_help_message()
        line_bot_api.reply_message(reply_token, TextSendMessage(
            text=reply_text,
            quick_reply=get_quick_reply()
        ))
