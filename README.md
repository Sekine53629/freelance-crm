# Freelance CRM - 営業案件管理Bot

Slack + PostgreSQLで動作するフリーランス向け案件管理システム。
Tailscale経由で自宅サーバーから運用。

## 機能

- 案件登録（Slackから対話式/フォーム入力）
- 獲得チャネル別の分析
- クライアント管理
- (予定) Streamlitダッシュボード

## 構成

```
freelance-crm/
├── bot/
│   ├── app.py              # メインアプリ
│   ├── config.py           # 設定
│   ├── database.py         # DB操作
│   ├── models.py           # SQLAlchemyモデル
│   └── handlers/
│       └── project_handler.py  # 案件ハンドラー
├── dashboard/
│   └── (Streamlitアプリ予定)
├── migrations/
│   └── 001_init.sql        # DBスキーマ
├── .env.example
├── requirements.txt
└── README.md
```

## セットアップ

### 1. PostgreSQL設定

```bash
# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib
sudo -u postgres psql

# PostgreSQLコンソール内で:
CREATE DATABASE freelance_crm;
CREATE USER freelance_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE freelance_crm TO freelance_user;
\q

# スキーマ適用
psql -U freelance_user -d freelance_crm -f migrations/001_init.sql
```

### 2. Python環境

```bash
cd freelance-crm
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Slack App作成

1. https://api.slack.com/apps にアクセス
2. "Create New App" → "From scratch"
3. Bot Token Scopes追加:
   - `chat:write`
   - `commands`
   - `im:history`
   - `im:write`
   - `app_mentions:read`
4. Socket Mode有効化
5. Event Subscriptions有効化:
   - `message.im`
   - `app_mention`
6. Slash Commands追加: `/project`
7. Interactivity有効化
8. App-Level Token生成 (connections:write スコープ)
9. Install to Workspace

### 4. 環境変数設定

```bash
cp .env.example .env
# .envを編集してトークンを設定
```

### 5. 起動

```bash
cd bot
python app.py
```

### 6. systemdで常駐化 (Linux)

```ini
# /etc/systemd/system/freelance-crm.service
[Unit]
Description=Freelance CRM Slack Bot
After=network.target postgresql.service

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/freelance-crm/bot
ExecStart=/path/to/freelance-crm/venv/bin/python app.py
Restart=always
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable freelance-crm
sudo systemctl start freelance-crm
```

## 使い方

Slackで以下のコマンド/メッセージを送信:

- `案件登録` - 登録ボタンを表示
- `/project` - 登録フォームを直接開く
- `案件一覧` - 最近の案件を表示
- `ヘルプ` - コマンド一覧

## Tailscale設定

自宅サーバーにTailscaleをインストール:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

スマホからもTailscaleに接続すれば、外出先からも自宅サーバーにアクセス可能。
Socket Modeを使用しているため、外部からのHTTPアクセスは不要。

## 今後の予定

- [ ] データベース保存の実装
- [ ] Streamlitダッシュボード
- [ ] 月次レポート自動生成
- [ ] 工数トラッキング機能
