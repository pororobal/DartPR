import sys
import os
import asyncio

# Add parent directory to path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.services.groq_llm import analyze_disclosure

async def test_connection():
    print(f"Current GROQ_API_KEY: {settings.groq_api_key}")
    print(f"Current GROQ_MODEL: {settings.groq_model}")
    
    if not settings.groq_api_key or "your_groq" in settings.groq_api_key:
        print("\n[ERROR] GROQ_API_KEY is not configured or is a placeholder in backend/.env!")
        print("Please replace 'your_groq_api_key_here' with a valid Groq API key.")
        return
        
    print("\nAttempting to analyze a sample disclosure...")
    ticker = "005930"
    company_name = "삼성전자"
    title = "특허권 취득 (지구상에서 가장 가벼운 배터리 소재 관련 특허)"
    raw_text = """
    1. 특허명칭: 고체 전해질 및 이를 포함하는 리튬이차전지
    2. 특허 주요 내용: 기존 배터리 대비 무게를 50% 줄이고 용량을 2배 늘린 신소재 고체 전해질 특허 취득.
    3. 적용 제품: 모바일 및 전기차용 리튬이온 배터리
    4. 특허 취득일: 2026-07-24
    """
    
    try:
        result = await analyze_disclosure(ticker, company_name, title, raw_text)
        print("\n[SUCCESS] Groq LLM API call completed successfully!")
        print(f"Summary: {result.llm_summary}")
        print("Key Metrics:")
        for metric in result.key_metrics:
            print(f" - {metric.label}: {metric.value} ({metric.status})")
    except Exception as e:
        print(f"\n[FAILED] Error during Groq LLM API call: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
