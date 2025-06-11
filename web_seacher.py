import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import time
from concurrent.futures import ThreadPoolExecutor
import threading
from collections import defaultdict

class WebTextSearcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.visited_urls = set()
        self.results = []
        self.progress_callback = None
        self.max_depth = 3
        self.max_urls = 50
        self.timeout = 10
        
    def search(self, base_url, search_text, progress_callback=None):
        """メインの検索関数"""
        self.visited_urls.clear()
        self.results.clear()
        self.progress_callback = progress_callback
        
        try:
            self._crawl_and_search(base_url, search_text, 0, base_url)
            return {
                'success': True,
                'results': self.results,
                'total_pages': len(self.visited_urls)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'results': self.results,
                'total_pages': len(self.visited_urls)
            }
    
    def _crawl_and_search(self, url, search_text, depth, base_domain):
        """再帰的にページをクロールして検索"""
        if (depth > self.max_depth or 
            len(self.visited_urls) >= self.max_urls or 
            url in self.visited_urls or
            not self._is_same_domain(url, base_domain)):
            return
        
        self.visited_urls.add(url)
        
        if self.progress_callback:
            self.progress_callback(f"クロール中: {url}")
        
        try:
            # ページを取得
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # エンコーディングを適切に設定
            if response.encoding == 'ISO-8859-1':
                response.encoding = response.apparent_encoding
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # JavaScriptやCSSを除去
            for script in soup(["script", "style"]):
                script.decompose()
            
            # テキストを抽出
            text_content = soup.get_text()
            clean_text = re.sub(r'\s+', ' ', text_content).strip()
            
            # 検索テキストをチェック
            matches = self._find_matches(clean_text, search_text)
            
            if matches:
                # ページタイトルを取得
                title = soup.find('title')
                page_title = title.get_text() if title else "タイトルなし"
                
                # マッチした文脈を抽出
                context_snippets = self._extract_context(clean_text, search_text)
                
                self.results.append({
                    'url': url,
                    'title': page_title.strip(),
                    'matches': len(matches),
                    'snippets': context_snippets[:3]  # 最大3つのスニペット
                })
            
            # 次の階層のリンクを取得
            if depth < self.max_depth:
                links = self._extract_links(soup, url)
                for link in links[:10]:  # 各ページから最大10個のリンク
                    if len(self.visited_urls) < self.max_urls:
                        time.sleep(0.1)  # レート制限
                        self._crawl_and_search(link, search_text, depth + 1, base_domain)
        
        except Exception as e:
            print(f"Error crawling {url}: {str(e)}")
    
    def _is_same_domain(self, url, base_url):
        """同じドメインかチェック"""
        try:
            return urlparse(url).netloc == urlparse(base_url).netloc
        except:
            return False
    
    def _find_matches(self, text, search_text):
        """テキスト内の一致を検索"""
        pattern = re.compile(re.escape(search_text), re.IGNORECASE)
        return pattern.findall(text)
    
    def _extract_context(self, text, search_text, context_length=100):
        """マッチした箇所の前後の文脈を抽出"""
        pattern = re.compile(f'(.{{0,{context_length}}})({re.escape(search_text)})(.{{0,{context_length}}})', re.IGNORECASE)
        matches = pattern.findall(text)
        
        snippets = []
        for before, match, after in matches[:5]:  # 最大5個のマッチ
            snippet = f"...{before.strip()}<mark>{match}</mark>{after.strip()}..."
            snippets.append(snippet)
        
        return snippets
    
    def _extract_links(self, soup, base_url):
        """ページからリンクを抽出"""
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            
            # 有効なHTTP/HTTPSリンクのみ
            if full_url.startswith(('http://', 'https://')):
                links.append(full_url)
        
        return list(set(links))  # 重複を除去