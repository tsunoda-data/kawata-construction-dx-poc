# 加和太建設向け「多角化経営DXコックピット」PoC

> **多角化経営の相乗効果を定量化する ― まちづくりROI × AI予兆検知 統合プラットフォーム**

[![Status](https://img.shields.io/badge/Status-PoC%20Design-blue)](https://github.com/your-username/kawata-construction-dx-poc)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Tech](https://img.shields.io/badge/Tech-BigQuery%20%7C%20Vertex%20AI%20%7C%20Looker%20Studio-orange)](ARCHITECTURE.md)

---

## 📌 プロジェクト概要

本プロジェクトは、静岡県三島市を拠点とする**加和太建設株式会社**（売上157億円、従業員306名）の多角化経営を支えるデータ基盤のPoC（概念実証）です。

加和太建設は、建設業の枠を超え「まちづくり企業」として**土木・建築・不動産・施設運営・DX SaaS事業・エリアマネジメント**を展開する地方ゼネコンです。自社開発SaaS「IMPACT CONSTRUCTION」やDXコミュニティ「ON-SITE X」の運営など、**DX先進企業としての顔**を持っています。

### 🎯 解決する課題

| # | 課題 | アプローチ |
| :---: | :--- | :--- |
| **A** | 多角化事業の横断的ROIが見えない | **まちづくりROI可視化** — エリア単位の投資対効果を定量化 |
| **B** | DXエコシステムのKPIが散在 | **DXエコシステムダッシュボード** — SaaS・コミュニティ指標を統合 |
| **C** | 原価予測が実績ベースの線形外挿 | **AI予兆検知** — 機械学習による原価超過の事前


---

## 🏗️ システムアーキテクチャ

```
[データソース]              [データ基盤]           [AI/ML]              [可視化]
                                                                       
IMPACT CONSTRUCTION ─┐     ┌────────────┐      ┌───────────┐       ┌──────────┐
Google Sheets ───────┼───► │  BigQuery  │ ───► │ Vertex AI │ ────► │ Looker   │
AppSheet ────────────┤     │            │      │ AutoML    │       │ Studio   │
外部データ ───────────┘     │  6 datasets│      │ Gemini API│       │          │
                           └────────────┘      └───────────┘       └──────────┘
                                ▲                                       │
                           Cloud Functions                         Gmail/Chat
                           + Scheduler                            自動レポート
```

📐 詳細設計 → [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 📂 リポジトリ構成

```
kawata-construction-dx-poc/
│
├── 📄 README.md                        # 本ファイル
├── 📄 REQUIREMENTS.md                  # 要件定義書（v2.0）
├── 📄 ARCHITECTURE.md                  # システムアーキテクチャ設計書
│
├── 📁 docs/
│   ├── 📄 business_context.md          # 加和太建設 事業構造分析
│   ├── 📄 as_is_to_be.md               # AS-IS / TO-BE分析（予定）
│   └── 📄 roi_estimation.md            # ROI試算根拠（予定）
│
├── 📁 data/
│   ├── 📄 mock_data_generator.py       # ダミーデータ生成スクリプト
│   ├── 📄 projects_master.csv          # 工事マスタ（生成済み）
│   ├── 📄 cost_records.csv             # 原価トランザクション（生成済み）
│   └── ... (その他CSV)
│
├── 📁 analysis/                        # Jupyter Notebook
│   ├── 📓 01_eda.ipynb                 # 探索的データ分析
│   ├── 📓 02_cost_prediction.ipynb     # 原価予測モデル
│   └── 📓 03_cashflow_anomaly.ipynb    # キャッシュフロー異常検知
│
└── 📁 dashboard/                       # ダッシュボード設計
    └── 📄 looker_studio_design.md
```

---

## 🔑 主要ドキュメント

| ドキュメント | 概要 | 読者 |
| :--- | :--- | :--- |
| [**REQUIREMENTS.md**](./REQUIREMENTS.md) | 要件定義書（全12章、AI/ML要件・データスキーマ含む） | 技術者・審査員 |
| [**ARCHITECTURE.md**](./ARCHITECTURE.md) | システムアーキテクチャ（Mermaid図4枚以上） | 技術者 |
| [**docs/business_context.md**](./docs/business_context.md) | 加和太建設の事業構造・DX現状分析 | ビジネス担当者 |
| [**data/mock_data_generator.py**](./data/mock_data_generator.py) | 7テーブル分のリアルなダミーデータ生成 | 技術者 |

---

## 🛠️ 技術スタック

| レイヤー | 技術 | 選定理由 |
| :--- | :--- | :--- |
| **データウェアハウス** | Google BigQuery | GWSエコシステムとのシームレスな統合。サーバーレスでスケーラブル |
| **機械学習** | Vertex AI (AutoML / Custom) | 原価着地予測（XGBoost）、異常検知（Isolation Forest）の迅速な構築 |
| **自然言語生成** | Gemini API | KPI変動の自動要約 → 経営陣への週次レポート配信 |
| **可視化** | Looker Studio | 無料で高品質なBIダッシュボード。BigQueryネイティブ接続 |
| **データ入力** | AppSheet + Google Sheets | ノーコードで現場担当者が使えるUI。GWS認証で即座に展開可能 |
| **オーケストレーション** | Cloud Functions + Cloud Scheduler | サーバーレスETL。バッチ処理・アラート発報の自動化 |
| **既存連携** | IMPACT CONSTRUCTION API | 加和太建設の自社SaaSからの確定原価データ取得（既存資産活用） |

---

## 🚀 クイックスタート

### ダミーデータの生成

```bash
# リポジトリのクローン
git clone https://github.com/your-username/kawata-construction-dx-poc.git
cd kawata-construction-dx-poc

# 依存パッケージのインストール
pip install pandas numpy python-dateutil

# ダミーデータ生成
python data/mock_data_generator.py

# 生成されるCSV:
# data/projects_master.csv      (50件の工事データ)
# data/cost_records.csv         (500-800件の原価データ)
# data/cash_in_schedules.csv    (入金スケジュール)
# data/real_estate_properties.csv (不動産物件)
# data/facility_operations.csv  (施設運営月次データ)
# data/saas_metrics.csv         (SaaS KPI月次データ)
# data/area_indicators.csv      (エリア指標月次データ)
```

---

## 📊 期待される成果

| 指標 | 改善前 | 改善後 | インパクト |
| :--- | :--- | :--- | :--- |
| 経営数値把握 | 1〜2ヶ月後 | リアルタイム | 意思決定の高速化 |
| 赤字現場の検知 | 完工時に判明 | 工期中間で予測 | **年間0.8〜1.6億円の損失回避** |
| 全社粗利率 | 12%（推定） | 13-14%（目標） | **年間1.57〜3.14億円** |
| レポート作成工数 | 40時間/月 | 10時間/月 | ▲75%削減 |

---

## 📝 分析データ
<img width="1584" height="1142" alt="Unknown-2" src="https://github.com/user-attachments/assets/e32fe708-e88a-4566-ab0c-ba6b2a577d4a" />

<img width="1384" height="1184" alt="Unknown-5" src="https://github.com/user-attachments/assets/90015b86-5348-4c65-8652-932c63677f0f" />


<img width="1147" height="526" alt="Unknown-6" src="https://github.com/user-attachments/assets/1ea49b1f-45dd-4785-bd71-72d889545774" />

<img width="1383" height="982" alt="Unknown-7" src="https://github.com/user-attachments/assets/1887afc3-9148-4d01-9153-d46d6146490d" />

<img width="1095" height="784" alt="Unknown-8" src="https://github.com/user-attachments/assets/8000806b-e475-4361-a12d-499578494511" />

<img width="752" height="565" alt="スクリーンショット 2026-08-03 9 07 13" src="https://github.com/user-attachments/assets/46e56fd9-435c-4032-b711-b3b2bb32a808" />

◻️レポート
週次経営サマリーレポート
1. 全体業績サマリー
売上予測: 45億円（目標達成率: 95.5%）
目標達成に向けて堅調に推移していますが、残り4.5%のギャップを埋める施策が必要です。
2. 各事業部の概況
建設事業: 売上32億円。主力事業として安定して貢献。
不動産事業: 売上8億円。
SaaS事業: 売上3億円。MRR2,500万円、チャーンレート1.2%と健全な成長を維持。
施設運営: 売上2億円。先月来場者数12,500人、稼働率88.5%と好調。
3. キャッシュフローの見通し
現在の現預金残高は15億円。
向こう3ヶ月は全体としてプラス推移の見込みですが、9月は大型支払いの影響で2,000万円の単月赤字が予想されます。
4. 推奨アクション
9月の資金繰りについて、早急に支払いスケジュールの調整または短期資金の手当てを確認してください。
SaaS事業の新規獲得（5件）の成功要因を分析し、更なる成長投資を検討してください。

リスクアラートレポート (Mock)
1. 原価超過リスク（要注意プロジェクト）
高リスクプロジェクト数: 3件（合計リスク金額: 1.2億円）
🚨 三島駅前再開発プロジェクト
現在の原価率: 105.2%
課題: 資材価格の高騰による原価悪化
影響: 全体利益を大きく圧迫する可能性あり。
2. キャッシュフローの警告
🚨 2026年9月 キャッシュフロー悪化見込み
大型工事の支払いが先行するため、単月で2,000万円の赤字（資金流出）となる見込みです。
3. リスク軽減策（AI提案）
調達の見直し: 三島駅前プロジェクトについて、代替資材の検討や協力業者との価格交渉を即時実施。
支払い条件の最適化: 9月に集中している支払いのうち、分割可能なものがないか交渉。

エリアROI分析レポート (Mock)
1. エリア投資の現状（三島・沼津・函南）
施設運営事業: 先月来場者数12,500人、稼働率88.5%と非常に高く、地域住民・観光客の双方を取り込めており、エリア投資の回収は順調です。
SaaS事業: 建設業向けSaaSは地域建設ネットワークを通じて着実に普及（新規5件獲得、解約率1.2%）しており、IT面からの地域貢献と収益化を両立しています。
2. 総合評価と洞察
加和太建設が掲げる「元気をつくる」というミッションは、リアルな場（施設運営）とデジタル（SaaS）の掛け合わせにより、三島周辺エリアで高い相乗効果（ROI）を生み出しています。
3. 今後の方向性
施設来場者のデータをSaaSや不動産開発に活かすクロスセル戦略の検討を推奨します。

---

## 📝 背景・思考プロセス

本プロジェクトの着想から設計に至る思考プロセスは、noteで詳しく解説予定です。


---
## 🤖 AIをパートナーにした開発プロセス（AI-Driven PoC）

本プロジェクトは、生成AI（LLM）を「共同開発パートナー・データエンジニア」として活用し、企画構想・データ設計・BigQuery SQL構築・Looker Studioダッシュボード設計・Pythonスクリプト作成までを包括的に実施した建設DXのPoC（概念実証）です。

* **データモデリング＆SQL作成**: データ構造の設計および分析ビュー（6種）のクエリ自動生成・最適化
* **データ生成＆処理**: Pythonによる疑似ビジネスデータの自動生成スクリプト作成およびColab環境での処理
* **UI/UX設計**: Looker Studioにおける効率的な指標（KPI）配置や可視化手順の導出

---

## ⚠️ 免責事項（Disclaimer）

本リポジトリに含まれるコード、データ、設計書、およびダッシュボード構成は、**個人のポートフォリオ・技術検証（PoC）目的で作成された架空のサンプル**です。

* 実在する加和太建設株式会社様およびその他の関連企業様・団体とは**一切関係ありません**。
* 使用している数値データ（売上、原価、キャッシュフロー等）はすべてスクリプトによって自動生成された**ダミーデータ**であり、実際の企業の財務・事業データを示すものではありません。

## 👤 Author

**[Tsunoda]**
- CRMマーケター  データストラテジスト / データサイエンティスト
- SIGNATEブートキャンプ修了 / まなびDXクエスト受講予定

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

> **本プロジェクトは、ポートフォリオとして作成したものです。**
