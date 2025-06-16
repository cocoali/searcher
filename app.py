import os
import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify
from urllib.parse import urljoin, urlparse
import time
import re
from concurrent.futures import ThreadPoolExecutor
import traceback

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
        print(f"Scraping URL: {url}")
        
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
        return {"error": "リクエストがタイムアウトしました"}
    except requests.exceptions.ConnectionError:
        return {"error": "接続エラーが発生しました"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTPエラー: {e.response.status_code}"}
    except Exception as e:
        print(f"Scraping error: {e}")
        print(traceback.format_exc())
        return {"error": f"スクレイピングエラー: {str(e)}"}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    start_time = time.time()
    
    try:
        print("Scraping endpoint called")
        data = request.get_json()
        print(f"Request data: {data}")
        
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
        
        print(f"Scraping URL: {url}")
        if query:
            print(f"Query: {query}")
        
        # スクレイピング実行
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(scrape_website, url, query)
            try:
                result = future.result(timeout=MAX_SEARCH_TIME)
                elapsed_time = time.time() - start_time
                
                if 'error' in result:
                    return jsonify({
                        'error': result['error'],
                        'elapsed_time': round(elapsed_time, 2)
                    }), 400
                
                result['elapsed_time'] = round(elapsed_time, 2)
                print(f"Scraping completed in {elapsed_time:.2f}s")
                return jsonify(result)
                
            except Exception as e:
                print(f"ThreadPoolExecutor error: {e}")
                return jsonify({
                    'error': f'処理中にエラーが発生しました: {str(e)}'
                }), 500
                
    except Exception as e:
        print(f"Request processing error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': f'リクエスト処理でエラーが発生しました: {str(e)}'}), 500

@app.route('/health')
def health_check():
    """ヘルスチェック用エンドポイント"""
    return jsonify({'status': 'healthy', 'timestamp': time.time()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
