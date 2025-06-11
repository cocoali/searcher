document.addEventListener('DOMContentLoaded', function () {
    const searchForm = document.getElementById('searchForm');
    const statusDiv = document.getElementById('status');
    const resultsDiv = document.getElementById('results');
    const searchBtn = document.getElementById('searchBtn');
    const spinner = document.getElementById('loadingSpinner');
    const loadingDiv = document.getElementById('loading');

    searchForm.addEventListener('submit', async function (e) {
        e.preventDefault();

        const url = document.getElementById('url').value;
        const searchText = document.getElementById('search_text').value;
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        const resultsDiv = document.getElementById('results');
        const loadingDiv = document.getElementById('loading');
        const searchBtn = document.getElementById('searchBtn');

        // 入力値の検証
        if (!url || !searchText) {
            resultsDiv.innerHTML = '<p class="error">URLと検索テキストは必須です。</p>';
            return;
        }

        try {
            loadingDiv.style.display = 'block';
            searchBtn.disabled = true;
            resultsDiv.innerHTML = '<p>検索中...</p>';

            const formData = new FormData();
            formData.append('url', url);
            formData.append('search_text', searchText);
            if (username) formData.append('username', username);
            if (password) formData.append('password', password);

            const response = await fetch('/search', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                let html = '<h2>検索結果</h2>';

                if (data.results.length === 0) {
                    html += '<p>検索結果が見つかりませんでした。</p>';
                } else {
                    data.results.forEach(result => {
                        html += `<div class="result-item">`;
                        html += `<h3><a href="${result.url}" target="_blank">${result.url}</a></h3>`;

                        if (result.body_matches && result.body_matches.length > 0) {
                            html += '<h4>本文の一致:</h4>';
                            result.body_matches.forEach(match => {
                                html += `<p>${match}</p>`;
                            });
                        }

                        if (result.head_matches && result.head_matches.length > 0) {
                            html += '<h4>headタグ内の一致:</h4>';
                            result.head_matches.forEach(match => {
                                html += `<p>${match}</p>`;
                            });
                        }

                        if (result.href_matches && result.href_matches.length > 0) {
                            html += '<h4>リンクの一致:</h4>';
                            result.href_matches.forEach(match => {
                                html += `<p>テキスト: ${match.text}</p>`;
                                html += `<p>リンク: <a href="${match.href}" target="_blank">${match.href}</a></p>`;
                            });
                        }

                        html += '</div>';
                    });
                }

                resultsDiv.innerHTML = html;
            } else {
                resultsDiv.innerHTML = `<p class="error">エラー: ${data.error}</p>`;
            }
        } catch (error) {
            console.error('エラー発生:', error);
            resultsDiv.innerHTML = `<p class="error">エラーが発生しました: ${error.message}</p>`;
        } finally {
            loadingDiv.style.display = 'none';
            searchBtn.disabled = false;
        }
    });

    function resetUI() {
        resultsDiv.innerHTML = '';
        statusDiv.style.display = 'none';
    }

    function showLoading() {
        searchBtn.disabled = true;
        searchBtn.textContent = '🔍 検索中...';
        spinner.style.display = 'block';
        loadingDiv.style.display = 'block';
        showStatus('検索を開始しています...', 'loading');
    }

    function hideLoading() {
        searchBtn.disabled = false;
        searchBtn.textContent = '🔍 検索開始';
        spinner.style.display = 'none';
        loadingDiv.style.display = 'none';
    }

    function showStatus(message, type) {
        statusDiv.className = `status ${type}`;
        statusDiv.textContent = message;
        statusDiv.style.display = 'block';
    }

    function showNoResults() {
        resultsDiv.innerHTML = `
          <div class="no-results">
              <h3>🔍 検索結果なし</h3>
              <p>該当するテキストが見つかりませんでした</p>
              <p>別のキーワードで検索してみてください</p>
          </div>
      `;
    }

    function displayResults(results) {
        console.log('検索結果の表示:', results);

        if (!results || results.length === 0) {
            resultsDiv.innerHTML = '<div class="no-results">検索結果が見つかりませんでした</div>';
            return;
        }

        const resultsHtml = results.map(result => {
            const sections = [];

            // 本文のマッチ
            if (result.body_matches && result.body_matches.length > 0) {
                sections.push(`
                    <div class="result-section">
                        <h3>本文の一致</h3>
                        <div class="matches">
                            ${result.body_matches.map(match => `<div class="match">${match}</div>`).join('')}
                        </div>
                    </div>
                `);
            }

            // headタグのマッチ
            if (result.head_matches && result.head_matches.length > 0) {
                sections.push(`
                    <div class="result-section">
                        <h3>headタグ内の一致</h3>
                        <div class="matches">
                            ${result.head_matches.map(match => `<div class="match">${match}</div>`).join('')}
                        </div>
                    </div>
                `);
            }

            // href属性のマッチ
            if (result.href_matches && result.href_matches.length > 0) {
                sections.push(`
                    <div class="result-section">
                        <h3>リンクの一致</h3>
                        <div class="matches">
                            ${result.href_matches.map(match => `
                                <div class="match">
                                    <a href="${match.original_url}" target="_blank">
                                        ${match.text || match.original_url}
                                    </a>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `);
            }

            return `
                <div class="result">
                    <h2>ページ: ${result.url}</h2>
                    ${sections.join('')}
                </div>
            `;
        }).join('');

        resultsDiv.innerHTML = resultsHtml;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // エンターキーでの検索
    document.getElementById('searchText').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            searchForm.dispatchEvent(new Event('submit'));
        }
    });

    // フォームのバリデーション
    const urlInput = document.getElementById('url');
    const textInput = document.getElementById('searchText');

    urlInput.addEventListener('blur', function () {
        if (this.value && !isValidUrl(this.value)) {
            this.setCustomValidity('有効なURLを入力してください（例: https://example.com）');
        } else {
            this.setCustomValidity('');
        }
    });

    textInput.addEventListener('input', function () {
        if (this.value.length > 100) {
            this.setCustomValidity('検索テキストは100文字以内で入力してください');
        } else {
            this.setCustomValidity('');
        }
    });

    function isValidUrl(string) {
        try {
            const url = new URL(string);
            return url.protocol === 'http:' || url.protocol === 'https:';
        } catch (_) {
            return false;
        }
    }
});

function startSearch() {
    const url = document.getElementById('url').value;
    const searchText = document.getElementById('search-text').value;
    const progress = document.getElementById('progress');
    const results = document.getElementById('results');

    if (!url || !searchText) {
        alert('URLと検索テキストを入力してください');
        return;
    }

    progress.innerHTML = '検索中...';
    results.innerHTML = '';

    fetch('/search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            url: url,
            search_text: searchText
        })
    })
        .then(response => response.json())
        .then(data => {
            progress.innerHTML = '';
            if (data.error) {
                results.innerHTML = `<div class="error">${data.error}</div>`;
                return;
            }

            if (data.results.length === 0) {
                results.innerHTML = '<div class="no-results">検索結果が見つかりませんでした。</div>';
                return;
            }

            const resultsHtml = data.results.map(result => `
            <div class="result-item">
                <h3><a href="${result.url}" target="_blank">${result.title}</a></h3>
                <p class="url">${result.url}</p>
                <p class="matches">マッチ数: ${result.matches}</p>
                <div class="snippets">
                    ${result.snippets.map(snippet => `<p class="snippet">${snippet}</p>`).join('')}
                </div>
            </div>
        `).join('');

            results.innerHTML = resultsHtml;
        })
        .catch(error => {
            progress.innerHTML = '';
            results.innerHTML = `<div class="error">エラーが発生しました: ${error.message}</div>`;
        });
}