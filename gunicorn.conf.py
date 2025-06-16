import os

# ワーカープロセス数
workers = int(os.environ.get('GUNICORN_WORKERS', 2))

# ワーカークラス
worker_class = 'sync'

# タイムアウト設定（秒）
timeout = int(os.environ.get('GUNICORN_TIMEOUT', 300))
keepalive = 2

# バインド設定
bind = f"0.0.0.0:{os.environ.get('PORT', 5000)}"

# ログ設定
loglevel = 'info'
accesslog = '-'
errorlog = '-'

# プロセス設定
preload_app = True
max_requests = 1000
max_requests_jitter = 50

# メモリ管理
worker_tmp_dir = '/dev/shm'
