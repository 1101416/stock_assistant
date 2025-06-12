import os
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-1.5-flash")

def ask_gemini(question):
    try:
        response = model.generate_content(question)
        return response.text
    except Exception as e:
        return f"⚠️ Gemini 回覆失敗：{str(e)}"
