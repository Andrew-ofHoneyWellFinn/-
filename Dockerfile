FROM python:3.10

# コンテナ内の作業ディレクトリ
WORKDIR /app

# pipのアップグレード
RUN python -m pip install --upgrade pip

# パッケージリストをコピーしてインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションのコードをコピー
COPY . .

# Djangoのデフォルトポートを開放
EXPOSE 8000

# ★修正：Djangoのサーバー起動コマンドに変更
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]