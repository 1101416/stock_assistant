import sqlite3

DB_NAME = "line_gemini.db"

def init_stock_table():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_stocks (
                user_id TEXT,
                stock_id TEXT,
                PRIMARY KEY (user_id, stock_id)
            )
        """)
        conn.commit()

# 查詢使用者的股票
def get_user_stocks(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT stock_id FROM user_stocks WHERE user_id = ?", (user_id,))
        return [row[0] for row in c.fetchall()]

# 新增股票（每人最多 5 檔）
def add_stock(user_id, stock_id):
    stocks = get_user_stocks(user_id)
    if len(stocks) >= 5:
        return "⚠️ 你已經關注 5 檔股票，請先刪除一檔才能新增。"
    if stock_id in stocks:
        return f"⚠️ 你已經關注 {stock_id} 了。"
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO user_stocks (user_id, stock_id) VALUES (?, ?)", (user_id, stock_id))
        conn.commit()
        return f"✅ 成功新增 {stock_id} 至你的關注清單。"

# 刪除股票
def remove_stock(user_id, stock_id):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM user_stocks WHERE user_id = ? AND stock_id = ?", (user_id, stock_id))
        conn.commit()
        return f"✅ 已從關注清單中刪除 {stock_id}。"

# 處理文字指令
def handle_stock_command(user_id, msg):
    if msg.startswith("新增"):
        stock_id = msg.replace("新增", "").strip()
        return add_stock(user_id, stock_id)

    elif msg.startswith("刪除"):
        stock_id = msg.replace("刪除", "").strip()
        return remove_stock(user_id, stock_id)

    elif msg.startswith("查詢股票"):
        stocks = get_user_stocks(user_id)
        if not stocks:
            return "📭 你尚未關注任何股票。"
        else:
            return "📌 你目前關注的股票有：\n" + "\n".join(f"- {s}" for s in stocks)

    else:
        return "⚠️ 指令格式錯誤，請使用：\n新增 [股票代碼]、刪除 [股票代碼]、查詢股票"
