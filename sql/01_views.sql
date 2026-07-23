-- =============================================================================
-- 加和太建設 DXコックピット PoC — BigQuery 分析ビュー定義
-- =============================================================================
-- 
-- 前提:
--   BigQuery プロジェクト内に以下のテーブルが存在すること
--   - `{kawata-dx-poc}.{kawata_dx_cockpit}.projects_master`
--   - `{kawata-dx-poc}.{kawata_dx_cockpit}.cost_records`
--   - `{kawata-dx-poc}.{kawata_dx_cockpit}.cash_in_schedules`
--   - `{kawata-dx-poc}.{kawata_dx_cockpit}.real_estate_properties`
--   - `{kawata-dx-poc}.{kawata_dx_cockpit}.facility_operations`
--   - `{kawata-dx-poc}.{kawata_dx_cockpit}.saas_metrics`
--   - `{kawata-dx-poc}.{kawata_dx_cockpit}.area_indicators`
--
-- 使い方:
--   1. BigQuery コンソールで新しいクエリを開く
--   2. {kawata-dx-poc} と {kawata_dx_cockpit} を実際の値に置換する
--   3. 各 CREATE VIEW 文を個別に実行する
--
-- =============================================================================


-- ---------------------------------------------------------------------------
-- ビュー 1: 工事別 原価サマリー
-- 各工事の確定原価・見込み原価・実効原価率を統合算出する
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW `{kawata-dx-poc}.{kawata_dx_cockpit}.vw_project_cost_summary` AS
WITH cost_agg AS (
  SELECT
    kawata-dx-poc,
    -- 確定原価
    SUM(CASE WHEN status = '確定請求' THEN amount_kpy ELSE 0 END) AS confirmed_cost,
    -- 見込み原価（口頭発注 + 現場見込み）
    SUM(CASE WHEN status IN ('現場見込み', '口頭発注') THEN amount_kpy ELSE 0 END) AS forecast_cost,
    -- 総原価（確定 + 見込み）
    SUM(amount_kpy) AS total_cost,
    -- カテゴリ別集計
    SUM(CASE WHEN category = '外注費' THEN amount_kpy ELSE 0 END) AS outsourcing_cost,
    SUM(CASE WHEN category = '材料費' THEN amount_kpy ELSE 0 END) AS material_cost,
    SUM(CASE WHEN category = '労務費' THEN amount_kpy ELSE 0 END) AS labor_cost,
    SUM(CASE WHEN category = '経費' THEN amount_kpy ELSE 0 END) AS expense_cost,
    -- レコード数
    COUNT(*) AS record_count,
    COUNT(CASE WHEN status = '確定請求' THEN 1 END) AS confirmed_count,
    COUNT(CASE WHEN status IN ('現場見込み', '口頭発注') THEN 1 END) AS forecast_count
  FROM `{kawata-dx-poc}.{kawata_dx_cockpit}.cost_records`
  GROUP BY kawata-dx-poc
)
SELECT
  p.kawata-dx-poc,
  p.project_name,
  p.division,
  p.client_type,
  p.contract_amount_kpy,
  p.target_cost_rate,
  p.progress_rate,
  p.status AS project_status,
  p.start_date,
  p.end_date,
  -- 原価集計
  COALESCE(c.confirmed_cost, 0) AS confirmed_cost_kpy,
  COALESCE(c.forecast_cost, 0) AS forecast_cost_kpy,
  COALESCE(c.total_cost, 0) AS total_cost_kpy,
  -- 原価率の算出
  SAFE_DIVIDE(COALESCE(c.confirmed_cost, 0), p.contract_amount_kpy) * 100 AS confirmed_cost_rate,
  SAFE_DIVIDE(COALESCE(c.total_cost, 0), p.contract_amount_kpy) * 100 AS effective_cost_rate,
  -- 目標との差異（正 = 超過、負 = 余裕）
  SAFE_DIVIDE(COALESCE(c.total_cost, 0), p.contract_amount_kpy) * 100 - p.target_cost_rate AS cost_rate_gap,
  -- カテゴリ別
  COALESCE(c.outsourcing_cost, 0) AS outsourcing_cost_kpy,
  COALESCE(c.material_cost, 0) AS material_cost_kpy,
  COALESCE(c.labor_cost, 0) AS labor_cost_kpy,
  COALESCE(c.expense_cost, 0) AS expense_cost_kpy,
  -- カテゴリ別比率
  SAFE_DIVIDE(c.outsourcing_cost, c.total_cost) * 100 AS outsourcing_ratio,
  SAFE_DIVIDE(c.material_cost, c.total_cost) * 100 AS material_ratio,
  SAFE_DIVIDE(c.labor_cost, c.total_cost) * 100 AS labor_ratio,
  SAFE_DIVIDE(c.expense_cost, c.total_cost) * 100 AS expense_ratio,
  -- リスク判定
  CASE
    WHEN SAFE_DIVIDE(COALESCE(c.total_cost, 0), p.contract_amount_kpy) * 100 >= p.target_cost_rate + 5 THEN '🔴 緊急'
    WHEN SAFE_DIVIDE(COALESCE(c.total_cost, 0), p.contract_amount_kpy) * 100 >= p.target_cost_rate THEN '🟠 警告'
    WHEN SAFE_DIVIDE(COALESCE(c.total_cost, 0), p.contract_amount_kpy) * 100 >= p.target_cost_rate * 0.95 THEN '🟡 注意'
    ELSE '🟢 正常'
  END AS risk_level
FROM `{kawata-dx-poc}.{kawata_dx_cockpit}.projects_master` p
LEFT JOIN cost_agg c ON p.kawata-dx-poc = c.kawata-dx-poc;


-- ---------------------------------------------------------------------------
-- ビュー 2: 月別キャッシュフロー予測
-- 全社の月別入金予定と出金予定を統合し、資金残高推移を算出する
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW `{kawata-dx-poc}.{kawata_dx_cockpit}.vw_cashflow_forecast` AS
WITH monthly_inflow AS (
  -- 入金予定の月別集計
  SELECT
    deposit_month AS month,
    SUM(expected_amount_kpy) AS expected_inflow,
    SUM(CASE WHEN status = '入金済' THEN COALESCE(actual_amount_kpy, expected_amount_kpy) ELSE 0 END) AS actual_inflow,
    COUNT(*) AS inflow_count
  FROM `{kawata-dx-poc}.{kawata_dx_cockpit}.cash_in_schedules`
  GROUP BY deposit_month
),
monthly_outflow AS (
  -- 出金予定の月別集計（支払予定月ベース）
  SELECT
    payment_due_month AS month,
    SUM(amount_kpy) AS total_outflow,
    SUM(CASE WHEN status = '確定請求' THEN amount_kpy ELSE 0 END) AS confirmed_outflow,
    SUM(CASE WHEN status IN ('現場見込み', '口頭発注') THEN amount_kpy ELSE 0 END) AS forecast_outflow,
    COUNT(*) AS outflow_count
  FROM `{kawata-dx-poc}.{kawata_dx_cockpit}.cost_records`
  GROUP BY payment_due_month
)
SELECT
  COALESCE(i.month, o.month) AS month,
  COALESCE(i.expected_inflow, 0) AS expected_inflow_kpy,
  COALESCE(i.actual_inflow, 0) AS actual_inflow_kpy,
  COALESCE(o.total_outflow, 0) AS total_outflow_kpy,
  COALESCE(o.confirmed_outflow, 0) AS confirmed_outflow_kpy,
  COALESCE(o.forecast_outflow, 0) AS forecast_outflow_kpy,
  -- 月次純キャッシュフロー
  COALESCE(i.expected_inflow, 0) - COALESCE(o.total_outflow, 0) AS net_cashflow_kpy,
  -- 累積キャッシュフロー（ウィンドウ関数）
  SUM(COALESCE(i.expected_inflow, 0) - COALESCE(o.total_outflow, 0))
    OVER (ORDER BY COALESCE(i.month, o.month)) AS cumulative_cashflow_kpy,
  -- 資金ショートリスク判定
  CASE
    WHEN COALESCE(i.expected_inflow, 0) - COALESCE(o.total_outflow, 0) < -50000 THEN '🔴 資金不足リスク'
    WHEN COALESCE(i.expected_inflow, 0) - COALESCE(o.total_outflow, 0) < 0 THEN '🟡 注意'
    ELSE '🟢 正常'
  END AS cashflow_risk
FROM monthly_inflow i
FULL OUTER JOIN monthly_outflow o ON i.month = o.month
ORDER BY month;


-- ---------------------------------------------------------------------------
-- ビュー 3: エリア別まちづくりROI
-- 建設事業・不動産事業・施設運営の収益をエリア単位で統合し、ROIを算出する
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW `{kawata-dx-poc}.{kawata_dx_cockpit}.vw_area_roi` AS
WITH construction_by_area AS (
  -- 建設事業: project_nameの先頭に市町名が含まれている前提
  SELECT
    CASE
      WHEN project_name LIKE '%三島%' THEN '三島'
      WHEN project_name LIKE '%沼津%' THEN '沼津'
      WHEN project_name LIKE '%函南%' THEN '函南'
      WHEN project_name LIKE '%清水%' THEN '清水'
      WHEN project_name LIKE '%長泉%' THEN '長泉'
      ELSE 'その他'
    END AS area,
    SUM(contract_amount_kpy) AS construction_revenue_kpy,
    COUNT(*) AS project_count,
    AVG(progress_rate) AS avg_progress
  FROM `{kawata-dx-poc}.{kawata_dx_cockpit}.projects_master`
  GROUP BY 1
),
real_estate_by_area AS (
  -- 不動産事業: location列でエリア判定
  SELECT
    CASE
      WHEN location LIKE '%三島%' THEN '三島'
      WHEN location LIKE '%沼津%' THEN '沼津'
      WHEN location LIKE '%函南%' THEN '函南'
      ELSE 'その他'
    END AS area,
    SUM(monthly_rental_income_kpy) * 12 AS annual_rental_income_kpy,
    SUM(current_value_kpy) AS total_property_value_kpy,
    SUM(acquisition_cost_kpy) AS total_acquisition_cost_kpy,
    AVG(occupancy_rate) AS avg_occupancy_rate,
    COUNT(*) AS property_count
  FROM `{kawata-dx-poc}.{kawata_dx_cockpit}.real_estate_properties`
  GROUP BY 1
),
facility_by_area AS (
  -- 施設運営: facility_nameでエリア推定
  SELECT
    CASE
      WHEN facility_name LIKE '%函南%' OR facility_name LIKE '%伊豆%' THEN '函南'
      WHEN facility_name LIKE '%三島%' OR facility_name LIKE '%未来%' THEN '三島'
      WHEN facility_name LIKE '%沼津%' THEN '沼津'
      ELSE 'その他'
    END AS area,
    SUM(revenue_kpy) AS facility_revenue_kpy,
    SUM(operating_profit_kpy) AS facility_profit_kpy,
    SUM(visitors) AS total_visitors
  FROM `{kawata-dx-poc}.{kawata_dx_cockpit}.facility_operations`
  GROUP BY 1
),
area_data AS (
  -- エリアマネジメント指標（最新月）
  SELECT
    CASE
      WHEN area_name LIKE '%三島%' THEN '三島'
      WHEN area_name LIKE '%沼津%' THEN '沼津'
      WHEN area_name LIKE '%函南%' THEN '函南'
      ELSE 'その他'
    END AS area,
    AVG(land_price_index) AS avg_land_price_index,
    AVG(population) AS avg_population,
    AVG(foot_traffic) AS avg_foot_traffic
  FROM `{kawata-dx-poc}.{kawata_dx_cockpit}.area_indicators`
  GROUP BY 1
)
SELECT
  COALESCE(c.area, r.area, f.area, a.area) AS area,
  -- 建設事業
  COALESCE(c.construction_revenue_kpy, 0) AS construction_revenue_kpy,
  COALESCE(c.project_count, 0) AS project_count,
  -- 不動産事業
  COALESCE(r.annual_rental_income_kpy, 0) AS annual_rental_income_kpy,
  COALESCE(r.total_property_value_kpy, 0) AS property_value_kpy,
  COALESCE(r.avg_occupancy_rate, 0) AS avg_occupancy_rate,
  -- 施設運営
  COALESCE(f.facility_revenue_kpy, 0) AS facility_revenue_kpy,
  COALESCE(f.facility_profit_kpy, 0) AS facility_profit_kpy,
  COALESCE(f.total_visitors, 0) AS total_visitors,
  -- 総合リターン
  (COALESCE(c.construction_revenue_kpy, 0)
   + COALESCE(r.annual_rental_income_kpy, 0)
   + COALESCE(f.facility_revenue_kpy, 0)) AS total_return_kpy,
  -- エリア指標
  COALESCE(a.avg_land_price_index, 0) AS land_price_index,
  COALESCE(a.avg_population, 0) AS population,
  COALESCE(a.avg_foot_traffic, 0) AS foot_traffic
FROM construction_by_area c
FULL OUTER JOIN real_estate_by_area r ON c.area = r.area
FULL OUTER JOIN facility_by_area f ON COALESCE(c.area, r.area) = f.area
FULL OUTER JOIN area_data a ON COALESCE(c.area, r.area, f.area) = a.area;


-- ---------------------------------------------------------------------------
-- ビュー 4: 全社経営ダッシュボードサマリー
-- 事業部別の主要KPIをワンビューに集約する
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW `{kawata-dx-poc}.{kawata_dx_cockpit}.vw_company_dashboard` AS
WITH construction_kpi AS (
  SELECT
    '建設事業' AS business_unit,
    division AS sub_unit,
    SUM(contract_amount_kpy) AS revenue_kpy,
    COUNT(*) AS count_metric,
    AVG(progress_rate) AS avg_metric
  FROM `{kawata-dx-poc}.{kawata_dx_cockpit}.projects_master`
  GROUP BY division
),
real_estate_kpi AS (
  SELECT
    '不動産事業' AS business_unit,
    '不動産' AS sub_unit,
    SUM(monthly_rental_income_kpy) * 12 AS revenue_kpy,
    COUNT(*) AS count_metric,
    AVG(occupancy_rate) AS avg_metric
  FROM `{kawata-dx-poc}.{kawata_dx_cockpit}.real_estate_properties`
),
facility_kpi AS (
  SELECT
    '施設運営事業' AS business_unit,
    '施設運営' AS sub_unit,
    SUM(revenue_kpy) AS revenue_kpy,
    SUM(visitors) AS count_metric,
    SAFE_DIVIDE(SUM(operating_profit_kpy), SUM(revenue_kpy)) * 100 AS avg_metric
  FROM `{kawata-dx-poc}.{kawata_dx_cockpit}.facility_operations`
),
saas_kpi AS (
  SELECT
    'DX・SaaS事業' AS business_unit,
    product AS sub_unit,
    SUM(mrr_kpy) AS revenue_kpy,
    MAX(customers) AS count_metric,
    AVG(churn_rate_pct) AS avg_metric
  FROM `{kawata-dx-poc}.{kawata_dx_cockpit}.saas_metrics`
  GROUP BY product
)
SELECT * FROM construction_kpi
UNION ALL
SELECT * FROM real_estate_kpi
UNION ALL
SELECT * FROM facility_kpi
UNION ALL
SELECT * FROM saas_kpi;


-- ---------------------------------------------------------------------------
-- ビュー 5: AI原価予測用 特徴量テーブル
-- 機械学習モデルの学習・推論に使用する特徴量を事前算出する
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW `{kawata-dx-poc}.{kawata_dx_cockpit}.vw_ml_features` AS
WITH project_costs AS (
  SELECT
    kawata-dx-poc,
    SUM(amount_kpy) AS total_cost,
    SUM(CASE WHEN status = '確定請求' THEN amount_kpy ELSE 0 END) AS confirmed_cost,
    SUM(CASE WHEN status IN ('現場見込み', '口頭発注') THEN amount_kpy ELSE 0 END) AS forecast_cost,
    SUM(CASE WHEN category = '外注費' THEN amount_kpy ELSE 0 END) AS outsourcing_cost,
    SUM(CASE WHEN category = '材料費' THEN amount_kpy ELSE 0 END) AS material_cost,
    SUM(CASE WHEN category = '労務費' THEN amount_kpy ELSE 0 END) AS labor_cost,
    SUM(CASE WHEN category = '経費' THEN amount_kpy ELSE 0 END) AS expense_cost,
    COUNT(*) AS cost_record_count,
    COUNT(CASE WHEN status = '確定請求' THEN 1 END) AS confirmed_count,
    COUNT(CASE WHEN status IN ('現場見込み', '口頭発注') THEN 1 END) AS forecast_count
  FROM `{kawata-dx-poc}.{kawata_dx_cockpit}.cost_records`
  GROUP BY kawata-dx-poc
)
SELECT
  p.kawata-dx-poc,
  -- ターゲット変数: 実績原価率
  SAFE_DIVIDE(c.total_cost, p.contract_amount_kpy) * 100 AS actual_cost_rate,
  -- 特徴量: 工事属性
  p.division,
  p.client_type,
  p.contract_amount_kpy,
  DATE_DIFF(DATE(p.end_date), DATE(p.start_date), MONTH) AS duration_months,
  p.target_cost_rate,
  p.progress_rate,
  p.status AS project_status,
  -- 特徴量: 原価消化状況
  SAFE_DIVIDE(c.confirmed_cost, p.contract_amount_kpy) * 100 AS confirmed_cost_rate,
  SAFE_DIVIDE(c.forecast_cost, p.contract_amount_kpy) * 100 AS forecast_cost_rate,
  SAFE_DIVIDE(c.confirmed_cost, c.total_cost) * 100 AS confirmed_ratio,
  -- 特徴量: カテゴリ別比率
  SAFE_DIVIDE(c.outsourcing_cost, c.total_cost) * 100 AS outsourcing_pct,
  SAFE_DIVIDE(c.material_cost, c.total_cost) * 100 AS material_pct,
  SAFE_DIVIDE(c.labor_cost, c.total_cost) * 100 AS labor_pct,
  SAFE_DIVIDE(c.expense_cost, c.total_cost) * 100 AS expense_pct,
  -- 特徴量: 原価消化ペース vs 工期進捗
  SAFE_DIVIDE(
    SAFE_DIVIDE(c.total_cost, p.contract_amount_kpy),
    p.progress_rate / 100
  ) AS cost_progress_ratio,
  -- メタデータ
  c.cost_record_count,
  c.confirmed_count,
  c.forecast_count
FROM `{kawata-dx-poc}.{kawata_dx_cockpit}.projects_master` p
LEFT JOIN project_costs c ON p.kawata-dx-poc = c.kawata-dx-poc
WHERE c.total_cost IS NOT NULL;

