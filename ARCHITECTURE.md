# 加和太建設 マルチドメインDXコックピット PoC システムアーキテクチャ設計書

## 1. アーキテクチャ概要
加和太建設（建設、不動産、施設運営、SaaS、エリアマネジメント）の多様な事業領域のデータを統合し、データドリブンな経営判断を支援する「マルチドメインDXコックピット」のアーキテクチャ設計です。既存のGoogle Workspace環境を最大限に活用し、Google Cloud（GCP）のデータ基盤・AIサービスを中核としたスケーラブルな構成を採用しています。

本アーキテクチャは、以下の3つの戦略的テーマの実現を目的としています：
1. **まちづくりROI可視化**: 建設、不動産、施設運営を統合したエリア単位の投資対効果の算出
2. **建設DXエコシステム可視化**: 自社SaaS（IMPACT CONSTRUCTION, SCALE）のKPIや利用状況のトラッキング
3. **AI原価予測**: 蓄積された過去データと外部要因を考慮した機械学習による原価予測および異常検知

## 2. システム構成図

### 2.1 全体システムアーキテクチャ
データの発生源から、蓄積、AIによる分析、そして可視化・レポーティングに至るデータフローの全体像です。

```mermaid
graph TD
    %% Data Sources
    subgraph データソース層
        IC[IMPACT CONSTRUCTION]
        SC[SCALE]
        AS[AppSheet<br/>現場入力/予兆データ]
        GW[Google Sheets<br/>不動産/施設運営]
        EX[外部データ<br/>天候/資材価格指数]
    end

    %% Ingestion & Orchestration
    subgraph パイプライン・オーケストレーション層
        CF[Cloud Functions]
        CS[Cloud Scheduler]
        CS -->|トリガー| CF
        IC -.->|API連携| CF
        SC -.->|API連携| CF
        AS -.->|連携| CF
        GW -.->|連携| CF
        EX -.->|API取得| CF
    end

    %% Data Warehouse
    subgraph データ基盤層
        BQ[(BigQuery)]
        CF -->|ELT処理| BQ
    end

    %% AI & ML
    subgraph AI/ML層
        VA[Vertex AI<br/>AutoML / Custom Model]
        GM[Gemini API<br/>自然言語レポート]
        BQ <-->|学習/推論| VA
        BQ -->|プロンプト構築| GM
    end

    %% Visualization
    subgraph 可視化・活用層
        LS[Looker Studio]
        WS[Google Workspace<br/>Docs/Chat通知]
        BQ -->|ダッシュボード| LS
        VA -->|予測結果| BQ
        GM -->|レポート| WS
    end
```

### 2.2 セキュリティ・アクセス制御アーキテクチャ

```mermaid
graph LR
    User[ユーザー]
    Admin[管理者]
    
    subgraph Google Cloud IAM
        Roles[IAM ロール制御]
        DataViewer[データ閲覧者]
        DataEditor[データ管理者]
    end
    
    subgraph BigQuery
        RLS[行レベルセキュリティ]
        CLS[列レベルセキュリティ]
    end
    
    subgraph Looker Studio
        DashboardAccess[ダッシュボード権限]
    end

    User --> DashboardAccess
    DashboardAccess --> DataViewer
    Admin --> DataEditor
    
    DataViewer --> RLS
    DataEditor --> CLS
```

## 3. データソース層

多様な事業ポートフォリオに対応するため、各事業の特性に合わせたデータソースから情報を収集します。

- **IMPACT CONSTRUCTION (API連携)**
  - 建設部門の根幹データ（工事マスタ、実行予算、原価実績、入出金履歴など）をAPI経由で定期取得。
- **Google Sheets (不動産・施設運営データ)**
  - 「道の駅」等の施設運営データ（来場者数、店舗売上）、不動産事業データ（物件情報、賃貸収入）。既存の業務フロー（GAS等の自動化）を活用。
- **AppSheet (現場入力・予兆データ)**
  - 建設現場からの日報、非構造化データの構造化入力、ヒヤリハットやトラブル予兆の定性データを収集。
- **外部データ (External Data)**
  - AI原価予測の精度向上のため、気象庁API（天候・降水量）や建設物価調査会の資材価格指数を自動収集。

## 4. データ基盤層（BigQuery）

事業部ごとのデータサイロを解消し、統合的な分析を可能にするため、BigQuery上に論理的なデータセットを構築します。

| データセット名 | 用途・格納データ |
|---|---|
| `construction` | 工事マスタ、実行予算、実績原価、入出金トラッキング |
| `real_estate` | 物件マスタ、テナント情報、賃貸収入実績、不動産取引データ |
| `facility_ops` | 道の駅等の施設別来場者数、POS売上データ、顧客セグメント |
| `saas_metrics` | IMPACT CONSTRUCTION / SCALEのユーザー数、MRR、チャーンレート、機能利用頻度 |
| `area_management` | 特定エリアごとの事業横断指標、地域人口動態、地価推移、地域イベント効果 |
| `cross_domain` | まちづくりROIや全社KPI集約用の中間テーブル・データマート。Looker Studioの直接の参照先 |

## 5. AI/ML層（Vertex AI）

蓄積されたデータを価値に変えるための3つのAI機能を実装します。

1. **原価着地予測モデル (AutoML / Custom Models)**
   - **目的**: プロジェクト完了時の最終原価を高精度に予測
   - **アルゴリズム**: XGBoost または Prophet（時系列性重視）
   - **特徴量**: 過去の類似工事実績、進捗率、天候データ、最新の資材価格指数
2. **キャッシュフロー異常検知**
   - **目的**: 予算消化の急激な変動や、不自然な経費計上を早期発見
   - **アルゴリズム**: Isolation Forest または LSTMベースの時系列異常検知
3. **自然言語レポート生成 (Gemini API)**
   - **目的**: 経営陣向けの月次/週次の事業ハイライト自動生成
   - **処理**: BigQueryの集計結果と予実差異をプロンプトに埋め込み、Geminiにより要約テキストやアラート文章を生成し、Google ChatやDocsへ配信。

## 6. 可視化層（Looker Studio）

経営層から現場のプロジェクトマネージャーまで、役割に応じたインサイトを提供するダッシュボード群です。

- **全社経営サマリー**: 全事業（建設、不動産、SaaS等）の売上・利益サマリーと予実管理。
- **事業部別詳細（ドリルダウン）**: 各事業の主要KPI（例：SaaSのMRR推移、道の駅の客単価など）。
- **まちづくりROIトラッカー**: 特定の地域（例：三島市エリア）における建設投資、施設運営利益、エリア価値向上を統合した指標（ROI）の可視化。
- **AI予測・アラート画面**: Vertex AIが予測した原価超過リスクの高いプロジェクトのランキングと異常検知アラート。

## 7. データパイプライン設計

データの抽出(Extract)、ロード(Load)、変換(Transform)のELTプロセスを定義します。

```mermaid
sequenceDiagram
    participant Source as 各データソース
    participant CF as Cloud Functions
    participant BQ_Raw as BigQuery (Raw)
    participant dbt as dbt / BQ SQL
    participant BQ_Mart as BigQuery (Mart)
    participant AI as Vertex AI

    Note over Source,CF: 毎晩深夜帯にバッチ実行
    CF->>Source: データ抽出リクエスト (API/Sheets)
    Source-->>CF: JSON/CSVデータ応答
    CF->>BQ_Raw: Rawデータとしてロード
    dbt->>BQ_Raw: クレンジング・正規化・結合処理
    dbt->>BQ_Mart: データマート生成 (cross_domain等)
    BQ_Mart->>AI: 学習・推論用データ抽出
    AI-->>BQ_Mart: 予測結果・スコア書き戻し
```

## 8. セキュリティ・権限設計

Google Workspaceの既存グループ権限とGoogle Cloud IAMを統合します。

- **IAM ロール**:
  - `roles/bigquery.dataViewer`: 各部門のアナリスト（自身が所属する事業のデータセットのみアクセス可）
  - `roles/bigquery.admin`: DX推進室データエンジニア
- **行レベル・列レベルセキュリティ (RLS/CLS)**:
  - 建設原価の詳細や個人情報を含む列へのアクセスをDX推進室と経営層のみに制限。
  - Looker Studioの閲覧者のGoogleアカウントに基づき、表示されるデータを所属部門に限定（Row-Level Securityの活用）。

## 9.運用・監視設計

- **ジョブ監視**: Cloud Monitoringを使用し、Cloud Functionsの実行エラーや処理遅延を検知。
- **データ品質監視**: 必須項目のNull率や異常値のチェッククエリを日次で実行し、閾値を超えた場合はGoogle ChatのDX推進室チャンネルへアラート通知。
- **コスト管理**: BigQueryのクエリスキャン量に基づく予算アラートを設定。

## 10. 拡張性・将来構想

本PoCアーキテクチャは、加和太建設社内のDX推進に留まらず、将来的なスケールを前提としています。

1. **マルチテナント化への拡張**:
   将来的には、この「DXコックピット」自体を自社SaaS（IMPACT CONSTRUCTION等）の付加価値機能、あるいは新たなデータSaaSとして他の中堅建設会社へ展開可能な設計とする（BigQueryのデータセット分割やマルチテナントアーキテクチャの導入）。
2. **リアルタイム処理の導入**:
   IoTセンサー（現場の温湿度、重機の稼働状況）からのストリーミングデータをPub/Sub経由で統合し、よりリアルタイムな現場モニタリングを実現。
3. **Generative AIの高度活用**:
   Geminiを活用した社内規定や過去の施工トラブル事例を検索できるRAG（検索拡張生成）チャットボットを統合し、知識共有プラットフォーム「SCALE」の価値を最大化。
