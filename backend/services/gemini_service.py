import os
import re
import json
from google import genai
from google.genai import types

class GeminiService:
    """Gemini 2.0 API を用いた画像・マルチモーダル解析を担当するサービス oily クラス"""

    def __init__(self):
        """環境変数からAPI KEYを厳格に取得し、GenAI クライアントを初期化します"""
        self.api_key = os.environ['GEMINI_API_KEY']
        self.client = genai.Client(api_key=self.api_key)

    def analyze_receipt(self, image_bytes):
        """
        レシートの画像バイナリをGeminiに送信し、指定のフォーマットに沿ったデータをJSON抽出します。
        
        Args:
            image_bytes (bytes): 解析対象の画像バイナリ
        Returns:
            dict: パース済みのレシート情報（shop_name, pay_date, pay_time, total_pay）
        """
        # 解析精度を高め、かつ出力をJSONに限定するための構造化プロンプト
        prompt = (
            "添付したレシートの写真から店名、日付(YYYY-MM-DD)、時間(HH:mm)、合計金額を抽出してJSON形式でのみ答えてください。"
            "キー名は shop_name, pay_date, pay_time, total_pay としてください。"
        )

        # モデルには軽量・高速かつ無料枠が安定している 'models/gemini-flash-latest' を指定
        response = self.client.models.generate_content(
            model='models/gemini-flash-latest',
            contents=[
                prompt,
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            ]
        )

        # Geminiがたまに出力に付与してくるマークダウン表記（```json ... ```）を正規表現でトリミング
        clean_json = re.sub(r'^```json\s*|\s*```$', '', response.text.strip(), flags=re.MULTILINE)
        
        # 文字列をPythonの辞書（dict）型にパースして返却
        return json.loads(clean_json)
