import os
from flask import Flask, render_template, request, jsonify
import openai
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

app = Flask(__name__)

# OpenAI APIキーの設定
openai.api_key = os.getenv('OPENAI_API_KEY')

# タイムアウト設定（秒）
API_TIMEOUT = 60
MAX_SEARCH_TIME = 240  # 4分でタイムアウト

def search_with_timeout(query, timeout=API_TIMEOUT):
    """タイムアウト付きでOpenAI APIを呼び出す"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたは有能な検索アシスタントです。質問に対して簡潔で正確な回答を提供してください。"},
                {"role": "user", "content": query}
            ],
            max_tokens=500,
            temperature=0.7,
            timeout=timeout  # APIレベルでのタイムアウト
        )
        return response.choices[0].message.content.strip()
    except openai.error.Timeout:
        return "検索がタイムアウトしました。もう一度お試しください。"
    except openai.error.RateLimitError:
        return "APIの利用制限に達しました。しばらく待ってからお試しください。"
    except openai.error.APIError as e:
        return f"API エラーが発生しました: {str(e)}"
    except Exception as e:
        return f"エラーが発生しました: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    start_time = time.time()
    
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'クエリが提供されていません'}), 400
        
        query = data['query'].strip()
        if not query:
            return jsonify({'error': '空のクエリです'}), 400
        
        # 長すぎるクエリをチェック
        if len(query) > 1000:
            return jsonify({'error': 'クエリが長すぎます（1000文字以下にしてください）'}), 400
        
        # バックグラウンドで検索実行（タイムアウト付き）
        def search_task():
            return search_with_timeout(query, API_TIMEOUT)
        
        # ThreadPoolExecutorを使用してタイムアウト制御
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(search_task)
            try:
                result = future.result(timeout=MAX_SEARCH_TIME)
                elapsed_time = time.time() - start_time
                
                return jsonify({
                    'result': result,
                    'elapsed_time': round(elapsed_time, 2)
                })
            
            except Exception as e:
                return jsonify({
                    'error': f'検索処理でエラーが発生しました: {str(e)}'
                }), 500
                
    except Exception as e:
        return jsonify({'error': f'リクエスト処理でエラーが発生しました: {str(e)}'}), 500

@app.route('/health')
def health_check():
    """ヘルスチェック用エンドポイント"""
    return jsonify({'status': 'healthy', 'timestamp': time.time()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
