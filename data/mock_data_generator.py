"""
加和太建設 DXコックピット PoC用モックデータ生成スクリプト

このスクリプトは、加和太建設の多様な事業（建設、不動産、施設運営、SaaS、まちづくり）を
統合的に可視化・分析する「DXコックピット」のための検証用ダミーデータを生成します。
BigQueryなどのDWHにロードすることを前提としており、AIモデルの学習やBIツールの
ダッシュボード構築に利用可能な、現実的で一貫性のあるデータを生成します。

生成されるデータ (CSV形式, UTF-8 with BOM):
1. projects_master.csv      - 建設プロジェクトマスタ (工期、請負金額、目標原価率、進捗状況など)
2. cost_records.csv         - プロジェクト別原価トランザクション (外注費、材料費、労務費、経費)
3. cash_in_schedules.csv    - 入金予定・実績データ (前払金、中間金、完成金)
4. real_estate_properties.csv - 不動産ポートフォリオデータ (賃貸マンション、商業施設、オフィス等)
5. facility_operations.csv  - 施設運営データ (道の駅、コワーキングスペース等の月次収益・来客数)
6. saas_metrics.csv         - SaaS事業 (IMPACT CONSTRUCTION等) の月次KPI (MRR, Churnなど)
7. area_indicators.csv      - まちづくり指標 (地価、人口、歩行者通行量など)

Usage:
    python mock_data_generator.py
"""

import os
import random
import datetime
import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta

# 再現性確保のためシードを固定
np.random.seed(42)
random.seed(42)

# ====== 定数 ======
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
MONTHS_36 = [datetime.date(2023, 4, 1) + relativedelta(months=i) for i in range(36)]
MONTHS_24 = [datetime.date(2024, 4, 1) + relativedelta(months=i) for i in range(24)]

# 地名リスト（静岡県東部中心）
CITIES = ["三島市", "沼津市", "函南町", "清水町", "長泉町", "伊豆の国市", "伊豆市"]
CLIENT_TYPES = ["官公庁", "民間"]
DIVISIONS = ["土木", "建築"]

def random_date(start, end):
    """指定された期間内のランダムな日付を返す"""
    delta = end - start
    int_delta = (delta.days)
    random_days = random.randrange(int_delta)
    return start + datetime.timedelta(days=random_days)

def generate_projects_master(num_projects=50):
    """建設プロジェクトマスタデータの生成"""
    data = []
    for i in range(1, num_projects + 1):
        project_id = f"PRJ-{str(i).zfill(4)}"
        division = random.choice(DIVISIONS)
        client_type = random.choice(CLIENT_TYPES)
        city = random.choice(CITIES)
        
        if division == "土木":
            name_suffix = random.choice(["道路改良工事", "河川改修工事", "橋梁補修工事", "下水道整備工事"])
            contract_amount = int(np.random.uniform(50000, 1000000)) # 5000万〜10億 (千円)
            target_cost_rate = np.random.uniform(85.0, 90.0)
        else:
            name_suffix = random.choice(["新築工事", "改修工事", "耐震補強工事", "外壁改修工事"])
            contract_amount = int(np.random.uniform(30000, 1500000)) # 3000万〜15億 (千円)
            target_cost_rate = np.random.uniform(82.0, 88.0)
            
        project_name = f"{city}{name_suffix}"
        
        # 工期 (6-24ヶ月)
        duration_months = random.randint(6, 24)
        start_date = random_date(datetime.date(2023, 4, 1), datetime.date(2025, 12, 31))
        end_date = start_date + relativedelta(months=duration_months)
        
        # ステータスと進捗率
        today = datetime.date.today()
        if today < start_date:
            status = "未着工"
            progress_rate = 0.0
        elif today > end_date:
            status = "完了"
            progress_rate = 100.0
        else:
            status = "進行中"
            elapsed = (today - start_date).days
            total = (end_date - start_date).days
            progress_rate = min(100.0, max(0.0, (elapsed / total) * 100 + np.random.normal(0, 5)))
            
        data.append([
            project_id, project_name, division, client_type, 
            contract_amount, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), 
            round(target_cost_rate, 2), round(progress_rate, 2), status
        ])
        
    df = pd.DataFrame(data, columns=[
        "project_id", "project_name", "division", "client_type", 
        "contract_amount_kpy", "start_date", "end_date", 
        "target_cost_rate", "progress_rate", "status"
    ])
    return df

def generate_cost_records(projects_df, num_records=800):
    """プロジェクト別原価トランザクションデータの生成"""
    data = []
    categories = ["外注費", "材料費", "労務費", "経費"]
    category_weights = [0.45, 0.25, 0.20, 0.10]
    statuses = ["確定請求", "現場見込み", "口頭発注"]
    
    # 異常検知(AI)用に一部のプロジェクトを赤字（原価率オーバー）にする
    # 建設業界の実態: 赤字工事は全体の20-30%程度
    over_budget_projects = random.sample(projects_df["project_id"].tolist(), int(len(projects_df) * 0.22))
    
    vendors = [f"協力業者{chr(65+i)}社" for i in range(20)] + [f"資材メーカー{chr(65+i)}" for i in range(10)]
    
    for i in range(1, num_records + 1):
        record_id = f"CST-{str(i).zfill(5)}"
        project = projects_df.sample(1).iloc[0]
        project_id = project["project_id"]
        
        start_date = datetime.datetime.strptime(project["start_date"], "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(project["end_date"], "%Y-%m-%d").date()
        
        # 原価発生月 (工期内のランダムな月)
        if start_date < end_date:
            accrual_date = random_date(start_date, end_date)
        else:
            accrual_date = start_date
            
        accrual_month = accrual_date.replace(day=1)
        payment_due_month = accrual_month + relativedelta(months=1)
        
        # 季節性変動（冬場は進捗が遅れがちになるため少しノイズを入れるなど）
        season_factor = 1.0
        if accrual_month.month in [1, 2]:
            season_factor = 0.8
            
        category = np.random.choice(categories, p=category_weights)
        
        # プロジェクト規模に応じた金額感 (1件あたり)
        base_amount = (project["contract_amount_kpy"] * (project["target_cost_rate"] / 100)) / (num_records / len(projects_df))
        
        # ★ 正常工事と赤字工事で原価発生パターンを分離
        if project_id in over_budget_projects:
            # 赤字工事: 原価が目標を超過する（lognormal期待値 ≈ 1.08）
            amount = int(base_amount * np.random.lognormal(0.05, 0.25) * season_factor)
        else:
            # 正常工事: 原価が目標内に収まる（lognormal期待値 ≈ 0.76）
            amount = int(base_amount * np.random.lognormal(-0.3, 0.2) * season_factor)
        
        # 赤字プロジェクトの場合、工期後半でコストが膨らむ（追加人員・手戻り等）
        if project_id in over_budget_projects and (accrual_date - start_date).days > (end_date - start_date).days * 0.7:
            amount = int(amount * 1.3)
            
        status = np.random.choice(statuses, p=[0.7, 0.2, 0.1])
        vendor_name = random.choice(vendors)
        
        input_timestamp = accrual_date + datetime.timedelta(days=random.randint(1, 10))
        confirmed_timestamp = input_timestamp + datetime.timedelta(days=random.randint(0, 5)) if status == "確定請求" else None
        
        data.append([
            record_id, project_id, category, amount, status, 
            accrual_month.strftime("%Y-%m"), payment_due_month.strftime("%Y-%m"), 
            input_timestamp.strftime("%Y-%m-%dT%H:%M:%S"), 
            confirmed_timestamp.strftime("%Y-%m-%dT%H:%M:%S") if confirmed_timestamp else None,
            vendor_name
        ])
        
    df = pd.DataFrame(data, columns=[
        "record_id", "project_id", "category", "amount_kpy", "status", 
        "accrual_month", "payment_due_month", "input_timestamp", "confirmed_timestamp", "vendor_name"
    ])
    return df

def generate_cash_in_schedules(projects_df):
    """入金予定・実績データの生成"""
    data = []
    schedule_id_counter = 1
    
    # 支払遅延の異常値シミュレーション用
    delayed_projects = random.sample(projects_df["project_id"].tolist(), int(len(projects_df) * 0.1))
    
    for _, project in projects_df.iterrows():
        project_id = project["project_id"]
        contract_amount = project["contract_amount_kpy"]
        start_date = datetime.datetime.strptime(project["start_date"], "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(project["end_date"], "%Y-%m-%d").date()
        
        milestones = [
            ("前払金", 0.4, start_date + relativedelta(months=1)),
            ("中間金", 0.2, start_date + relativedelta(months=max(1, (end_date.year - start_date.year)*12 + end_date.month - start_date.month) // 2)),
            ("完成金", 0.4, end_date + relativedelta(months=1))
        ]
        
        today = datetime.date.today()
        
        for name, ratio, expected_date in milestones:
            schedule_id = f"CSH-{str(schedule_id_counter).zfill(5)}"
            expected_amount = int(contract_amount * ratio)
            deposit_month = expected_date.replace(day=1)
            
            status = "予定"
            actual_amount = None
            actual_deposit_date = None
            
            if expected_date < today:
                if project_id in delayed_projects and name != "前払金":
                    # 遅延シミュレーション
                    if random.random() > 0.5:
                        status = "遅延"
                    else:
                        status = "入金済"
                        actual_deposit_date = expected_date + relativedelta(months=1) + datetime.timedelta(days=random.randint(1,15))
                        actual_amount = expected_amount
                else:
                    status = "入金済"
                    actual_deposit_date = expected_date + datetime.timedelta(days=random.randint(-5, 5))
                    actual_amount = expected_amount
            
            data.append([
                schedule_id, project_id, name, expected_amount, 
                actual_amount, deposit_month.strftime("%Y-%m"), 
                actual_deposit_date.strftime("%Y-%m-%d") if actual_deposit_date else None, 
                status
            ])
            schedule_id_counter += 1
            
    df = pd.DataFrame(data, columns=[
        "schedule_id", "project_id", "milestone", "expected_amount_kpy", 
        "actual_amount_kpy", "deposit_month", "actual_deposit_date", "status"
    ])
    return df

def generate_real_estate_properties(num_properties=25):
    """不動産ポートフォリオデータの生成"""
    data = []
    property_types = ["賃貸マンション", "商業施設", "オフィス", "土地"]
    
    for i in range(1, num_properties + 1):
        property_id = f"RE-{str(i).zfill(3)}"
        prop_type = np.random.choice(property_types, p=[0.5, 0.2, 0.2, 0.1])
        city = random.choice(CITIES)
        property_name = f"加和太{city}{prop_type} {chr(65 + (i % 5))}"
        
        acquisition_date = random_date(datetime.date(2015, 1, 1), datetime.date(2023, 12, 31))
        
        if prop_type == "賃貸マンション":
            acquisition_cost = int(np.random.uniform(50000, 300000))
            monthly_rental = int(acquisition_cost * 0.05 / 12)
            occupancy_rate = np.random.uniform(85.0, 98.0)
        elif prop_type == "商業施設":
            acquisition_cost = int(np.random.uniform(200000, 1000000))
            monthly_rental = int(acquisition_cost * 0.07 / 12)
            occupancy_rate = np.random.uniform(70.0, 100.0)
        elif prop_type == "オフィス":
            acquisition_cost = int(np.random.uniform(100000, 500000))
            monthly_rental = int(acquisition_cost * 0.06 / 12)
            occupancy_rate = np.random.uniform(80.0, 95.0)
        else: # 土地
            acquisition_cost = int(np.random.uniform(30000, 150000))
            monthly_rental = 0
            occupancy_rate = 0.0
            
        # 現在価値 (地価変動を模倣)
        appreciation = np.random.uniform(0.9, 1.3)
        current_value = int(acquisition_cost * appreciation)
        
        data.append([
            property_id, property_name, prop_type, city,
            acquisition_date.strftime("%Y-%m-%d"), acquisition_cost, current_value,
            monthly_rental, round(occupancy_rate, 1)
        ])
        
    df = pd.DataFrame(data, columns=[
        "property_id", "property_name", "property_type", "location",
        "acquisition_date", "acquisition_cost_kpy", "current_value_kpy",
        "monthly_rental_income_kpy", "occupancy_rate"
    ])
    return df

def generate_facility_operations():
    """施設運営データ（道の駅等）の生成"""
    data = []
    facilities = [
        {"id": "FAC-001", "name": "道の駅伊豆ゲートウェイ函南", "type": "large", "seasonality": True},
        {"id": "FAC-002", "name": "ブルワリーレストラン", "type": "medium", "seasonality": False},
        {"id": "FAC-003", "name": "みしま未来研究所", "type": "small", "seasonality": False},
        {"id": "FAC-004", "name": "LtG Startup Studio", "type": "small", "seasonality": False},
    ]
    
    for facility in facilities:
        for month_date in MONTHS_36:
            month_str = month_date.strftime("%Y-%m")
            
            # 季節変動係数（夏場と大型連休に増加）
            season_mult = 1.0
            if facility["seasonality"]:
                if month_date.month in [5, 8]:
                    season_mult = 1.5
                elif month_date.month in [1, 2]:
                    season_mult = 0.7
                    
            if facility["type"] == "large":
                base_visitors = 50000
                revenue_per_visitor = 1.5 # 千円
                base_cost = 40000 # 固定費等 (千円)
            elif facility["type"] == "medium":
                base_visitors = 8000
                revenue_per_visitor = 3.0
                base_cost = 15000
            else:
                base_visitors = 2000
                revenue_per_visitor = 0.5
                base_cost = 3000
                
            visitors = int(base_visitors * np.random.uniform(0.8, 1.2) * season_mult)
            revenue = int(visitors * revenue_per_visitor * np.random.uniform(0.9, 1.1))
            operating_cost = int(base_cost + (revenue * 0.2)) # 変動費加算
            operating_profit = revenue - operating_cost
            
            data.append([
                facility["id"], facility["name"], month_str,
                visitors, revenue, operating_cost, operating_profit
            ])
            
    df = pd.DataFrame(data, columns=[
        "facility_id", "facility_name", "month",
        "visitors", "revenue_kpy", "operating_cost_kpy", "operating_profit_kpy"
    ])
    return df

def generate_saas_metrics():
    """SaaS事業(IMPACT CONSTRUCTION等)のKPIデータ生成"""
    data = []
    products = ["IMPACT CONSTRUCTION", "SCALE"]
    
    for product in products:
        mrr = 5000 if product == "IMPACT CONSTRUCTION" else 2000 # 初期MRR (千円)
        customers = 30 if product == "IMPACT CONSTRUCTION" else 15
        
        for month_date in MONTHS_24:
            month_str = month_date.strftime("%Y-%m")
            
            # 成長をシミュレーション
            new_customers = int(np.random.poisson(3 if product == "IMPACT CONSTRUCTION" else 1))
            churned_customers = int(np.random.binomial(customers, 0.02)) # 約2%の解約率
            
            customers = customers + new_customers - churned_customers
            
            # MRR変動
            new_mrr = new_customers * (150 if product == "IMPACT CONSTRUCTION" else 50)
            expansion_mrr = int(mrr * np.random.uniform(0.01, 0.03))
            churn_mrr = churned_customers * (150 if product == "IMPACT CONSTRUCTION" else 50)
            
            mrr = mrr + new_mrr + expansion_mrr - churn_mrr
            churn_rate = (churned_customers / customers) * 100 if customers > 0 else 0
            
            data.append([
                month_str, product, int(mrr), customers, 
                round(churn_rate, 2), new_customers, int(expansion_mrr)
            ])
            
    df = pd.DataFrame(data, columns=[
        "month", "product", "mrr_kpy", "customers", 
        "churn_rate_pct", "new_customers", "expansion_mrr_kpy"
    ])
    return df

def generate_area_indicators():
    """まちづくり（エリアマネジメント）指標データの生成"""
    data = []
    areas = ["三島", "沼津", "函南"]
    
    for area in areas:
        base_land_price = 100.0
        base_population = 108000 if area == "三島" else (185000 if area == "沼津" else 37000)
        
        for month_date in MONTHS_36:
            month_str = month_date.strftime("%Y-%m")
            
            # 徐々に人口が減少するトレンド + マイクロな増減
            trend_pop = base_population * (1 - 0.005 * (len(data) // 3 / 12))
            population = int(trend_pop + np.random.normal(0, 50))
            
            # 地価は微増トレンド
            land_price_index = base_land_price + (len(data) // 3 / 12) * 1.5 + np.random.normal(0, 0.5)
            
            # 歩行者通行量 (季節性あり)
            foot_traffic = int(np.random.normal(20000 if area == "三島" else 15000, 2000))
            if month_date.month in [4, 5, 8, 12]:
                foot_traffic = int(foot_traffic * 1.2)
                
            new_business_count = np.random.poisson(2)
            event_count = np.random.poisson(3 if area == "三島" else 1)
            
            data.append([
                area, month_str, round(land_price_index, 1), 
                population, foot_traffic, new_business_count, event_count
            ])
            
    df = pd.DataFrame(data, columns=[
        "area_name", "month", "land_price_index", 
        "population", "foot_traffic", "new_business_count", "event_count"
    ])
    return df

def main():
    print("DXコックピット PoC用モックデータの生成を開始します...")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 1. 建設プロジェクトマスタ（200件: ML学習に十分なデータ量）
    projects_df = generate_projects_master(200)
    projects_df.to_csv(os.path.join(OUTPUT_DIR, "projects_master.csv"), index=False, encoding="utf-8-sig")
    print("- projects_master.csv を作成しました。")
    
    # 2. 原価トランザクション（2000件: プロジェクトあたり平均約10件）
    cost_records_df = generate_cost_records(projects_df, 2000)
    cost_records_df.to_csv(os.path.join(OUTPUT_DIR, "cost_records.csv"), index=False, encoding="utf-8-sig")
    print("- cost_records.csv を作成しました。")
    
    # 3. 入金予定・実績
    cash_in_schedules_df = generate_cash_in_schedules(projects_df)
    cash_in_schedules_df.to_csv(os.path.join(OUTPUT_DIR, "cash_in_schedules.csv"), index=False, encoding="utf-8-sig")
    print("- cash_in_schedules.csv を作成しました。")
    
    # 4. 不動産ポートフォリオ
    real_estate_df = generate_real_estate_properties(25)
    real_estate_df.to_csv(os.path.join(OUTPUT_DIR, "real_estate_properties.csv"), index=False, encoding="utf-8-sig")
    print("- real_estate_properties.csv を作成しました。")
    
    # 5. 施設運営データ
    facility_df = generate_facility_operations()
    facility_df.to_csv(os.path.join(OUTPUT_DIR, "facility_operations.csv"), index=False, encoding="utf-8-sig")
    print("- facility_operations.csv を作成しました。")
    
    # 6. SaaS KPI
    saas_df = generate_saas_metrics()
    saas_df.to_csv(os.path.join(OUTPUT_DIR, "saas_metrics.csv"), index=False, encoding="utf-8-sig")
    print("- saas_metrics.csv を作成しました。")
    
    # 7. まちづくり指標
    area_df = generate_area_indicators()
    area_df.to_csv(os.path.join(OUTPUT_DIR, "area_indicators.csv"), index=False, encoding="utf-8-sig")
    print("- area_indicators.csv を作成しました。")
    
    print(f"\nすべてのデータ生成が完了しました。出力先: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
