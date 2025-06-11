# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, render_template
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import base64
import os

app = Flask(__name__)

# セキュリティ設定
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30分

# レート制限の設定
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per hour", "10 per minute"]
)

class WebTextSearcher:
    def __init__(self):
        self.timeout = 10
        self.visited_urls = set()
        self.max_depth = 2  # 最大検索深度

    def _highlight_text(self, text, search_text):
        """検索テキストをハイライト表示"""
        pattern = re.compile(re.escape(search_text), re.IGNORECASE)
        return pattern.sub(lambda m: f'<mark>{m.group()}</mark>', text)

    def _is_same_domain(self, url, base_url):
        """同じドメインかチェック"""
        try:
            return urlparse(url).netloc == urlparse(base_url).netloc
        except:
            return False

    def search(self, url, search_text, auth=None):
        """指定されたURLから検索を開始"""
        print(f"検索開始: URL={url}, 検索テキスト={search_text}")
        self.visited_urls = set()
        results = []
        
        try:
            self._search_page(url, search_text, depth=0, results=results, auth=auth)
            return {
                'success': True,
                'results': results
            }
        except Exception as e:
            print(f"検索中にエラー: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _search_page(self, url, search_text, depth=0, results=None, auth=None):
        """ページを検索し、結果を追加"""
        if results is None:
            results = []
            
        if url in self.visited_urls or depth > self.max_depth:
            return
            
        self.visited_urls.add(url)
        print(f"ページを検索中: {url} (深さ: {depth})")
        
        try:
            # ページを取得
            headers = {}
            if auth:
                auth_str = f"{auth['username']}:{auth['password']}"
                auth_bytes = auth_str.encode('ascii')
                base64_bytes = base64.b64encode(auth_bytes)
                headers['Authorization'] = f"Basic {base64_bytes.decode('ascii')}"
            
            response = requests.get(url, timeout=self.timeout, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # ページの検索結果を格納
            page_results = {
                'url': url,
                'body_matches': [],
                'head_matches': [],
                'href_matches': []
            }
            
            # 本文の検索
            text = soup.get_text()
            clean_text = ' '.join(text.split())
            if search_text.lower() in clean_text.lower():
                highlighted_text = self._highlight_text(clean_text, search_text)
                page_results['body_matches'] = [highlighted_text]
            
            # headタグ内の検索
            head = soup.find('head')
            if head:
                head_text = head.get_text()
                if search_text.lower() in head_text.lower():
                    highlighted_text = self._highlight_text(head_text, search_text)
                    page_results['head_matches'] = [highlighted_text]
            
            # href属性の検索
            for link in soup.find_all('a', href=True):
                href = link['href']
                link_text = link.get_text().strip()
                
                try:
                    # 相対URLを絶対URLに変換
                    full_url = urljoin(url, href)
                    normalized_url = full_url.rstrip('/')
                    
                    # 検索テキストが数字の場合の特別な処理
                    if search_text.isdigit():
                        if f"/journal/{search_text}" in normalized_url:
                            highlighted_url = self._highlight_text(full_url, search_text)
                            highlighted_text = self._highlight_text(link_text, search_text) if link_text else highlighted_url
                            page_results['href_matches'].append({
                                'text': highlighted_text,
                                'href': highlighted_url,
                                'original_url': full_url,
                                'page_url': url
                            })
                    # 通常のテキスト検索
                    elif search_text.lower() in normalized_url.lower() or search_text.lower() in link_text.lower():
                        highlighted_url = self._highlight_text(full_url, search_text)
                        highlighted_text = self._highlight_text(link_text, search_text) if link_text else highlighted_url
                        page_results['href_matches'].append({
                            'text': highlighted_text,
                            'href': highlighted_url,
                            'original_url': full_url,
                            'page_url': url
                        })
                except Exception as e:
                    print(f"リンクの処理中にエラー: {href} - {str(e)}")
                    continue
            
            # マッチがある場合のみ結果に追加
            if any([page_results['body_matches'], page_results['head_matches'], page_results['href_matches']]):
                results.append(page_results)
            
            # 次の階層のリンクを取得
            if depth < self.max_depth:
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    try:
                        full_url = urljoin(url, href)
                        if self._is_same_domain(full_url, url) and full_url not in self.visited_urls:
                            self._search_page(full_url, search_text, depth + 1, results, auth)
                    except Exception as e:
                        print(f"リンクの処理中にエラー: {href} - {str(e)}")
                        continue
                        
        except Exception as e:
            print(f"ページの検索中にエラー: {url} - {str(e)}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
@limiter.limit("10 per minute")  # エンドポイントごとの制限
def search():
    print("検索リクエストを受信")
    url = request.form.get('url')
    search_text = request.form.get('search_text')
    username = request.form.get('username')
    password = request.form.get('password')
    
    print(f"リクエストパラメータ: URL={url}, 検索テキスト={search_text}")
    
    if not url or not search_text:
        print("パラメータが不足")
        return jsonify({
            'success': False,
            'error': 'URLと検索テキストを入力してください'
        })
    
    auth = None
    if username and password:
        auth = {
            'username': username,
            'password': password
        }
    
    searcher = WebTextSearcher()
    result = searcher.search(url, search_text, auth)
    print(f"検索結果: {result}")
    return jsonify(result)

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        'success': False,
        'error': 'リクエストが多すぎます。しばらく待ってから再試行してください。'
    }), 429

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
