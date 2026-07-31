# カラム辞書（Column Dictionary）
## BigQueryビュー ↔ Looker Studio 日英対照表

> **用途**: Looker Studio のグラフ作成時に、英語カラム名から日本語の意味を素早く確認するための対照表です。

---

## 📊 Page 1: 全社経営サマリー — `vw_company_dashboard`

| カラム名 (BigQuery) | 日本語名 | 型 | 説明 |
|:---|:---|:---:|:---|
| `sales_month` | 月ディメンション | DATE | Looker の時系列軸に使用 |
| `total_sales` | 全社売上 | INT64 | 建設+不動産+施設+SaaSの合算（千円） |
| `actual_sales` | 売上実績（建設） | INT64 | 建設事業の入金ベース売上（千円） |
| `forecast_sales` | 売上予測 | INT64 | 直近3ヶ月移動平均による予測値（千円） |
| `operating_profit_margin` | 営業利益率 | FLOAT64 | (売上 - 原価) ÷ 売上 × 100 (%) |
| `active_project_count` | 進行中工事数 | INT64 | 当月時点で工期内の工事数 |
| `cash_balance` | 手元資金 | INT64 | 累積キャッシュフロー残高（千円） |

**Looker Studio でのグラフ例**:
- スコアカード: `total_sales`, `operating_profit_margin`, `active_project_count`, `cash_balance`
- 折れ線: `sales_month` × (`actual_sales` + `forecast_sales`)
- 棒グラフ: `sales_month` × `total_sales`

---

## 🏘️ Page 2: まちづくりROI — `vw_area_roi` + `vw_area_indicators`

### `vw_area_roi`（エリア別集約）

| カラム名 (BigQuery) | 日本語名 | 型 | 説明 |
|:---|:---|:---:|:---|
| `area` | エリア名 | STRING | 三島/沼津/函南/清水/長泉/伊豆の国/伊豆/その他 |
| `construction_revenue_kpy` | 建設事業売上 | INT64 | エリア内の請負金額合計（千円） |
| `project_count` | 工事件数 | INT64 | エリア内の工事数 |
| `annual_rental_income_kpy` | 不動産年間収入 | INT64 | エリア内の年間賃貸収入（千円） |
| `property_value_kpy` | 不動産時価 | INT64 | エリア内の不動産時価合計（千円） |
| `avg_occupancy_rate` | 平均稼働率 | FLOAT64 | 不動産の平均入居率 (%) |
| `facility_revenue_kpy` | 施設売上 | INT64 | 施設運営事業の売上合計（千円） |
| `facility_profit_kpy` | 施設営業利益 | INT64 | 施設の営業利益合計（千円） |
| `total_visitors` | 来場者合計 | INT64 | 施設の累計来場者数 |
| `total_return_kpy` | 総リターン | INT64 | 建設+不動産+施設の合算売上（千円） |
| `total_investment_kpy` | 投資総額 | INT64 | 建設請負+不動産取得原価の合算（千円） |
| `roi_rate` | ROI率 | FLOAT64 | (総リターン - 投資総額) ÷ 投資総額 × 100 (%) |
| `land_price_index` | 地価指数 | FLOAT64 | エリア平均の地価指数 |
| `population` | 人口 | FLOAT64 | エリア平均の人口 |
| `foot_traffic` | 歩行者交通量 | FLOAT64 | エリア平均の歩行者数 |

### `vw_area_indicators`（エリア指標 月次推移）

| カラム名 (BigQuery) | 日本語名 | 型 | 説明 |
|:---|:---|:---:|:---|
| `area_name` | エリア名 | STRING | 三島/沼津/函南 |
| `indicator_month` | 年月ディメンション | DATE | Looker の時系列軸に使用 |
| `land_price_index` | 地価指数 | FLOAT64 | 月次の地価推移指数 |
| `population` | 人口 | FLOAT64 | 月次の推計人口 |
| `foot_traffic` | 歩行者交通量 | FLOAT64 | 月次の歩行者トラフィック |
| `new_business_count` | 新規事業数 | INT64 | 月内の新規開業数 |
| `event_count` | イベント数 | INT64 | 月内の地域イベント開催数 |

**Looker Studio でのグラフ例**:
- 積み上げ棒: `area` × (`construction_revenue_kpy` + `annual_rental_income_kpy` + `facility_revenue_kpy`)
- スコアカード: `roi_rate` (エリア別)
- 折れ線（時系列）: `indicator_month` × `land_price_index`（`area_name` でフィルタ）

---

## 🏗️ Page 3: 工事原価管理 — `vw_project_cost_summary` + `vw_cost_category_detail`

### `vw_project_cost_summary`（工事別サマリー）

| カラム名 (BigQuery) | 日本語名 | 型 | 説明 |
|:---|:---|:---:|:---|
| `project_id` | 工事ID | STRING | PRJ-0001 形式 |
| `project_name` | 工事名 | STRING | 「三島市道路改良工事」等 |
| `division` | 事業部 | STRING | 土木 / 建築 |
| `client_type` | 発注者 | STRING | 官公庁 / 民間 |
| `pm_name` | プロジェクトマネージャー名 | STRING | 担当PM名 |
| `contract_amount_kpy` | 請負金額 | INT64 | 工事の契約金額（千円） |
| `target_cost_rate` | 目標原価率 | FLOAT64 | 予算上の目標原価率 (%) |
| `progress_rate` | 工事進捗率 | FLOAT64 | 現在の出来高進捗 (%) |
| `project_status` | 工事ステータス | STRING | 未着工/進行中/完了 |
| `start_date` | 着工日 | DATE | 工事開始日 |
| `end_date` | 竣工予定日 | DATE | 工事完了予定日 |
| `confirmed_cost_kpy` | 確定原価 | INT64 | 支払・請求確定済みの原価（千円） |
| `forecast_cost_kpy` | 見込み原価 | INT64 | 現場見込み+口頭発注（千円） |
| `total_cost_kpy` | 総原価 | INT64 | 確定+見込みの合計（千円） |
| `gross_profit` | 粗利 | INT64 | 請負金額 - 総原価（千円） |
| `effective_cost_rate` | 実効原価率 | FLOAT64 | 総原価 ÷ 請負金額 × 100 (%) |
| `cost_rate_gap` | 原価率乖離 | FLOAT64 | 実効原価率 - 目標原価率 (pt) |
| `outsourcing_cost_kpy` | 外注費 | INT64 | 千円 |
| `material_cost_kpy` | 材料費 | INT64 | 千円 |
| `labor_cost_kpy` | 労務費 | INT64 | 千円 |
| `expense_cost_kpy` | 経費 | INT64 | 千円 |
| `outsourcing_ratio` | 外注費比率 | FLOAT64 | % |
| `material_ratio` | 材料費比率 | FLOAT64 | % |
| `labor_ratio` | 労務費比率 | FLOAT64 | % |
| `expense_ratio` | 経費比率 | FLOAT64 | % |
| `risk_level` | リスクレベル | STRING | 緊急/警告/注意/正常 |

### `vw_cost_category_detail`（カテゴリ別予実明細 — ドーナツ・棒グラフ用）

| カラム名 (BigQuery) | 日本語名 | 型 | 説明 |
|:---|:---|:---:|:---|
| `project_id` | 工事ID | STRING | PRJ-0001 形式 |
| `project_name` | 工事名 | STRING | |
| `division` | 事業部 | STRING | 土木/建築 |
| `cost_category` | 原価カテゴリ | STRING | 外注費/材料費/労務費/経費 |
| `category_budget` | カテゴリ別予算原価 | INT64 | 請負金額×目標原価率×標準比率（千円） |
| `category_actual` | カテゴリ別実績原価 | INT64 | 実際の発生原価（千円） |
| `category_variance` | 予実差異 | INT64 | 予算 - 実績（正=余裕、負=超過）（千円） |

**Looker Studio でのグラフ例**:
- テーブル: 全カラムで一覧表（`risk_level` で色分け）
- ドーナツ: `cost_category` × `category_actual`（1工事のカテゴリ構成）
- 予実対比棒: `cost_category` × (`category_budget`, `category_actual`)
- 散布図: `progress_rate` × `effective_cost_rate`（`risk_level` で色分け）

---

## 💰 Page 4: キャッシュフロー — `vw_cashflow_forecast`

| カラム名 (BigQuery) | 日本語名 | 型 | 説明 |
|:---|:---|:---:|:---|
| `cf_date` | キャッシュフロー日付 | DATE | Looker の時系列軸に使用 |
| `month_str` | 年月文字列 | STRING | "2024-01" 形式（ラベル用） |
| `expected_inflow_kpy` | 入金予定 | INT64 | 請求予定の入金額（千円） |
| `actual_inflow_kpy` | 入金実績 | INT64 | 実際の入金額（千円） |
| `total_outflow_kpy` | 出金合計 | INT64 | 原価支出の合計（千円） |
| `confirmed_outflow_kpy` | 確定出金 | INT64 | 確定請求分の出金（千円） |
| `forecast_outflow_kpy` | 見込み出金 | INT64 | 現場見込み+口頭発注分（千円） |
| `net_cashflow_kpy` | 純キャッシュフロー | INT64 | 入金 - 出金（千円） |
| `beginning_balance_kpy` | 期首残高 | INT64 | 月初時点の累積残高（千円） |
| `ending_balance_kpy` | 期末残高 | INT64 | 月末時点の累積残高（千円） |
| `min_cash_flag` | 資金ショートフラグ | INT64 | 期末残高 < 0 の場合 = 1 |
| `cashflow_risk` | リスク判定 | STRING | 資金不足リスク/注意/正常 |

**Looker Studio でのグラフ例**:
- 複合グラフ: `cf_date` × (`expected_inflow_kpy`[棒] + `total_outflow_kpy`[棒] + `ending_balance_kpy`[折れ線])
- スコアカード: 最新月の `ending_balance_kpy`, `min_cash_flag` の合計
- テーブル: `min_cash_flag = 1` でフィルタ → 資金ショートリスク月の一覧

---

## 🤖 ML用: `vw_ml_features`

| カラム名 (BigQuery) | 日本語名 | 型 | 説明 |
|:---|:---|:---:|:---|
| `project_id` | 工事ID | STRING | |
| `actual_cost_rate` | 実績原価率 | FLOAT64 | 回帰モデルのターゲット変数 (%) |
| `division` | 事業部 | STRING | One-Hot特徴量 |
| `client_type` | 発注者 | STRING | One-Hot特徴量 |
| `contract_amount_kpy` | 請負金額 | INT64 | 連続特徴量（千円） |
| `duration_months` | 工期 | INT64 | 連続特徴量（月） |
| `target_cost_rate` | 目標原価率 | FLOAT64 | 連続特徴量 (%) |
| `progress_rate` | 進捗率 | FLOAT64 | 連続特徴量 (%) |
| `project_status` | ステータス | STRING | One-Hot特徴量 |
| `confirmed_cost_rate` | 確定原価率 | FLOAT64 | 確定原価 ÷ 請負金額 (%) |
| `forecast_cost_rate` | 見込み原価率 | FLOAT64 | 見込み原価 ÷ 請負金額 (%) |
| `confirmed_ratio` | 確定比率 | FLOAT64 | 確定原価 ÷ 総原価 (%) |
| `outsourcing_pct` | 外注費比率 | FLOAT64 | % |
| `material_pct` | 材料費比率 | FLOAT64 | % |
| `labor_pct` | 労務費比率 | FLOAT64 | % |
| `expense_pct` | 経費比率 | FLOAT64 | % |
| `cost_progress_ratio` | 原価消化ペース | FLOAT64 | 原価率÷進捗率（>1で先行消化） |
| `cost_record_count` | レコード数 | INT64 | 原価明細の件数 |
| `confirmed_count` | 確定レコード数 | INT64 | 確定請求のレコード数 |
| `forecast_count` | 見込みレコード数 | INT64 | 見込み・口頭発注のレコード数 |

---

## 📝 命名規則

| 接尾辞 | 意味 | 例 |
|:---|:---|:---|
| `_kpy` | 千円単位の金額 | `contract_amount_kpy` |
| `_rate` | パーセンテージ (%) | `target_cost_rate` |
| `_ratio` | 比率 (%) | `outsourcing_ratio` |
| `_pct` | 比率 (%) ※ML特徴量用 | `outsourcing_pct` |
| `_count` | 件数 | `project_count` |
| `_flag` | 0/1 フラグ | `min_cash_flag` |
| `_month` | 日付ディメンション (DATE) | `sales_month` |
| `_str` | 文字列表現 | `month_str` |

> 💡 **Looker Studio Tips**: BigQuery のカラム名は変更できませんが、Looker Studio 側でフィールドの「表示名」を自由に日本語に設定できます。上記の日本語名をそのまま表示名にコピーしてください。
