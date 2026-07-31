-- =============================================================================
-- 加和太建設 DXコックピット PoC — BigQuery 分析ビュー定義 (v2)
-- =============================================================================
--
-- Looker Studio の4ページ構成に完全対応
--   Page 1: 全社経営サマリー  → vw_company_dashboard
--   Page 2: まちづくりROI     → vw_area_roi, vw_area_indicators
--   Page 3: 工事原価管理      → vw_project_cost_summary, vw_cost_category_detail
--   Page 4: キャッシュフロー   → vw_cashflow_forecast
--   ML用:                     → vw_ml_features
--
-- 使い方:
--   1. {PROJECT_ID} と {DATASET} を実際の値に置換する
--   2. BigQuery コンソールで各 CREATE VIEW 文を個別に実行する
--
-- カラム名の命名規則:
--   英語表記 + SQLコメントで日本語名を併記
--   別途 docs/column_dictionary.md に日英対照表あり
-- =============================================================================


-- ═══════════════════════════════════════════════════════════════════════════
-- Page 1: 全社経営サマリー
-- ═══════════════════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET}.vw_company_dashboard` AS
WITH
-- 月別入金（建設事業の売上ベース）
monthly_inflow AS (
  SELECT
    PARSE_DATE('%Y-%m-%d', CONCAT(deposit_month, '-01')) AS sales_month,  -- 月ディメンション
    SUM(expected_amount_kpy) AS inflow_amount
  FROM `{PROJECT_ID}.{DATASET}.cash_in_schedules`
  GROUP BY 1
),
-- 月別出金（原価合計）
monthly_outflow AS (
  SELECT
    PARSE_DATE('%Y-%m-%d', CONCAT(accrual_month, '-01')) AS sales_month,
    SUM(amount_kpy) AS outflow_amount
  FROM `{PROJECT_ID}.{DATASET}.cost_records`
  GROUP BY 1
),
-- 不動産月次収入
monthly_rental AS (
  SELECT
    PARSE_DATE('%Y-%m-%d', CONCAT(deposit_month, '-01')) AS sales_month,
    SUM(monthly_rental_income_kpy) AS rental_income
  FROM (
    -- 不動産は毎月一定の賃料収入が発生する前提
    SELECT
      r.monthly_rental_income_kpy,
      m.deposit_month
    FROM `{PROJECT_ID}.{DATASET}.real_estate_properties` r
    CROSS JOIN (
      SELECT DISTINCT deposit_month
      FROM `{PROJECT_ID}.{DATASET}.cash_in_schedules`
    ) m
  )
  GROUP BY 1
),
-- 施設運営月次
monthly_facility AS (
  SELECT
    PARSE_DATE('%Y-%m-%d', CONCAT(month, '-01')) AS sales_month,
    SUM(revenue_kpy) AS facility_revenue,
    SUM(operating_profit_kpy) AS facility_profit
  FROM `{PROJECT_ID}.{DATASET}.facility_operations`
  GROUP BY 1
),
-- SaaS月次
monthly_saas AS (
  SELECT
    PARSE_DATE('%Y-%m-%d', CONCAT(month, '-01')) AS sales_month,
    SUM(mrr_kpy) AS saas_mrr
  FROM `{PROJECT_ID}.{DATASET}.saas_metrics`
  GROUP BY 1
),
-- 進行中工事数（月別）
monthly_active_projects AS (
  SELECT
    m.sales_month,
    COUNT(DISTINCT p.project_id) AS active_project_count  -- 進行中工事数
  FROM monthly_inflow m
  CROSS JOIN `{PROJECT_ID}.{DATASET}.projects_master` p
  WHERE DATE(p.start_date) <= m.sales_month
    AND DATE(p.end_date) >= m.sales_month
  GROUP BY 1
),
-- 統合
combined AS (
  SELECT
    i.sales_month,
    -- 全事業売上合算
    COALESCE(i.inflow_amount, 0)
      + COALESCE(r.rental_income, 0)
      + COALESCE(f.facility_revenue, 0)
      + COALESCE(s.saas_mrr, 0) AS total_sales,           -- 全社売上（千円）
    COALESCE(i.inflow_amount, 0) AS actual_sales,          -- 建設売上実績（千円）
    COALESCE(o.outflow_amount, 0) AS total_cost,           -- 原価合計（千円）
    COALESCE(ap.active_project_count, 0) AS active_project_count  -- 進行中工事数
  FROM monthly_inflow i
  LEFT JOIN monthly_outflow o ON i.sales_month = o.sales_month
  LEFT JOIN monthly_rental r ON i.sales_month = r.sales_month
  LEFT JOIN monthly_facility f ON i.sales_month = f.sales_month
  LEFT JOIN monthly_saas s ON i.sales_month = s.sales_month
  LEFT JOIN monthly_active_projects ap ON i.sales_month = ap.sales_month
)
SELECT
  sales_month,                                              -- 月ディメンション
  total_sales,                                              -- 全社売上
  actual_sales,                                             -- 売上実績（建設事業）
  -- 売上予測: 直近3ヶ月移動平均
  CAST(AVG(total_sales) OVER (
    ORDER BY sales_month
    ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING
  ) AS INT64) AS forecast_sales,                            -- 売上予測
  -- 営業利益率 = (売上 - 原価) / 売上 × 100
  ROUND(SAFE_DIVIDE(total_sales - total_cost, total_sales) * 100, 1)
    AS operating_profit_margin,                             -- 営業利益率（%）
  active_project_count,                                     -- 進行中工事数
  -- 手元資金 = 累積キャッシュフロー
  SUM(total_sales - total_cost) OVER (
    ORDER BY sales_month
  ) AS cash_balance                                         -- 手元資金（千円）
FROM combined
ORDER BY sales_month;


-- ═══════════════════════════════════════════════════════════════════════════
-- Page 2-a: まちづくりROIダッシュボード
-- ═══════════════════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET}.vw_area_roi` AS
WITH
-- エリア判定用ヘルパー
area_detect AS (
  SELECT
    project_id, project_name, contract_amount_kpy,
    CASE
      WHEN project_name LIKE '%三島%' THEN '三島'
      WHEN project_name LIKE '%沼津%' THEN '沼津'
      WHEN project_name LIKE '%函南%' THEN '函南'
      WHEN project_name LIKE '%清水%' THEN '清水'
      WHEN project_name LIKE '%長泉%' THEN '長泉'
      WHEN project_name LIKE '%伊豆の国%' THEN '伊豆の国'
      WHEN project_name LIKE '%伊豆市%' THEN '伊豆'
      ELSE 'その他'
    END AS area
  FROM `{PROJECT_ID}.{DATASET}.projects_master`
),
construction_by_area AS (
  SELECT
    area,
    SUM(contract_amount_kpy) AS construction_revenue_kpy,  -- 建設事業売上
    COUNT(*) AS project_count                              -- 工事件数
  FROM area_detect
  GROUP BY 1
),
real_estate_by_area AS (
  SELECT
    CASE
      WHEN location LIKE '%三島%' THEN '三島'
      WHEN location LIKE '%沼津%' THEN '沼津'
      WHEN location LIKE '%函南%' THEN '函南'
      ELSE 'その他'
    END AS area,
    SUM(monthly_rental_income_kpy) * 12 AS annual_rental_income_kpy,  -- 年間賃貸収入
    SUM(acquisition_cost_kpy) AS total_acquisition_cost_kpy,          -- 取得原価合計
    SUM(current_value_kpy) AS total_property_value_kpy,               -- 時価合計
    AVG(occupancy_rate) AS avg_occupancy_rate,                        -- 平均稼働率
    COUNT(*) AS property_count                                        -- 物件数
  FROM `{PROJECT_ID}.{DATASET}.real_estate_properties`
  GROUP BY 1
),
facility_by_area AS (
  SELECT
    CASE
      WHEN facility_name LIKE '%函南%' OR facility_name LIKE '%伊豆%' THEN '函南'
      WHEN facility_name LIKE '%三島%' OR facility_name LIKE '%未来%' THEN '三島'
      WHEN facility_name LIKE '%沼津%' THEN '沼津'
      ELSE 'その他'
    END AS area,
    SUM(revenue_kpy) AS facility_revenue_kpy,              -- 施設売上
    SUM(operating_profit_kpy) AS facility_profit_kpy,      -- 施設営業利益
    SUM(visitors) AS total_visitors                        -- 来場者合計
  FROM `{PROJECT_ID}.{DATASET}.facility_operations`
  GROUP BY 1
),
area_data AS (
  SELECT
    area_name AS area,
    AVG(land_price_index) AS avg_land_price_index,         -- 平均地価指数
    AVG(population) AS avg_population,                     -- 平均人口
    AVG(foot_traffic) AS avg_foot_traffic                  -- 平均歩行者数
  FROM `{PROJECT_ID}.{DATASET}.area_indicators`
  GROUP BY 1
)
SELECT
  COALESCE(c.area, r.area, f.area, a.area) AS area,       -- エリア名
  -- 事業別売上
  COALESCE(c.construction_revenue_kpy, 0) AS construction_revenue_kpy,  -- 建設事業売上
  COALESCE(c.project_count, 0) AS project_count,                        -- 工事件数
  COALESCE(r.annual_rental_income_kpy, 0) AS annual_rental_income_kpy,  -- 不動産年間収入
  COALESCE(r.total_property_value_kpy, 0) AS property_value_kpy,        -- 不動産時価
  COALESCE(r.avg_occupancy_rate, 0) AS avg_occupancy_rate,              -- 平均稼働率（%）
  COALESCE(f.facility_revenue_kpy, 0) AS facility_revenue_kpy,          -- 施設売上
  COALESCE(f.facility_profit_kpy, 0) AS facility_profit_kpy,            -- 施設営業利益
  COALESCE(f.total_visitors, 0) AS total_visitors,                      -- 来場者合計
  -- 統合指標
  (COALESCE(c.construction_revenue_kpy, 0)
   + COALESCE(r.annual_rental_income_kpy, 0)
   + COALESCE(f.facility_revenue_kpy, 0)) AS total_return_kpy,          -- 総リターン（千円）
  -- ★ 投資総額 = 不動産取得原価 + 建設請負額（エリアへの投下資本）
  (COALESCE(c.construction_revenue_kpy, 0)
   + COALESCE(r.total_acquisition_cost_kpy, 0)) AS total_investment_kpy, -- 投資総額（千円）
  -- ★ ROI率 = (総リターン - 投資総額) / 投資総額 × 100
  ROUND(SAFE_DIVIDE(
    (COALESCE(c.construction_revenue_kpy, 0) + COALESCE(r.annual_rental_income_kpy, 0) + COALESCE(f.facility_revenue_kpy, 0))
    - (COALESCE(c.construction_revenue_kpy, 0) + COALESCE(r.total_acquisition_cost_kpy, 0)),
    (COALESCE(c.construction_revenue_kpy, 0) + COALESCE(r.total_acquisition_cost_kpy, 0))
  ) * 100, 1) AS roi_rate,                                              -- ROI率（%）
  -- エリア指標
  COALESCE(a.avg_land_price_index, 0) AS land_price_index,              -- 地価指数
  COALESCE(a.avg_population, 0) AS population,                          -- 人口
  COALESCE(a.avg_foot_traffic, 0) AS foot_traffic                       -- 歩行者数
FROM construction_by_area c
FULL OUTER JOIN real_estate_by_area r ON c.area = r.area
FULL OUTER JOIN facility_by_area f ON COALESCE(c.area, r.area) = f.area
FULL OUTER JOIN area_data a ON COALESCE(c.area, r.area, f.area) = a.area;


-- ═══════════════════════════════════════════════════════════════════════════
-- Page 2-b: エリア指標ビュー（area_indicators のLooker用ラッパー）
-- ═══════════════════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET}.vw_area_indicators` AS
SELECT
  area_name,                                                             -- エリア名
  PARSE_DATE('%Y-%m-%d', CONCAT(month, '-01')) AS indicator_month,       -- 年月ディメンション（DATE型）
  land_price_index,                                                      -- 地価指数
  population,                                                            -- 人口
  foot_traffic,                                                          -- 歩行者交通量
  new_business_count,                                                    -- 新規事業数
  event_count                                                            -- イベント数
FROM `{PROJECT_ID}.{DATASET}.area_indicators`;


-- ═══════════════════════════════════════════════════════════════════════════
-- Page 3-a: 工事原価管理
-- ═══════════════════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET}.vw_project_cost_summary` AS
WITH cost_agg AS (
  SELECT
    project_id,
    SUM(CASE WHEN status = '確定請求' THEN amount_kpy ELSE 0 END) AS confirmed_cost,  -- 確定原価
    SUM(CASE WHEN status IN ('現場見込み', '口頭発注') THEN amount_kpy ELSE 0 END) AS forecast_cost,  -- 見込み原価
    SUM(amount_kpy) AS total_cost,                                       -- 総原価
    SUM(CASE WHEN category = '外注費' THEN amount_kpy ELSE 0 END) AS outsourcing_cost,  -- 外注費
    SUM(CASE WHEN category = '材料費' THEN amount_kpy ELSE 0 END) AS material_cost,     -- 材料費
    SUM(CASE WHEN category = '労務費' THEN amount_kpy ELSE 0 END) AS labor_cost,        -- 労務費
    SUM(CASE WHEN category = '経費' THEN amount_kpy ELSE 0 END) AS expense_cost,        -- 経費
    COUNT(*) AS record_count                                             -- レコード数
  FROM `{PROJECT_ID}.{DATASET}.cost_records`
  GROUP BY project_id
)
SELECT
  p.project_id,                                                          -- 工事ID
  p.project_name,                                                        -- 工事名
  p.division,                                                            -- 事業部（土木/建築）
  p.client_type,                                                         -- 発注者（官公庁/民間）
  p.pm_name,                                                             -- プロジェクトマネージャー名
  p.contract_amount_kpy,                                                 -- 請負金額（千円）
  p.target_cost_rate,                                                    -- 目標原価率（%）
  p.progress_rate,                                                       -- 工事進捗率（%）
  p.status AS project_status,                                            -- 工事ステータス
  p.start_date,                                                          -- 着工日
  p.end_date,                                                            -- 竣工予定日
  -- 原価
  COALESCE(c.confirmed_cost, 0) AS confirmed_cost_kpy,                   -- 確定原価（千円）
  COALESCE(c.forecast_cost, 0) AS forecast_cost_kpy,                     -- 見込み原価（千円）
  COALESCE(c.total_cost, 0) AS total_cost_kpy,                           -- 総原価（千円）
  -- ★ 粗利 = 請負金額 - 総原価
  p.contract_amount_kpy - COALESCE(c.total_cost, 0) AS gross_profit,     -- 粗利（千円）
  -- 原価率
  ROUND(SAFE_DIVIDE(COALESCE(c.total_cost, 0), p.contract_amount_kpy) * 100, 1)
    AS effective_cost_rate,                                               -- 実効原価率（%）
  ROUND(SAFE_DIVIDE(COALESCE(c.total_cost, 0), p.contract_amount_kpy) * 100 - p.target_cost_rate, 1)
    AS cost_rate_gap,                                                     -- 原価率乖離（ポイント）
  -- カテゴリ別
  COALESCE(c.outsourcing_cost, 0) AS outsourcing_cost_kpy,               -- 外注費（千円）
  COALESCE(c.material_cost, 0) AS material_cost_kpy,                     -- 材料費（千円）
  COALESCE(c.labor_cost, 0) AS labor_cost_kpy,                           -- 労務費（千円）
  COALESCE(c.expense_cost, 0) AS expense_cost_kpy,                       -- 経費（千円）
  -- カテゴリ別比率
  ROUND(SAFE_DIVIDE(c.outsourcing_cost, c.total_cost) * 100, 1) AS outsourcing_ratio,  -- 外注費比率（%）
  ROUND(SAFE_DIVIDE(c.material_cost, c.total_cost) * 100, 1) AS material_ratio,        -- 材料費比率（%）
  ROUND(SAFE_DIVIDE(c.labor_cost, c.total_cost) * 100, 1) AS labor_ratio,              -- 労務費比率（%）
  ROUND(SAFE_DIVIDE(c.expense_cost, c.total_cost) * 100, 1) AS expense_ratio,          -- 経費比率（%）
  -- リスク判定
  CASE
    WHEN SAFE_DIVIDE(COALESCE(c.total_cost, 0), p.contract_amount_kpy) * 100 >= p.target_cost_rate + 5 THEN '緊急'
    WHEN SAFE_DIVIDE(COALESCE(c.total_cost, 0), p.contract_amount_kpy) * 100 >= p.target_cost_rate THEN '警告'
    WHEN SAFE_DIVIDE(COALESCE(c.total_cost, 0), p.contract_amount_kpy) * 100 >= p.target_cost_rate * 0.95 THEN '注意'
    ELSE '正常'
  END AS risk_level                                                       -- リスクレベル
FROM `{PROJECT_ID}.{DATASET}.projects_master` p
LEFT JOIN cost_agg c ON p.project_id = c.project_id;


-- ═══════════════════════════════════════════════════════════════════════════
-- Page 3-b: 原価カテゴリ別詳細（ドーナツ・棒グラフ用）
-- ═══════════════════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET}.vw_cost_category_detail` AS
SELECT
  p.project_id,                                                          -- 工事ID
  p.project_name,                                                        -- 工事名
  p.division,                                                            -- 事業部
  c.category AS cost_category,                                           -- 原価カテゴリ（外注費/材料費/労務費/経費）
  -- カテゴリ別予算原価 = 請負金額 × 目標原価率 × カテゴリ標準比率
  CAST(CASE c.category
    WHEN '外注費' THEN p.contract_amount_kpy * p.target_cost_rate / 100 * 0.45
    WHEN '材料費' THEN p.contract_amount_kpy * p.target_cost_rate / 100 * 0.25
    WHEN '労務費' THEN p.contract_amount_kpy * p.target_cost_rate / 100 * 0.20
    WHEN '経費'   THEN p.contract_amount_kpy * p.target_cost_rate / 100 * 0.10
    ELSE 0
  END AS INT64) AS category_budget,                                      -- カテゴリ別予算原価（千円）
  -- カテゴリ別実績原価
  CAST(SUM(c.amount_kpy) AS INT64) AS category_actual,                   -- カテゴリ別実績原価（千円）
  -- 予実差異
  CAST(CASE c.category
    WHEN '外注費' THEN p.contract_amount_kpy * p.target_cost_rate / 100 * 0.45
    WHEN '材料費' THEN p.contract_amount_kpy * p.target_cost_rate / 100 * 0.25
    WHEN '労務費' THEN p.contract_amount_kpy * p.target_cost_rate / 100 * 0.20
    WHEN '経費'   THEN p.contract_amount_kpy * p.target_cost_rate / 100 * 0.10
    ELSE 0
  END - SUM(c.amount_kpy) AS INT64) AS category_variance                 -- 予実差異（千円、正=余裕/負=超過）
FROM `{PROJECT_ID}.{DATASET}.cost_records` c
JOIN `{PROJECT_ID}.{DATASET}.projects_master` p ON c.project_id = p.project_id
GROUP BY p.project_id, p.project_name, p.division, c.category,
         p.contract_amount_kpy, p.target_cost_rate;


-- ═══════════════════════════════════════════════════════════════════════════
-- Page 4: キャッシュフロー
-- ═══════════════════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET}.vw_cashflow_forecast` AS
WITH
monthly_inflow AS (
  SELECT
    deposit_month AS month_str,
    SUM(expected_amount_kpy) AS expected_inflow,                         -- 入金予定（千円）
    SUM(CASE WHEN status = '入金済'
        THEN COALESCE(actual_amount_kpy, expected_amount_kpy) ELSE 0
    END) AS actual_inflow                                                -- 入金実績（千円）
  FROM `{PROJECT_ID}.{DATASET}.cash_in_schedules`
  GROUP BY deposit_month
),
monthly_outflow AS (
  SELECT
    payment_due_month AS month_str,
    SUM(amount_kpy) AS total_outflow,                                    -- 出金合計（千円）
    SUM(CASE WHEN status = '確定請求' THEN amount_kpy ELSE 0 END) AS confirmed_outflow,  -- 確定出金
    SUM(CASE WHEN status IN ('現場見込み', '口頭発注') THEN amount_kpy ELSE 0 END) AS forecast_outflow  -- 見込み出金
  FROM `{PROJECT_ID}.{DATASET}.cost_records`
  GROUP BY payment_due_month
),
combined AS (
  SELECT
    COALESCE(i.month_str, o.month_str) AS month_str,
    COALESCE(i.expected_inflow, 0) AS expected_inflow_kpy,
    COALESCE(i.actual_inflow, 0) AS actual_inflow_kpy,
    COALESCE(o.total_outflow, 0) AS total_outflow_kpy,
    COALESCE(o.confirmed_outflow, 0) AS confirmed_outflow_kpy,
    COALESCE(o.forecast_outflow, 0) AS forecast_outflow_kpy,
    COALESCE(i.expected_inflow, 0) - COALESCE(o.total_outflow, 0) AS net_cashflow_kpy
  FROM monthly_inflow i
  FULL OUTER JOIN monthly_outflow o ON i.month_str = o.month_str
)
SELECT
  -- ★ Looker用日付型ディメンション
  PARSE_DATE('%Y-%m-%d', CONCAT(month_str, '-01')) AS cf_date,           -- キャッシュフロー日付（DATE型）
  month_str,                                                             -- 年月文字列
  expected_inflow_kpy,                                                   -- 入金予定（千円）
  actual_inflow_kpy,                                                     -- 入金実績（千円）
  total_outflow_kpy,                                                     -- 出金合計（千円）
  confirmed_outflow_kpy,                                                 -- 確定出金（千円）
  forecast_outflow_kpy,                                                  -- 見込み出金（千円）
  net_cashflow_kpy,                                                      -- 純キャッシュフロー（千円）
  -- ★ 期首残高 = 前月までの累積CF
  COALESCE(SUM(net_cashflow_kpy) OVER (
    ORDER BY month_str
    ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
  ), 0) AS beginning_balance_kpy,                                        -- 期首残高（千円）
  -- ★ 期末残高 = 当月までの累積CF
  SUM(net_cashflow_kpy) OVER (
    ORDER BY month_str
  ) AS ending_balance_kpy,                                               -- 期末残高（千円）
  -- ★ 最小残高アラートフラグ（期末残高がマイナスの場合 = 1）
  CASE
    WHEN SUM(net_cashflow_kpy) OVER (ORDER BY month_str) < 0 THEN 1
    ELSE 0
  END AS min_cash_flag,                                                  -- 資金ショートアラートフラグ
  -- リスク判定
  CASE
    WHEN net_cashflow_kpy < -50000 THEN '資金不足リスク'
    WHEN net_cashflow_kpy < 0 THEN '注意'
    ELSE '正常'
  END AS cashflow_risk                                                   -- リスク判定
FROM combined
ORDER BY month_str;


-- ═══════════════════════════════════════════════════════════════════════════
-- ML用: AI原価予測 特徴量テーブル
-- ═══════════════════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET}.vw_ml_features` AS
WITH project_costs AS (
  SELECT
    project_id,
    SUM(amount_kpy) AS total_cost,                                       -- 総原価
    SUM(CASE WHEN status = '確定請求' THEN amount_kpy ELSE 0 END) AS confirmed_cost,  -- 確定原価
    SUM(CASE WHEN status IN ('現場見込み', '口頭発注') THEN amount_kpy ELSE 0 END) AS forecast_cost,  -- 見込み原価
    SUM(CASE WHEN category = '外注費' THEN amount_kpy ELSE 0 END) AS outsourcing_cost,
    SUM(CASE WHEN category = '材料費' THEN amount_kpy ELSE 0 END) AS material_cost,
    SUM(CASE WHEN category = '労務費' THEN amount_kpy ELSE 0 END) AS labor_cost,
    SUM(CASE WHEN category = '経費' THEN amount_kpy ELSE 0 END) AS expense_cost,
    COUNT(*) AS cost_record_count,
    COUNT(CASE WHEN status = '確定請求' THEN 1 END) AS confirmed_count,
    COUNT(CASE WHEN status IN ('現場見込み', '口頭発注') THEN 1 END) AS forecast_count
  FROM `{PROJECT_ID}.{DATASET}.cost_records`
  GROUP BY project_id
)
SELECT
  p.project_id,                                                          -- 工事ID
  SAFE_DIVIDE(c.total_cost, p.contract_amount_kpy) * 100 AS actual_cost_rate,  -- 実績原価率（%）
  p.division,                                                            -- 事業部
  p.client_type,                                                         -- 発注者
  p.contract_amount_kpy,                                                 -- 請負金額
  DATE_DIFF(DATE(p.end_date), DATE(p.start_date), MONTH) AS duration_months,  -- 工期（月）
  p.target_cost_rate,                                                    -- 目標原価率（%）
  p.progress_rate,                                                       -- 進捗率（%）
  p.status AS project_status,                                            -- ステータス
  SAFE_DIVIDE(c.confirmed_cost, p.contract_amount_kpy) * 100 AS confirmed_cost_rate,  -- 確定原価率（%）
  SAFE_DIVIDE(c.forecast_cost, p.contract_amount_kpy) * 100 AS forecast_cost_rate,    -- 見込み原価率（%）
  SAFE_DIVIDE(c.confirmed_cost, c.total_cost) * 100 AS confirmed_ratio,               -- 確定比率（%）
  SAFE_DIVIDE(c.outsourcing_cost, c.total_cost) * 100 AS outsourcing_pct,  -- 外注費比率（%）
  SAFE_DIVIDE(c.material_cost, c.total_cost) * 100 AS material_pct,        -- 材料費比率（%）
  SAFE_DIVIDE(c.labor_cost, c.total_cost) * 100 AS labor_pct,              -- 労務費比率（%）
  SAFE_DIVIDE(c.expense_cost, c.total_cost) * 100 AS expense_pct,          -- 経費比率（%）
  SAFE_DIVIDE(
    SAFE_DIVIDE(c.total_cost, p.contract_amount_kpy),
    p.progress_rate / 100
  ) AS cost_progress_ratio,                                                -- 原価消化ペース
  c.cost_record_count,                                                     -- レコード数
  c.confirmed_count,                                                       -- 確定レコード数
  c.forecast_count                                                         -- 見込みレコード数
FROM `{PROJECT_ID}.{DATASET}.projects_master` p
LEFT JOIN project_costs c ON p.project_id = c.project_id
WHERE c.total_cost IS NOT NULL;
