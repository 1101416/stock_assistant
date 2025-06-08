import requests
from bs4 import BeautifulSoup

def fetch_stock_news(stock_id):
    url = f"https://www.cnyes.com/twstock/{stock_id}"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return None, "查詢失敗，請確認股票代號是否正確。"

        soup = BeautifulSoup(response.text, "html.parser")

        link_tag = soup.find("a", class_="jsx-2831776980 container shadow")
        link = link_tag["href"] if link_tag else "N/A"
        
        
        link_response = requests.get(link, headers=headers)
        if link_response.status_code != 200:
            return None, "title查詢失敗。"

        link_soup = BeautifulSoup(link_response.text, "html.parser")
        
        title_tag = link_soup.find("section", class_="t1el8oye")
        title = title_tag.text.strip() if title_tag else "N/A"


        result = f"""📈 股票代號：{stock_id}
相關新聞標題：{title}"""
        link=f"""網址：{link}"""
        return result, link

    except Exception as e:
        return None, f"解析股票資料失敗：{str(e)}"
    




