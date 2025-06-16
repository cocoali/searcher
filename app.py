import os
import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify
from urllib.parse import urljoin, urlparse
import time
import re
from concurrent.futures import ThreadPoolExecutor
import traceback
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# タイムアウト設定
REQUEST_TIMEOUT = 10
MAX_SEARCH_TIME = 60

def clean_text(text):
    """テキストをクリーンアップ"""
    if not text:
        return ""
    # 改行や余分な空白を削除
    text = re.sub(r'\s+', ' ', text.strip())
    return text

def scrape_website(url, query=None):
    """ウェブサイトをスクレイピング"""
    try:
        logger.info(f"Scraping URL: {url}")
        
        # URLの検証
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            return {"error": "無効なURLです"}
        
        # ヘッダーを設定してリクエスト
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        # BeautifulSoupでパース
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 基本情報を取得
        title = soup.find('title')
        title_text = clean_text(title.text) if title else "タイトルなし"
        
        # メタ情報
        description = soup.find('meta', attrs={'name': 'description'})
        description_text = clean_text(description.get('content')) if description else ""
        
        # 見出しを取得
        headings = []
        for h in soup.find_all(['h1', 'h2', 'h3'], limit=10):
            heading_text = clean_text(h.text)
            if heading_text:
                headings.append(heading_text)
        
        # 段落テキストを取得
        paragraphs = []
        for p in soup.find_all('p', limit=20):
            p_text = clean_text(p.text)
            if p_text and len(p_text) > 20:  # 短すぎるテキストは除外
                paragraphs.append(p_text)
        
        # リンクを取得
        links = []
        for a in soup.find_all('a', href=True, limit=15):
            link_text = clean_text(a.text)
            if link_text:
                href = urljoin(url, a['href'])
                links.append({
                    'text': link_text,
                    'url': href
                })
        
        # クエリが指定されている場合、関連するコンテンツをフィルタリング
        if query:
            query_lower = query.lower()
            
            # 関連する見出しをフィルタ
            relevant_headings = [h for h in headings if query_lower in h.lower()]
            
            # 関連する段落をフィルタ
            relevant_paragraphs = [p for p in paragraphs if query_lower in p.lower()]
            
            # 関連するリンクをフィルタ
            relevant_links = [l for l in links if query_lower in l['text'].lower()]
            
            return {
                'url': url,
                'title': title_text,
                'description': description_text,
                'query': query,
                'headings': relevant_headings[:5],
                'paragraphs': relevant_paragraphs[:10],
                'links': relevant_links[:10],
                'found_matches': len(relevant_headings) + len(relevant_paragraphs) + len(relevant_links)
            }
        else:
            return {
                'url': url,
                'title': title_text,
                'description': description_text,
                'headings': headings[:5],
                'paragraphs': paragraphs[:10],
                'links': links[:10]
            }
            
    except requests.exceptions.Timeout:
        logger.error(f"Timeout error for URL: {url}")
        return {"error": "リクエストがタイムアウトしました"}
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error for URL: {url}")
        return {"error": "接続エラーが発生しました"}
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error for URL: {url}, Status: {e.response.status_code}")
        return {"error": f"HTTPエラー: {e.response.status_code}"}
    except Exception as e:
        logger.error(f"Scraping error for URL: {url}, Error: {e}")
        logger.error(traceback.format_exc())
        return {"error": f"スクレイピングエラー: {str(e)}"}

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Template rendering error: {e}")
        return jsonify({'error': 'テンプレートの読み込みに失敗しました'}), 500

@app.route('/search', methods=['POST'])
def search():
    start_time = time.time()
    
    try:
        logger.info("Search endpoint called")
        data = request.get_json()
        logger.info(f"Request data received: {bool(data)}")
        
        if not data:
            return jsonify({'error': 'リクエストデータが提供されていません'}), 400
        
        # URLとクエリを取得
        url = data.get('url', '').strip()
        query = data.get('query', '').strip()
        
        if not url:
            return jsonify({'error': 'URLが提供されていません'}), 400
        
        # HTTPスキームを追加（必要に応じて）
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        logger.info(f"Processing URL: {url}")
        if query:
            logger.info(f"Search query: {query}")
        
        # スクレイピング実行
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(scrape_website, url, query)
            try:
                result = future.result(timeout=MAX_SEARCH_TIME)
                elapsed_time = time.time() - start_time
                
                if 'error' in result:
                    logger.warning(f"Scraping failed: {result['error']}")
                    return jsonify({
                        'error': result['error'],
                        'elapsed_time': round(elapsed_time, 2)
                    }), 400
                
                result['elapsed_time'] = round(elapsed_time, 2)
                logger.info(f"Scraping completed successfully in {elapsed_time:.2f}s")
                return jsonify(result)
                
            except Exception as e:
                logger.error(f"ThreadPoolExecutor error: {e}")
                return jsonify({
                    'error': f'処理中にエラーが発生しました: {str(e)}'
                }), 500
                
    except Exception as e:
        logger.error(f"Request processing error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'リクエスト処理でエラーが発生しました: {str(e)}'}), 500

@app.route('/health')
def health_check():
    """ヘルスチェック用エンドポイント"""
    return jsonify({
        'status': 'healthy', 
        'timestamp': time.time(),
        'port': os.environ.get('PORT', 'not set')
    })

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'ページが見つかりません'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': '内部サーバーエラーが発生しました'}), 500

if __name__ == '__main__':
    # Railway用のポート設定
    port = int(os.environ.get('PORT', 8080))
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"Starting Flask app on port {port}, debug={debug_mode}")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
