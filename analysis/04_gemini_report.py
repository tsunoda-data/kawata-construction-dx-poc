# %% [markdown]
# # AI自然言語レポート自動生成
# ## 加和太建設 DXコックピット PoC — Step 5
# Gemini APIを活用し、BigQueryのKPIデータから経営サマリーレポートを自動生成するデモ

# %% [markdown]
# ## 1. セットアップ
# - 必要なライブラリのインストールとインポートを行います。
# - Colab環境で実行する場合は、APIキーのシークレット設定が必要です。

# %%
# !pip install -q google-generativeai

import os
import json
import pandas as pd
from IPython.display import display, Markdown

import google.generativeai as genai

# 環境変数またはColabのシークレットからAPIキーを取得
try:
    from google.colab import userdata
    GEMINI_API_KEY = userdata.get('GEMINI_API_KEY')
except ImportError:
    # ローカル環境での実行時
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# BigQueryの設定（本番環境用、今回はモックデータを使用）
PROJECT_ID = 'your-project-id'  # ← ここを変更  
DATASET = 'your_dataset'  # ← ここを変更

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print("Gemini API key configured successfully.")
else:
    print("Warning: GEMINI_API_KEY is not set. The notebook will use simulated fallback responses.")

# 生成モデルの初期化（高速・低コストなフラッシュモデルを採用）
model = genai.GenerativeModel('gemini-2.0-flash')

# %% [markdown]
# ## 2. KPIデータの取得と集計
# BigQueryのビュー、またはCSVデータから以下の情報を集計します。
# 今回のPoCでは、前ステップまでに作成したダミーデータの集計結果を辞書として定義します。

# %%
# KPI集計データ（モックデータ）
kpi_data = {
    "report_date": "2026-07-23",
    "company_summary": {
        "total_revenue_forecast": 4500000000,
        "revenue_by_bu": {
            "建設事業": 3200000000,
            "不動産事業": 800000000,
            "SaaS事業": 300000000,
            "施設運営": 200000000
        },
        "target_achievement_rate": 95.5
    },
    "cost_risk_summary": {
        "high_risk_projects_count": 3,
        "total_risk_amount": 120000000,
        "notable_projects": [
            {"name": "三島駅前再開発プロジェクト", "cost_rate": 105.2, "issue": "資材価格の高騰による原価悪化"}
        ]
    },
    "cashflow_summary": {
        "current_balance": 1500000000,
        "next_3_months_forecast": [
            {"month": "2026-08", "net_cashflow": 50000000},
            {"month": "2026-09", "net_cashflow": -20000000},
            {"month": "2026-10", "net_cashflow": 120000000}
        ],
        "warning": "2026年9月は大型工事の支払いが先行するため単月赤字の見込み"
    },
    "saas_metrics": {
        "mrr": 25000000,
        "arr": 300000000,
        "churn_rate_percent": 1.2,
        "new_acquisitions": 5
    },
    "facility_operations": {
        "visitors_last_month": 12500,
        "revenue_last_month": 18000000,
        "occupancy_rate_percent": 88.5
    }
}

# データをプロンプトに埋め込みやすいようJSON文字列に変換
kpi_json = json.dumps(kpi_data, ensure_ascii=False, indent=2)
print("KPIデータの集計が完了しました。")

# %% [markdown]
# ## 3. プロンプトエンジニアリング
# 目的別に3種類のプロンプト（週次経営サマリー、リスクアラート、エリアROI分析）を設計します。

# %%
system_instruction = """あなたは加和太建設（静岡県三島市に拠点を置く総合建設企業）の優秀な経営企画AIアシスタントです。
提供されたKPIデータに基づいて、経営陣向けの簡潔で洞察に満ちたレポートを作成してください。
トーンはプロフェッショナルで、事実に基づきつつ、経営判断に資する示唆を含めること。
マークダウン形式で見やすく出力してください。"""

def create_prompt(report_type, kpi_json_str):
    base_prompt = f"{system_instruction}\n\n【KPIデータ】\n{kpi_json_str}\n\n"
    
    if report_type == "weekly_summary":
        return base_prompt + """【指示】
上記のデータから、「週次経営サマリーレポート」を作成してください。
以下の構成を含めること：
1. 全体業績サマリー（売上予測と目標達成率）
2. 各事業部の概況（建設、不動産、SaaS、施設運営）
3. キャッシュフローの見通し
4. 経営陣へのAIからの推奨アクション（1〜2点）
箇条書きを活用し、簡潔にまとめてください。"""

    elif report_type == "risk_alert":
        return base_prompt + """【指示】
上記のデータから、「リスクアラートレポート」を作成してください。
以下の構成を含めること：
1. 原価超過リスクのあるプロジェクト（具体的な名称、原価率、課題）
2. キャッシュフローの警告事項（単月赤字の見込みなど）
3. リスク軽減のための具体的な対策案（AIからの提案）
重要度が高い事項を強調（太字など）して記載してください。"""

    elif report_type == "area_roi":
        return base_prompt + """【指示】
上記のデータから、三島/沼津/函南エリアの投資回収状況を評価する「エリアROI分析レポート」を作成してください。
施設運営事業の集客・売上データ、およびSaaS事業などの新規事業の進捗を組み合わせ、
地域密着型企業としての現在の立ち位置と、今後のエリア投資の方向性について洞察を提供してください。"""

    return base_prompt

# フォールバック用のダミーレスポンス
FALLBACK_RESPONSES = {
    "weekly_summary": """### 週次経営サマリーレポート (Mock)
**1. 全体業績サマリー**
*   **売上予測:** 45億円（目標達成率: 95.5%）
*   目標達成に向けて堅調に推移していますが、残り4.5%のギャップを埋める施策が必要です。

**2. 各事業部の概況**
*   **建設事業:** 売上32億円。主力事業として安定して貢献。
*   **不動産事業:** 売上8億円。
*   **SaaS事業:** 売上3億円。MRR2,500万円、チャーンレート1.2%と健全な成長を維持。
*   **施設運営:** 売上2億円。先月来場者数12,500人、稼働率88.5%と好調。

**3. キャッシュフローの見通し**
*   現在の現預金残高は15億円。
*   向こう3ヶ月は全体としてプラス推移の見込みですが、9月は大型支払いの影響で2,000万円の単月赤字が予想されます。

**4. 推奨アクション**
*   9月の資金繰りについて、早急に支払いスケジュールの調整または短期資金の手当てを確認してください。
*   SaaS事業の新規獲得（5件）の成功要因を分析し、更なる成長投資を検討してください。""",
    
    "risk_alert": """### リスクアラートレポート (Mock)
**1. 原価超過リスク（要注意プロジェクト）**
*   **高リスクプロジェクト数:** 3件（合計リスク金額: 1.2億円）
*   🚨 **三島駅前再開発プロジェクト**
    *   **現在の原価率:** 105.2%
    *   **課題:** 資材価格の高騰による原価悪化
    *   **影響:** 全体利益を大きく圧迫する可能性あり。

**2. キャッシュフローの警告**
*   🚨 **2026年9月 キャッシュフロー悪化見込み**
    *   大型工事の支払いが先行するため、単月で**2,000万円の赤字（資金流出）**となる見込みです。

**3. リスク軽減策（AI提案）**
*   **調達の見直し:** 三島駅前プロジェクトについて、代替資材の検討や協力業者との価格交渉を即時実施。
*   **支払い条件の最適化:** 9月に集中している支払いのうち、分割可能なものがないか交渉。""",
    
    "area_roi": """### エリアROI分析レポート (Mock)
**1. エリア投資の現状（三島・沼津・函南）**
*   **施設運営事業:** 先月来場者数12,500人、稼働率88.5%と非常に高く、地域住民・観光客の双方を取り込めており、エリア投資の回収は順調です。
*   **SaaS事業:** 建設業向けSaaSは地域建設ネットワークを通じて着実に普及（新規5件獲得、解約率1.2%）しており、IT面からの地域貢献と収益化を両立しています。

**2. 総合評価と洞察**
*   加和太建設が掲げる「元気をつくる」というミッションは、リアルな場（施設運営）とデジタル（SaaS）の掛け合わせにより、三島周辺エリアで高い相乗効果（ROI）を生み出しています。

**3. 今後の方向性**
*   施設来場者のデータをSaaSや不動産開発に活かすクロスセル戦略の検討を推奨します。"""
}

def generate_report(report_type):
    if GEMINI_API_KEY:
        try:
            prompt = create_prompt(report_type, kpi_json)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"API Error: {e}\nFalling back to mock data.")
            return FALLBACK_RESPONSES[report_type]
    else:
        return FALLBACK_RESPONSES[report_type]

# %% [markdown]
# ## 4. レポート生成 — 週次経営サマリー
# 経営陣向けの週次業績サマリーを生成します。

# %%
weekly_report = generate_report("weekly_summary")
display(Markdown(weekly_report))

# %% [markdown]
# ## 5. レポート生成 — リスクアラート
# 原価超過やキャッシュフローの懸念に焦点を当てたリスクレポートを生成します。

# %%
risk_report = generate_report("risk_alert")
display(Markdown(risk_report))

# %% [markdown]
# ## 6. レポート生成 — エリアROI分析  
# 三島・沼津・函南エリアでの事業シナジーと投資対効果を分析します。

# %%
area_roi_report = generate_report("area_roi")
display(Markdown(area_roi_report))

# %% [markdown]
# ## 7. 自動配信シミュレーション
# 生成されたレポートをCloud FunctionsやCloud Schedulerを用いて自動配信するアーキテクチャのシミュレーションです。

# %%
# Cloud Functions へのWebhookペイロードのサンプル
webhook_payload = {
    "to": "executives@kawata.example.com",
    "subject": f"【自動生成】週次経営サマリー ({kpi_data['report_date']})",
    "body_markdown": weekly_report,
    "slack_channel": "#mgmt-reports",
    "urgency": "normal"
}

print("=== メール/Slack自動配信ペイロード (JSON) ===")
print(json.dumps(webhook_payload, ensure_ascii=False, indent=2))

# %% [markdown]
# ### 配信アーキテクチャ (Markdown Mermaid)
# ```mermaid
# graph LR
#     A[Cloud Scheduler] -->|毎朝8:00 トリガー| B(Cloud Functions)
#     B -->|SQL実行| C[(BigQuery)]
#     C -->|KPIデータ| B
#     B -->|プロンプト送信| D[Gemini API]
#     D -->|自然言語レポート| B
#     B -->|APIコール| E[Gmail API / SendGrid]
#     B -->|Webhook| F[Slack API]
#     E --> G[経営陣のメール]
#     F --> H[経営会議チャンネル]
# ```

# %% [markdown]
# ## 8. 考察
# - **レポート品質の評価:** KPIの無機質な数字を、具体的な経営課題（9月の資金繰り、三島駅前の原価高騰）の文脈に翻訳する能力が非常に高く、ダッシュボードを自発的に見に行かない経営層向けの「プッシュ型情報提供」として極めて有効です。
# - **プロンプトエンジニアリングの教訓:** 単にデータを渡すだけでなく、システムプロンプトで「トーン（プロフェッショナル）」や「役割（経営企画アシスタント）」を定義し、出力構成（箇条書き、太字の活用）を明確に指定することが安定した品質につながります。
# - **本番導入への課題:** BigQuery上の最新データをいかにタイムリーかつ正確にJSON化するかのデータパイプライン構築が鍵となります。また、ハルシネーション（AIの嘘）を防ぐため、計算結果（合計値や達成率）はAIに計算させるのではなく、SQL側で計算済みの値を渡す設計にしています。
# - **コスト見積もり:** Gemini 2.0 Flashモデルは非常に安価です。1日1回、週5回レポートを生成しても、トークン単価が低いため月額数十円〜数百円程度のAPIコストに収まる見込みであり、ROIは極めて高いと言えます。
