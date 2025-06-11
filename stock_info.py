import requests
from bs4 import BeautifulSoup

def get_stock_info(stock_id):
    url = f"https://www.cnyes.com/twstock/{stock_id}"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return None, "查詢失敗，請確認股票代號是否正確。"

        soup = BeautifulSoup(response.text, "html.parser")

        # 擷取股票名稱
        name_tag = soup.find("h2", class_="jsx-2312976322")
        name = name_tag.text.strip() if name_tag else "N/A"

        # 擷取現價
        price_tag = soup.find("div", class_="jsx-2312976322 price")
        price = price_tag.text.strip() if price_tag else "N/A"

        change_tag = soup.find("div", class_="jsx-2312976322 first-row")
        change = change_tag.text.strip() if change_tag else "N/A"  # 漲跌
        
        values = soup.find_all("span", class_="jsx-4238438383 value")
        volume = values[2].text.strip() if values else "N/A"    # 成交量
        avg_price = values[6].text.strip() if values else "N/A" # 均價
        high_price = values[1].text.strip() if values else "N/A" # 最高
        low_price = values[4].text.strip() if values else "N/A" # 最低


        result = f"""📈 股票代號：{stock_id}
股票名稱：{name}
現價：{price}
漲跌：{change}
成交量：{volume}
均價：{avg_price}
最高：{high_price}
最低：{low_price}"""
        return result, None

    except Exception as e:
        return None, f"解析股票資料失敗：{str(e)}"
