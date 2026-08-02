# 要件定義書：加和太建設向け「多角化経営DXコックピット」PoC

> Document Version: 2.0  
> Last Updated: 2026-07-22  
> Author: [Your Name] — Data Strategist  
> Status: Draft for Review  
> Repository: [kawata-construction-dx-poc](https://github.com/your-username/kawata-construction-dx-poc)

---

## 目次

1. [プロジェクト概要](#1-プロジェクト概要)
2. [対象企業の事業構造理解](#2-対象企業の事業構造理解)
3. [課題分析（AS-IS / TO-BE）](#3-課題分析as-is--to-be)
4. [システム化の範囲（Scope）](#4-システム化の範囲scope)
5. [機能要件（Functional Requirements）](#5-機能要件functional-requirements)
6. [AI / ML要件](#6-ai--ml要件)
7. [データ構造要件（Data Schema）](#7-データ構造要件data-schema)
8. [非機能要件（Non-Functional Requirements）](#8-非機能要件non-functional-requirements)
9. [期待される導入効果（KPI / ROI）](#9-期待される導入効果kpi--roi)
10. [PoC実施計画](#10-poc実施計画)
11. [リスクと対策](#11-リスクと対策)
12. [用語集](#12-用語集)

---

## 1. プロジェクト概要

### 1.1 プロジェクト名

多角化経営DXコックピット ― まちづくりROI × AI予兆検知 統合プラットフォーム PoC

### 1.2 対象企業

加和太建設株式会社（静岡県三島市、売上高157億円、従業員306名）

土木・建築を基幹事業としながら、不動産開発、施設運営（道の駅伊豆ゲートウェイ函南等）、建設DX SaaS事業（IMPACT CONSTRUCTION / SCALE）、起業家支援・エリアマネジメントまで展開する「まちづくり企業」。

### 1.3 背景と課題認識

加和太建設は地方建設業界において突出したDX先進企業であり、以下の基盤を既に構築済みである。

| 既存DX基盤 | 詳細 |
| :--- | :--- |
| Google Workspace | 全社導入済み。Drive / Sheets / GAS / Sitesを業務基盤として活用 |
| IMPACT CONSTRUCTION | 自社開発の施工管理・原価管理クラウドSaaS（外販中） |
| SCALE | 技術ナレッジ共有プラットフォーム |
| DX推進室 | 2023年11月設立。内製開発・AI駆動開発を推進 |
| ICT施工 | ドローン、3Dレーザースキャナ、ICT建機を土木現場に導入 |

したがって、本PoCが取り組むべき課題は「データが取れていない」ことではなく、「多角化した事業群を横断的に統合分析し、経営の意思決定品質を変える」ことにある。

具体的な課題は以下の3領域に集約される。

#### 課題①：多角化事業ポートフォリオの横断的ROI把握の困難

加和太建設の事業は「建設 → 不動産 → 施設運営 → エリアマネジメント」のバリューチェーンとして相互に価値を生み出しているが、各事業の損益は独立して管理されており、「三島エリアへの総投資額に対する総合リターン」を定量的に評価する仕組みがない。

```
例：道の駅伊豆ゲートウェイ函南の建設（建築事業の売上）
    → 周辺地域の集客力向上（エリア価値）
    → 周辺不動産の賃料収入増加（不動産事業の売上）
    → 新規建設案件の受注（土木・建築事業の売上）
    
    この循環的価値創出の全体像を定量化できていない。
```

#### 課題②：建設DXエコシステムのKPI統合管理の不在

自社SaaS（IMPACT CONSTRUCTION / SCALE）の事業成長指標、ON-SITE Xコミュニティの活動実績、スタートアップ連携の成果が散在しており、建設DXエコシステム全体の成長・健全性を一元的にモニタリングする基盤がない。

#### 課題③：確定前予兆データの捕捉と予測精度の高度化

施工現場における口頭発注、資材高騰見込み等の「確定前の予兆データ」は、IMPACT CONSTRUCTIONの確定データと統合されておらず、着地予測の精度にギャップが生じている。また、過去データを活用したAIによる原価超過予測は未実装であり、予防的原価管理には至っていない。

### 1.4 プロジェクト目的

Google Cloudエコシステム（BigQuery / Vertex AI / Looker Studio）を活用し、以下の3つの戦略的価値を統合的に実現するデータ基盤を構築する。

| 戦略方向 | 提供価値 | 対象ユーザー |
| :--- | :--- | :--- |
| A. まちづくりROI可視化 | 多角化事業の横断ROI追跡と相乗効果の定量化 | 経営陣・経営企画 |
| B. DXエコシステム可視化 | SaaS事業・コミュニティKPIの統合ダッシュボード | 経営陣・DX推進室 |
| C. AI予兆検知・原価予測 | 予兆データを活用した原価超過の事前予測・アラート | 事業部長・現場監督 |

---

## 2. 対象企業の事業構造理解

### 2.1 事業ポートフォリオ全体像

```
┌─────────────────────────────────────────────────────────────────────┐
│                     加和太建設グループ（売上157億円）                    │
├─────────────┬─────────────┬──────────────┬──────────┬───────────────┤
│  土木事業部   │  建築事業部   │  不動産事業部  │ 施設運営  │ DX・SaaS事業  │
│  (基幹)      │  (基幹)      │  (成長)       │ (成長)   │ (育成)        │
│             │             │              │          │              │
│ ・道路      │ ・公共施設   │ ・売買仲介    │ ・道の駅  │ ・IMPACT      │
│ ・橋梁      │ ・商業施設   │ ・賃貸管理    │  函南     │  CONSTRUCTION │
│ ・砂防堰堤  │ ・教育福祉   │ ・リノベ      │ ・ﾌﾞﾙﾜﾘｰ │ ・SCALE       │
│ ・ICT施工   │ ・設計コラボ │ ・コンサル    │ ・未来研  │ ・ON-SITE X   │
│             │             │              │ ・LtG SS │              │
└─────────────┴─────────────┴──────────────┴──────────┴───────────────┘
                    │                │                │
                    ▼                ▼                ▼
              【ものづくり】    【まちづくり】     【しくみづくり】
```

### 2.2 バリューチェーンの循環構造

加和太建設の最大の差別化要因は、建設→不動産→運営→エリア価値→新規受注の循環的バリューチェーンにある。本PoCでは、この循環構造を定量的に可視化するデータモデルを構築する。

```
    ┌────────────────────────────────────────────────────┐
    │                                                    │
    ▼                                                    │
[1.建設工事] ──完工──► [2.不動産開発] ──保有/賃貸──►      │
    │                       │                            │
    │                       ▼                            │
    │                 [3.施設運営]                        │
    │                  (道の駅/ﾌﾞﾙﾜﾘｰ)                   │
    │                       │                            │
    │                       ▼                            │
    │              [4.エリア価値向上]                      │
    │               (集客↑ 地価↑ 人口↑)                   │
    │                       │                            │
    │                       ▼                            │
    │              [5.新規案件・投資機会]──────────────────┘
    │
    └──── [6.DXナレッジ蓄積] ──► [SaaS外販 / コミュニティ拡大]
```

---

## 3. 課題分析（AS-IS / TO-BE）

### 3.1 領域A：多角化経営のデータ統合

| 項目 | AS-IS（現状） | TO-BE（本システム導入後） |
| :--- | :--- | :--- |
| 事業別損益把握 | 各事業部が個別にP/L管理。グループ全体の事業ポートフォリオ分析は四半期ごとの手動集計。 | BigQueryに全事業データを統合し、リアルタイムで事業別・エリア別の損益をクロス分析可能に。 |
| まちづくりROI | 個別事業の投資回収は把握可能だが、「エリアへの総投資 vs 総リターン（建設受注＋不動産収益＋施設売上＋エリア価値向上）」の統合ROIは未計測。 | エリア単位のROIダッシュボードにより、三島・沼津・函南など地域ごとの投資対効果を横断的に可視化。 |
| 相乗効果の定量化 | 「道の駅が集客に効いている」等の定性的な認識のみ。 | 施設来場者数 → 周辺不動産稼働率 → 新規受注件数の相関分析・回帰分析を自動化し、因果関係を数値化。 |

### 3.2 領域B：DXエコシステムのKPI管理

| 項目 | AS-IS（現状） | TO-BE（本システム導入後） |
| :--- | :--- | :--- |
| SaaS事業KPI | IMPACT CONSTRUCTIONのMRR・顧客数・チャーンレートは社内報告ベースで個別管理。 | SaaS Growth DashboardにてMRR推移、LTV/CAC比率、Net Revenue Retentionを自動算出・可視化。 |
| コミュニティ活動指標 | ON-SITE Xの参加者数・イベント実績は手動集計。ナレッジ共有（SCALE）の利用実態も定量化されていない。 | コミュニティ指標（参加社数、イベント開催数、マッチング成約数）をKPIとして統合モニタリング。 |
| DX投資対効果 | DX推進室の活動成果は定性報告が中心。 | DX施策ごとの投入コスト vs 効果（工数削減時間、SaaS売上、受賞実績等）をDX-ROIとして計測。 |

### 3.3 領域C：原価管理の高度化

| 項目 | AS-IS（現状） | TO-BE（本システム導入後） |
| :--- | :--- | :--- |
| 原価捕捉 | IMPACT CONSTRUCTIONで確定原価は管理。ただし口頭発注・資材高騰見込み等の「予兆データ」は基幹システム外で管理。 | 予兆データ入力UIを構築し、確定原価と予兆原価を統合した実効原価率をリアルタイム算出。 |
| 着地予測 | 実績ベースの線形外挿。季節性・工種特性・外部要因は考慮されていない。 | Vertex AI AutoMLによる機械学習ベースの原価着地予測。天候・資材価格指数・外注先稼働状況を特徴量として取り込み。 |
| 資金繰り予測 | 工事別の入出金予定は管理しているが、全社キャッシュフローの統合予測とリスク検知は未実装。 | 入出金パターンの時系列分析により、資金ショートリスクを60日前にアラート。 |

---

## 4. システム化の範囲（Scope）

### 4.1 PoC対象範囲

```
Phase 1（本PoC）：     土木事業部 × 不動産事業部 × 施設運営（道の駅函南）
Phase 2（拡張）：       建築事業部 × 全施設運営 × SaaS事業
Phase 3（全社展開）：   全事業部 × エリアマネジメント × グループ会社統合
```

### 4.2 システム構成概要

```
[データソース層]                [データ基盤層]              [分析・AI層]           [可視化・配信層]
                                                                                 
┌──────────────┐              ┌──────────────┐            ┌─────────────┐        ┌──────────────┐
│ IMPACT       │──API連携───► │              │            │ Vertex AI   │        │ Looker       │
│ CONSTRUCTION │              │              │───────────►│ AutoML      │──予測─►│ Studio       │
└──────────────┘              │              │            │ (原価予測)   │        │              │
┌──────────────┐              │   BigQuery   │            └─────────────┘        │ ・全社サマリー │
│ Google       │──自動取込───►│              │            ┌─────────────┐        │ ・まちROI     │
│ Sheets       │              │ ・construction│           │ Anomaly     │        │ ・DXエコ      │
│(不動産/施設)  │              │ ・real_estate │───────────►│ Detection   │──検知─►│ ・AI予測      │
└──────────────┘              │ ・facility   │            │ (CF異常検知)  │       │ ・アラート     │
┌──────────────┐              │ ・saas       │            └─────────────┘        └──────┬───────┘
│ AppSheet     │──即時反映───►│ ・area_mgmt  │            ┌─────────────┐               │
│(予兆入力)     │              │ ・cross_view │           │ Gemini API  │               │
└──────────────┘              │              │───────────►│ (NLレポート  │───自動配信───►│
┌──────────────┐              │              │            │  生成)       │        ┌─────┴──────┐
│ 外部データ    │──定期取込───►│              │            └─────────────┘        │ Gmail /    │
│(天候/資材価格) │              └──────────────┘                                   │ Chat通知   │
└──────────────┘                     ▲                                           └────────────┘
                              ┌──────┴───────┐
                              │Cloud Functions│
                              │+ Scheduler    │
                              │(ETL/バッチ)    │
                              └──────────────┘
```

### 4.3 既存システムとの関係

| 既存システム | 本PoCとの関係 | 連携方式 |
| :--- | :--- | :--- |
| IMPACT CONSTRUCTION | 工事マスタ・確定原価データのソース。置き換えない | REST API / データエクスポート |
| Google Workspace | 認証基盤・データ入力基盤として活用 | ネイティブ統合 |
| Jobcan | 勤怠データとの連携（Phase 2以降） | API（Phase 2） |

> 設計方針： 既存の業務システム（特にIMPACT CONSTRUCTION）を補完・拡張する位置づけであり、既存の業務フローを破壊しない。「車輪の再発明」を避け、既存資産の上にデータ統合・AI分析レイヤーを積む。

---

## 5. 機能要件（Functional Requirements）

### F-01：全社経営コックピット（Looker Studio）

#### F-01-1：グループ全社サマリー画面

- グループ全体の売上高、営業利益、営業利益率、従業員一人当たり売上高をKPIカードで表示
- 事業部別の売上構成比（ドーナツチャート）+ 前年同期比トレンド
- 全社キャッシュポジション（手元資金残高）のリアルタイム表示
- 事業ポートフォリオマトリクス（横軸: 売上成長率、縦軸: 営業利益率）による各事業の位置づけ可視化

#### F-01-2：エリア別まちづくりROIダッシュボード

- エリア単位（三島 / 沼津 / 函南 / その他）の投資総額 vs リターン総額のROI推移
- ROI計算式:

$$\text{エリアROI} = \frac{\text{建設売上} + \text{不動産収益} + \text{施設運営利益} + \text{エリア価値変動}}{\text{当該エリアへの総投資額}} \times 100$$

- 各エリアのバリューチェーン連鎖図（建設工事件数 → 施設来場者数 → 不動産稼働率 → 地価変動の相関）
- エリア別の将来投資効果予測（回帰分析ベース）

#### F-01-3：事業部別損益管理画面

##### 土木・建築事業

- 収益認識基準に基づく当月売上・原価・粗利の表示
- 工事別の「当初予算」vs「確定原価 + 予兆原価」の差異分析（ウォーターフォールチャート）
- 原価超過リスクスコア（AI算出）による工事一覧のヒートマップ表示
- 工種別の原価構成比率（外注費 / 材料費 / 労務費 / 経費）の時系列推移

##### 不動産事業

- 物件ポートフォリオ一覧（稼働率・利回り・築年数マトリクス）
- 月次賃貸収入推移 + 空室率トレンド
- 物件取得価額 vs 時価評価の含み損益

##### 施設運営事業

- 施設別の来場者数・売上・営業利益の月次推移
- 季節性分析（前年同月比・移動平均）
- 顧客単価トレンドとキャパシティ稼働率

#### F-01-4：キャッシュフロー予測画面

- 向こう6ヶ月間の全社キャッシュフロー予測（入金 / 出金 / 純残高）
- 建設事業特有の入金パターン（前払金40% / 中間金20% / 完成金40%）の可視化
- 一時的な手元資金低下ゾーンの視覚的アラート（黄色: 注意 / 赤色: 危険）
- 「もしシナリオ」機能：主要工事の入金遅延を仮定した場合のインパクトシミュレーション

### F-02：DXエコシステムダッシュボード

#### F-02-1：SaaS事業KPIパネル

- IMPACT CONSTRUCTION / SCALE のMRR（月次定期収益）推移グラフ
- SaaS健全性指標:

$$\text{LTV/CAC比率} = \frac{\text{ARPU} \times \text{平均契約月数}}{\text{顧客獲得コスト}}$$

$$\text{Net Revenue Retention} = \frac{\text{既存顧客MRR} + \text{Expansion} - \text{Churn} - \text{Contraction}}{\text{前月既存顧客MRR}} \times 100$$

- 顧客数推移、チャーンレート、新規獲得数の月次トラッキング

#### F-02-2：コミュニティ・エコシステム指標パネル

- ON-SITE Xコミュニティ: 参加企業数、イベント開催数、スタートアップマッチング成約数
- SCALE: アクティブユーザー数、ナレッジ投稿数、閲覧数
- LtG Startup Studio: 入居スタートアップ数、資金調達実績

#### F-02-3：DX-ROIトラッカー

- DX施策ごとの投入コスト vs 定量効果のマトリクス表示
- 工数削減効果の累積グラフ（Before/After比較）

### F-03：データ入力・予兆捕捉インターフェース

#### F-03-1：現場予兆原価入力フォーム（AppSheet）

- 現場監督がスマートフォン / PCから入力可能な簡易UI
- 入力項目:
  - 工事ID（プルダウン選択）
  - コスト区分（外注費 / 材料費 / 労務費 / 経費）
  - 予兆種別（口頭発注 / 資材高騰見込み / 追加工事見込み / 手戻り発生）
  - 概算金額（千円）
  - 確度レベル（高: 80%以上 / 中: 50-80% / 低: 50%未満）
  - 備考（自由記述）
- 入力データはBigQueryに即時反映
- 予兆→確定への状態遷移ワークフロー（現場入力 → 事業部長承認 → 確定計上）

#### F-03-2：不動産・施設運営データ入力画面（Google Sheets + GAS）

- 月次の賃貸収入実績、施設来場者数、売上データの入力テンプレート
- GASによる入力バリデーションとBigQueryへの自動同期

### F-04：アラート・通知機能

#### F-04-1：原価超過リスクアラート

- リスクスコア（AI算出）が閾値を超過した工事に対し、自動でGoogle Chat / Gmail通知
- アラートレベル:

| レベル | 条件 | 通知先 |
| :---: | :--- | :--- |
| 🟡 注意 | 実効原価率が目標値の95%に到達 | 現場監督 |
| 🟠 警告 | 実効原価率が目標値を超過 or AIリスクスコア ≥ 0.7 | 現場監督 + 事業部長 |
| 🔴 緊急 | 実効原価率が目標値+5%を超過 or AIリスクスコア ≥ 0.9 | 事業部長 + 経営陣 |

- 目標原価率は工種別に設定（一律閾値ではない）:

| 工種 | 目標原価率 | 根拠 |
| :--- | :---: | :--- |
| 土木（官公庁） | 88% | 低マージン・安定案件 |
| 土木（民間） | 85% | 価格交渉余地あり |
| 建築（公共施設） | 86% | 設計変更リスクを考慮 |
| 建築（民間商業） | 82% | 高付加価値案件 |

#### F-04-2：キャッシュフローアラート

- 30日/60日/90日先の予測残高が安全水準を下回る場合に警告
- 入金遅延の自動検知（予定日を7日超過した未入金に対するフラグ）

#### F-04-3：経営サマリー自動配信

- Gemini APIによる週次経営サマリーの自然言語レポート自動生成
- 生成内容: KPIの変動要因、注目すべき工事、アラート一覧のダイジェスト
- 毎週月曜8:00に経営陣・事業部長へGmail自動送信

---

## 6. AI / ML要件

### 6.1 原価着地予測モデル

#### 目的

工事進行途中の段階で、完工時の最終原価率を予測し、赤字リスクを事前に検知する。

#### モデル設計

| 項目 | 仕様 |
| :--- | :--- |
| 予測対象 | 工事完了時の最終原価率（回帰問題） |
| 学習データ | 過去3年間の完工済み工事データ（約150件想定） |
| 特徴量 | 下表参照 |
| アルゴリズム候補 | XGBoost / LightGBM / Prophet（時系列要素含む場合） |
| 実装環境 | Vertex AI AutoML Tables または Custom Training |
| 更新頻度 | 月次でモデル再学習（新規完工データの追加） |
| 評価指標 | RMSE、MAPE、適合率@赤字検知 |

#### 特徴量設計

| カテゴリ | 特徴量 | 型 | 取得元 |
| :--- | :--- | :--- | :--- |
| 工事属性 | 工種（土木/建築） | カテゴリカル | projects_master |
| | 発注者区分（官公庁/民間） | カテゴリカル | projects_master |
| | 請負金額 | 連続値 | projects_master |
| | 工期（月数） | 連続値 | projects_master |
| 進捗状況 | 工期進捗率（経過月数/全工期） | 連続値 | 算出 |
| | 原価消化率（累計原価/予算） | 連続値 | cost_records |
| | 予兆原価率（予兆原価/総予算） | 連続値 | cost_records |
| 原価構成 | 外注費比率 | 連続値 | cost_records |
| | 材料費比率 | 連続値 | cost_records |
| | 確定/見込みの比率 | 連続値 | cost_records |
| 外部環境 | 月間降水日数 | 連続値 | 気象庁API |
| | 鉄鋼価格指数（前月比） | 連続値 | 日経指数 |
| | 生コン価格指数 | 連続値 | 業界統計 |
| 時間特徴 | 月（季節性） | カテゴリカル | 算出 |
| | 年度（トレンド） | 連続値 | 算出 |

#### 出力仕様

```json
{
  "project_id": "PRJ-2026-042",
  "predicted_final_cost_rate": 0.912,
  "prediction_interval_lower": 0.885,
  "prediction_interval_upper": 0.939,
  "risk_score": 0.78,
  "risk_level": "WARNING",
  "top_risk_factors": [
    {"factor": "外注費消化ペース", "contribution": 0.35},
    {"factor": "資材価格高騰", "contribution": 0.28},
    {"factor": "予兆原価の増加", "contribution": 0.22}
  ],
  "prediction_timestamp": "2026-07-22T09:00:00+09:00"
}
```

### 6.2 キャッシュフロー異常検知モデル

#### 目的

入出金パターンの季節性・トレンドを学習し、異常な資金変動を早期に検知する。

| 項目 | 仕様 |
| :--- | :--- |
| 検知対象 | 月次キャッシュフローの異常偏差 |
| アルゴリズム | Isolation Forest（初期）→ LSTM（Phase 2で高度化） |
| 特徴量 | 月次入金額、月次出金額、入出金比率、季節指標、進行中工事数 |
| 出力 | 異常スコア（0-1）、異常フラグ（閾値: 0.8以上で異常と判定） |
| アクション | 異常検知時にGoogle Chatへ自動通知 + ダッシュボード上でハイライト |

### 6.3 自然言語レポート生成

#### 目的

KPIの変動を自動要約し、経営陣が数字を読み解く負担を軽減する。

| 項目 | 仕様 |
| :--- | :--- |
| 生成エンジン | Gemini API (gemini-2.0-flash) |
| 入力 | BigQueryから取得した週次KPIサマリー + 前週比変動データ |
| 出力 | 日本語300-500字の経営サマリーテキスト |
| 配信 | 毎週月曜 08:00 にGmail / Google Chat配信 |

#### プロンプト設計（例）

```
あなたは加和太建設の経営企画担当AIアシスタントです。
以下のKPIデータに基づき、経営陣向けの週次サマリーを生成してください。

【報告形式】
1. 今週のハイライト（良いニュース1-2件）
2. 注意事項（リスクや懸念1-2件）
3. 推奨アクション（具体的な意思決定の示唆1件）

【トーン】簡潔・事実ベース・アクション指向
【データ】{kpi_json}
```

---

## 7. データ構造要件（Data Schema）

### 7.1 BigQuery データセット構成

```
kawata_dx_cockpit (プロジェクト)
├── construction          # 建設事業データセット
│   ├── projects_master   # 工事マスタ
│   ├── cost_records      # 原価トランザクション
│   ├── cash_in_schedules # 入金スケジュール
│   └── cash_out_schedules # 出金スケジュール
├── real_estate           # 不動産事業データセット
│   ├── properties        # 物件マスタ
│   ├── rental_income     # 賃貸収入実績
│   └── property_transactions # 売買取引
├── facility_ops          # 施設運営データセット
│   ├── facilities        # 施設マスタ
│   └── monthly_operations # 月次運営実績
├── saas_metrics          # SaaS事業データセット
│   ├── product_kpis      # プロダクトKPI
│   └── customer_master   # 顧客マスタ
├── area_management       # エリアマネジメントデータセット
│   └── area_indicators   # エリア指標
├── ai_outputs            # AI出力データセット
│   ├── cost_predictions  # 原価予測結果
│   ├── anomaly_scores    # 異常検知スコア
│   └── nl_reports        # 生成レポート
└── cross_domain          # 横断分析ビュー
    ├── vw_company_summary      # 全社サマリービュー
    ├── vw_area_roi             # エリアROIビュー
    └── vw_portfolio_matrix     # 事業ポートフォリオビュー
```

### 7.2 主要テーブル定義

#### 【construction.projects_master】工事マスタ

| カラム名 | 型 | 説明 |
| :--- | :--- | :--- |
| `project_id` | STRING (PK) | 工事ID（例: PRJ-2026-001） |
| `project_name` | STRING | 工事名称 |
| `division` | STRING | 事業区分（土木 / 建築） |
| `client_type` | STRING | 発注者区分（官公庁 / 民間） |
| `client_name` | STRING | 発注者名 |
| `contract_amount` | INT64 | 請負契約金額（千円） |
| `estimated_cost` | INT64 | 当初見積原価（千円） |
| `target_cost_rate` | FLOAT64 | 目標原価率 |
| `start_date` | DATE | 工期開始日 |
| `end_date` | DATE | 工期終了日 |
| `progress_rate` | FLOAT64 | 進捗率（0.0-1.0） |
| `status` | STRING | ステータス（未着工 / 進行中 / 完了 / 中止） |
| `area` | STRING | エリア（三島 / 沼津 / 函南 / その他） |
| `created_at` | TIMESTAMP | レコード作成日時 |
| `updated_at` | TIMESTAMP | レコード更新日時 |

#### 【construction.cost_records】原価トランザクション

| カラム名 | 型 | 説明 |
| :--- | :--- | :--- |
| `record_id` | STRING (PK) | レコードID |
| `project_id` | STRING (FK) | 工事ID |
| `category` | STRING | コスト区分（外注費 / 材料費 / 労務費 / 経費） |
| `amount` | INT64 | 金額（千円） |
| `status` | STRING | ステータス（確定請求 / 現場見込み / 口頭発注） |
| `confidence_level` | STRING | 確度（高 / 中 / 低）※ status≠確定請求 の場合 |
| `accrual_month` | STRING | 計上対象月（YYYY-MM） |
| `payment_due_month` | STRING | 支払予定月（YYYY-MM） |
| `vendor_name` | STRING | 取引先名 |
| `input_timestamp` | TIMESTAMP | 入力日時 |
| `confirmed_timestamp` | TIMESTAMP | 確定日時（NULL許容） |
| `input_user` | STRING | 入力者（Googleアカウント） |
| `approved_by` | STRING | 承認者（NULL許容） |
| `note` | STRING | 備考 |

#### 【construction.cash_in_schedules】入金スケジュール

| カラム名 | 型 | 説明 |
| :--- | :--- | :--- |
| `schedule_id` | STRING (PK) | スケジュールID |
| `project_id` | STRING (FK) | 工事ID |
| `milestone` | STRING | 区分（前払金 / 中間金 / 完成金 / その他） |
| `milestone_ratio` | FLOAT64 | 契約金額に対する比率 |
| `expected_amount` | INT64 | 入金予定額（千円） |
| `actual_amount` | INT64 | 実入金額（千円、NULL許容） |
| `deposit_month` | STRING | 入金予定月（YYYY-MM） |
| `actual_deposit_date` | DATE | 実入金日（NULL許容） |
| `status` | STRING | ステータス（予定 / 入金済 / 遅延） |

#### 【real_estate.properties】物件マスタ

| カラム名 | 型 | 説明 |
| :--- | :--- | :--- |
| `property_id` | STRING (PK) | 物件ID |
| `property_name` | STRING | 物件名称 |
| `property_type` | STRING | 種別（賃貸マンション / 商業施設 / オフィス / 土地） |
| `area` | STRING | エリア（三島 / 沼津 / 函南 / その他） |
| `acquisition_date` | DATE | 取得日 |
| `acquisition_cost` | INT64 | 取得価額（千円） |
| `current_value` | INT64 | 時価評価額（千円） |
| `total_units` | INT64 | 総戸数/区画数 |
| `occupied_units` | INT64 | 入居済み/稼働数 |
| `monthly_rental_income` | INT64 | 月額賃貸収入（千円） |
| `annual_maintenance_cost` | INT64 | 年間維持管理費（千円） |

#### 【facility_ops.monthly_operations】月次運営実績

| カラム名 | 型 | 説明 |
| :--- | :--- | :--- |
| `facility_id` | STRING (FK) | 施設ID |
| `facility_name` | STRING | 施設名称 |
| `month` | STRING | 対象月（YYYY-MM） |
| `visitors` | INT64 | 来場者数 |
| `revenue` | INT64 | 売上高（千円） |
| `operating_cost` | INT64 | 運営費用（千円） |
| `operating_profit` | INT64 | 営業利益（千円） |
| `avg_spend_per_visitor` | INT64 | 来場者一人当たり消費額（円） |

#### 【saas_metrics.product_kpis】SaaS事業KPI

| カラム名 | 型 | 説明 |
| :--- | :--- | :--- |
| `month` | STRING | 対象月（YYYY-MM） |
| `product` | STRING | プロダクト名（IMPACT CONSTRUCTION / SCALE） |
| `mrr` | INT64 | 月次定期収益（千円） |
| `total_customers` | INT64 | 有料顧客数 |
| `new_customers` | INT64 | 新規獲得数 |
| `churned_customers` | INT64 | 解約数 |
| `churn_rate` | FLOAT64 | 月次チャーンレート |
| `expansion_mrr` | INT64 | エクスパンションMRR（千円） |
| `arpu` | INT64 | 顧客平均月額（千円） |

#### 【area_management.area_indicators】エリア指標

| カラム名 | 型 | 説明 |
| :--- | :--- | :--- |
| `area_name` | STRING | エリア名（三島 / 沼津 / 函南） |
| `month` | STRING | 対象月（YYYY-MM） |
| `land_price_index` | FLOAT64 | 公示地価指数（基準年=100） |
| `estimated_population` | INT64 | 推計人口 |
| `foot_traffic_index` | FLOAT64 | 歩行者交通量指数 |
| `new_business_count` | INT64 | 新規開業事業所数 |
| `kawata_investment_amount` | INT64 | 加和太建設の当該エリア投資額（千円） |

### 7.3 横断分析ビュー定義（SQL例）

#### vw_area_roi — エリアROI算出ビュー

```sql
CREATE VIEW cross_domain.vw_area_roi AS
WITH construction_revenue AS (
  SELECT area, SUM(contract_amount) AS total_construction_revenue
  FROM construction.projects_master
  WHERE status = '完了'
  GROUP BY area
),
real_estate_revenue AS (
  SELECT p.area, SUM(r.monthly_rental_income)  12 AS annual_rental_income
  FROM real_estate.properties p
  JOIN real_estate.rental_income r ON p.property_id = r.property_id
  GROUP BY p.area
),
facility_revenue AS (
  SELECT f.area, SUM(m.operating_profit) AS total_facility_profit
  FROM facility_ops.facilities f
  JOIN facility_ops.monthly_operations m ON f.facility_id = m.facility_id
  GROUP BY f.area
),
area_investment AS (
  SELECT area_name, SUM(kawata_investment_amount) AS total_investment
  FROM area_management.area_indicators
  GROUP BY area_name
)
SELECT
  ai.area_name,
  ai.total_investment,
  COALESCE(cr.total_construction_revenue, 0) AS construction_revenue,
  COALESCE(rr.annual_rental_income, 0) AS rental_income,
  COALESCE(fr.total_facility_profit, 0) AS facility_profit,
  (COALESCE(cr.total_construction_revenue, 0) 
   + COALESCE(rr.annual_rental_income, 0) 
   + COALESCE(fr.total_facility_profit, 0)) AS total_return,
  SAFE_DIVIDE(
    (COALESCE(cr.total_construction_revenue, 0) 
     + COALESCE(rr.annual_rental_income, 0) 
     + COALESCE(fr.total_facility_profit, 0)),
    ai.total_investment
  )  100 AS area_roi_pct
FROM area_investment ai
LEFT JOIN construction_revenue cr ON ai.area_name = cr.area
LEFT JOIN real_estate_revenue rr ON ai.area_name = rr.area
LEFT JOIN facility_revenue fr ON ai.area_name = fr.area;
```

---

## 8. 非機能要件（Non-Functional Requirements）

### 8.1 パフォーマンス

| 項目 | 要件 |
| :--- | :--- |
| 現場入力の反映速度 | AppSheet入力からBigQuery反映まで5分以内 |
| ダッシュボード描画速度 | Looker Studio各画面の初期表示: 5秒以内 |
| AI予測バッチ | 夜間バッチ（毎日02:00実行）で全進行中工事の予測を更新、30分以内に完了 |
| NLレポート生成 | Gemini APIコール→レポート生成→配信: 3分以内 |

### 8.2 セキュリティ・権限管理

Google WorkspaceのIAM + BigQueryのデータセットレベルアクセス制御により、以下の権限マトリクスを実装する。

| ロール | 全社サマリー | 自事業部損益 | 他事業部損益 | まちづくりROI | DXエコ | AI予測 | データ入力 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 経営陣 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| 経営企画 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| 事業部長 | ✅ | ✅ | 📊(概要のみ) | ✅ | 📊 | ✅(自部門) | ❌ |
| DX推進室 | ✅ | 📊 | 📊 | ✅ | ✅ | ✅(全体) | ❌ |
| 現場監督 | ❌ | 📊(担当工事のみ) | ❌ | ❌ | ❌ | 📊(担当工事) | ✅ |

### 8.3 拡張性・運用性

- 内製対応可能な設計: 画面追加・KPI追加をDX推進室が数時間〜数日で対応可能な構造
- テンプレート化: 新規事業部やグループ会社を追加する際のデータセット・ダッシュボードテンプレートを用意
- ドキュメント化: 全テーブル定義、ETLフロー、AI モデルの仕様をConfluence/GitHub Wikiに文書化

### 8.4 可用性・監視

- データ品質チェック: Cloud Functionsによる日次データ品質バリデーション（欠損率、値域チェック）
- パイプライン監視: Cloud Monitoringによるバッチジョブの成否アラート
- SLA目標: ダッシュボードの可用性 99.5%（月間ダウンタイム ≤ 3.6時間）

---

## 9. 期待される導入効果（KPI / ROI）

### 9.1 定量的効果

| 効果領域 | 現状推定値 | 導入後目標 | 改善幅 | 年間インパクト推定 |
| :--- | :--- | :--- | :--- | :--- |
| 経営判断の高速化 | グループ統合数値の把握に1〜2ヶ月 | リアルタイム（日次更新） | ▲1.5ヶ月 | 意思決定迅速化による機会損失防止（定量化困難） |
| 赤字現場の事前防止 | 着地時に赤字判明（年間2〜3件と仮定） | 工期中間時点での赤字リスク検知 | 検知率 80%以上 | 0.8〜1.6億円の損失回避（注1） |
| 全社粗利率改善 | 粗利率 12%（推定） | 粗利率 13-14% | +1.0〜2.0% | 1.57〜3.14億円の粗利増 |
| 経営企画の工数削減 | 月次報告書作成に延べ40時間/月 | 自動化により10時間/月に | ▲75% | 年間360時間の工数削減 |
| DX投資効果の見える化 | 定性的な報告のみ | 定量的なDX-ROIトラッキング | — | DX予算の適正配分 |

> （注1） 算出根拠: 赤字現場1件あたりの平均損失額を4,000万〜8,000万円と仮定（請負金額5億円×原価超過率8-16%）。AI検知による早期対策で2件/年の赤字回避を想定。

### 9.2 定性的効果

1. まちづくり戦略の高度化: エリア別ROIの定量化により、次の投資先選定の精度向上
2. SaaS事業の成長加速: KPIの可視化により、プロダクト改善サイクルの高速化
3. 組織のデータドリブン文化醸成: 経営陣の意思決定プロセスにデータが組み込まれることで、全社的なデータリテラシーが向上
4. 採用競争力の強化: 先進的なDX基盤の存在が、IT人材・データ人材の採用において差別化要因に

### 9.3 投資対効果（概算）

| 項目 | 金額（概算） |
| :--- | :--- |
| 初期構築コスト（PoC） | 300〜500万円（内製の場合はクラウド利用料+工数） |
| 年間運用コスト | BigQuery: 月額5-10万円、Vertex AI: 月額3-5万円、Looker Studio: 無料 → 年間100〜180万円 |
| 期待リターン | 赤字回避: 0.8〜1.6億円 + 粗利改善: 1.57〜3.14億円 → 年間2.37〜4.74億円 |
| ROI | (投資回収期間: 1〜2ヶ月) |

---

## 10. PoC実施計画

### 10.1 全体スケジュール

```
Phase 1: データ基盤構築        [Week 1-3]  ████████████░░░░░░░░░░░░░░░░░░
Phase 2: AI モデル開発          [Week 3-6]  ░░░░░░░░████████████░░░░░░░░░░
Phase 3: ダッシュボード構築     [Week 5-8]  ░░░░░░░░░░░░░░████████████░░░░
Phase 4: 統合テスト・改善       [Week 8-10] ░░░░░░░░░░░░░░░░░░░░░░████████
```

### 10.2 Phase別タスク

#### Phase 1: データ基盤構築（Week 1-3）

- BigQueryデータセット・テーブル作成
- IMPACT CONSTRUCTION → BigQueryのデータ連携パイプライン構築
- Google Sheets → BigQueryの自動同期設定（GAS + Cloud Functions）
- AppSheetによる予兆入力フォーム構築
- 外部データソース（気象データ・資材価格指数）の取込設定
- ダミーデータによる動作確認

#### Phase 2: AIモデル開発（Week 3-6）

- 探索的データ分析（EDA）
- 特徴量エンジニアリング
- 原価着地予測モデルの学習・評価
- キャッシュフロー異常検知モデルの学習・評価
- Gemini APIによるNLレポート生成のプロンプトチューニング
- モデルのVertex AIへのデプロイ

#### Phase 3: ダッシュボード構築（Week 5-8）

- Looker Studioの各画面設計・実装
- 全社サマリー → エリアROI → 事業部別 → AI予測のドリルダウン導線
- アラートロジックの実装（Cloud Functions → Google Chat / Gmail）
- モバイル対応レイアウトの調整

#### Phase 4: 統合テスト・改善（Week 8-10）

- ユーザー受入テスト（経営陣・事業部長・現場監督の各ロール）
- フィードバック反映・UI改善
- 運用マニュアル作成
- 成果報告会の準備

### 10.3 成功基準（PoC完了条件）

| 基準 | 判定条件 |
| :--- | :--- |
| データ統合 | 3事業部以上のデータがBigQueryに自動連携されている |
| AI予測精度 | 原価着地予測のMAPEが10%以下 |
| ダッシュボード | 5画面以上が構築され、3ロール以上のアクセス制御が機能 |
| アラート | 原価超過リスクアラートが正常に発報される |
| ユーザー評価 | 経営陣・事業部長の満足度が5段階中4以上 |

---

## 11. リスクと対策

| リスク | 影響度 | 発生確率 | 対策 |
| :--- | :---: | :---: | :--- |
| IMPACT CONSTRUCTIONのAPIが公開されていない / 連携制限 | 高 | 中 | CSV/スプレッドシートエクスポートによる代替連携。DX推進室との事前協議 |
| 学習データ量の不足（完工実績150件未満） | 中 | 中 | 特徴量を絞った軽量モデルの採用。合成データによるデータ拡張の検討 |
| 現場監督の予兆入力が定着しない | 高 | 高 | 入力UIの極限までの簡素化（3タップで完了）。入力実績の可視化によるゲーミフィケーション |
| 外部データソースの取得コスト・遅延 | 低 | 中 | 初期は無料の公開データ（気象庁等）のみ使用。有料データは効果検証後に導入判断 |
| 経営陣のダッシュボード活用が習慣化しない | 中 | 中 | Gemini APIによるプッシュ型レポート配信で「見に来なくても届く」仕組みを構築 |

---

## 12. 用語集

| 用語 | 定義 |
| :--- | :--- |
| 収益認識基準 | 工事の進行に応じて売上を計上する会計基準（2021年4月適用開始の「収益認識に関する会計基準」に準拠。旧「工事進行基準」を包含） |
| 実効原価率 | （確定発生原価 + 予兆原価 × 確度加重）÷ 完成予想総原価 |
| 予兆データ | 請求書確定前の段階で現場から報告される見込み原価（口頭発注、資材高騰見込み等） |
| MRR | Monthly Recurring Revenue（月次定期収益）。SaaS事業の主要KPI |
| チャーンレート | 一定期間内に解約した顧客の割合 |
| LTV/CAC比率 | 顧客生涯価値 ÷ 顧客獲得コスト。3.0以上が健全な水準 |
| Net Revenue Retention | 既存顧客からの収益維持率。100%超がヘルシー（拡張収益がチャーンを上回る） |
| エリアROI | 特定地域への総投資額に対する、建設・不動産・施設運営の総リターンの比率 |
| IMPACT CONSTRUCTION | 加和太建設が自社開発したクラウド型施工管理・原価管理SaaS |
| SCALE | 加和太建設が開発した技術ナレッジ共有プラットフォーム |
| ON-SITE X | 加和太建設が運営する建設DXコミュニティ |

---

## 付録

### A. 参考文献・データソース

1. 加和太建設株式会社 公式ウェブサイト
2. 国土交通省「建設業の経理に関する実務指針」
3. 企業会計基準委員会「収益認識に関する会計基準」（企業会計基準第29号）
4. 気象庁 過去の気象データ API
5. 一般財団法人建設物価調査会「建設物価指数」

### B. 関連ドキュメント

- [business_context.md](./docs/business_context.md) — 加和太建設の事業構造分析
- [ARCHITECTURE.md](./ARCHITECTURE.md) — システムアーキテクチャ設計書
- [data/mock_data_generator.py](./data/mock_data_generator.py) — ダミーデータ生成スクリプト
- [analysis/](./analysis/) — 探索的データ分析・AIモデル構築ノートブック

---

> 本要件定義書は、まなびDXクエスト 地域企業協働プログラムへの応募に際し、加和太建設株式会社のDX課題に対するデータストラテジストとしての提案を文書化したものです。
>
> © 2026 [Your Name]. This document is part of the kawata-construction-dx-poc portfolio.
