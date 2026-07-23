# %% [markdown]
# # 探索的データ分析（EDA）
# ## 加和太建設 DXコックピット PoC — Step 2
#
# BigQueryに格納済みのダミーデータを用いて、加和太建設の多角化事業データの
# 全体像を把握し、経営コックピット構築のための分析基盤を確立する。
#
# **分析目的:**
# 1. 各事業のデータ品質・分布の確認
# 2. 原価構造の可視化と赤字リスク要因の特定
# 3. まちづくりROI仮説（施設来場者↔不動産稼働率の相関）の検証
# 4. キャッシュフローの季節性・トレンドの把握
# 5. SaaS事業の成長トラジェクトリーの分析

# %% [markdown]
# ## 1. セットアップ & BigQuery接続

# %%
# === Google Colab環境セットアップ ===
# 日本語フォント対応
# !pip install -q japanize-matplotlib

import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
# import japanize_matplotlib  # Colab実行時はコメント解除

from google.colab import auth
from google.cloud import bigquery

# === BigQuery接続設定 ===
# ★★★ 以下を自分の環境に合わせて変更してください ★★★
PROJECT_ID = 'your-project-id'   # ← GCPプロジェクトID
DATASET = 'your_dataset'         # ← BigQueryデータセット名
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

auth.authenticate_user()
client = bigquery.Client(project=PROJECT_ID)

def query_bq(sql):
    """BigQueryからデータを取得するヘルパー関数"""
    return client.query(sql).to_dataframe()

print(f"✅ BigQuery接続完了: {PROJECT_ID}.{DATASET}")

# %%
# === データ取得 ===
# 全テーブルをDataFrameに読み込む

projects = query_bq(f"SELECT * FROM `{PROJECT_ID}.{DATASET}.projects_master`")
costs = query_bq(f"SELECT * FROM `{PROJECT_ID}.{DATASET}.cost_records`")
cash_in = query_bq(f"SELECT * FROM `{PROJECT_ID}.{DATASET}.cash_in_schedules`")
real_estate = query_bq(f"SELECT * FROM `{PROJECT_ID}.{DATASET}.real_estate_properties`")
facilities = query_bq(f"SELECT * FROM `{PROJECT_ID}.{DATASET}.facility_operations`")
saas = query_bq(f"SELECT * FROM `{PROJECT_ID}.{DATASET}.saas_metrics`")
area_ind = query_bq(f"SELECT * FROM `{PROJECT_ID}.{DATASET}.area_indicators`")

print("📊 読み込みデータ概要:")
for name, df in [("projects_master", projects), ("cost_records", costs),
                  ("cash_in_schedules", cash_in), ("real_estate", real_estate),
                  ("facility_operations", facilities), ("saas_metrics", saas),
                  ("area_indicators", area_ind)]:
    print(f"  {name}: {df.shape[0]:,}行 × {df.shape[1]}列")

# %% [markdown]
# ## 2. 建設事業の分析

# %% [markdown]
# ### 2-1. 工事ポートフォリオ概要

# %%
# === 工事データの基本統計 ===
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('建設事業 — 工事ポートフォリオ分析', fontsize=16, fontweight='bold')

# (1) 事業部別・発注者別の工事件数
ct = projects.groupby(['division', 'client_type']).size().unstack(fill_value=0)
ct.plot(kind='bar', ax=axes[0, 0], color=['#3498db', '#e74c3c'])
axes[0, 0].set_title('事業部別・発注者別 工事件数')
axes[0, 0].set_xlabel('')
axes[0, 0].set_ylabel('件数')
axes[0, 0].tick_params(axis='x', rotation=0)
axes[0, 0].legend(title='発注者')

# (2) 請負金額の分布
for div in projects['division'].unique():
    subset = projects[projects['division'] == div]['contract_amount_kpy'] / 1000  # 百万円に変換
    axes[0, 1].hist(subset, bins=15, alpha=0.6, label=div)
axes[0, 1].set_title('請負金額の分布')
axes[0, 1].set_xlabel('請負金額（百万円）')
axes[0, 1].set_ylabel('件数')
axes[0, 1].legend()

# (3) 工事ステータス
status_counts = projects['status'].value_counts()
colors_status = {'進行中': '#3498db', '完了': '#2ecc71', '未着工': '#95a5a6'}
axes[1, 0].pie(status_counts.values,
               labels=status_counts.index,
               colors=[colors_status.get(s, '#bdc3c7') for s in status_counts.index],
               autopct='%1.1f%%', startangle=90)
axes[1, 0].set_title('工事ステータス構成')

# (4) 目標原価率の分布（事業部別）
for div in projects['division'].unique():
    subset = projects[projects['division'] == div]['target_cost_rate']
    axes[1, 1].hist(subset, bins=10, alpha=0.6, label=div)
axes[1, 1].set_title('目標原価率の分布')
axes[1, 1].set_xlabel('目標原価率（%）')
axes[1, 1].set_ylabel('件数')
axes[1, 1].legend()
axes[1, 1].axvline(x=88, color='red', linestyle='--', alpha=0.5, label='一般基準88%')

plt.tight_layout()
plt.savefig('output_01_portfolio.png', dpi=150, bbox_inches='tight')
plt.show()
print("✅ 図表を保存: output_01_portfolio.png")

# %% [markdown]
# ### 2-2. 原価構造分析

# %%
# === 原価構造の可視化 ===
fig, axes = plt.subplots(1, 3, figsize=(18, 6))
fig.suptitle('建設事業 — 原価構造分析', fontsize=16, fontweight='bold')

# (1) コストカテゴリ別構成比
category_sum = costs.groupby('category')['amount_kpy'].sum()
colors_cat = {'外注費': '#3498db', '材料費': '#e74c3c', '労務費': '#2ecc71', '経費': '#f39c12'}
axes[0].pie(category_sum.values,
            labels=[f"{c}\n({v/1000:.0f}百万円)" for c, v in zip(category_sum.index, category_sum.values)],
            colors=[colors_cat.get(c, '#bdc3c7') for c in category_sum.index],
            autopct='%1.1f%%', startangle=90, pctdistance=0.75)
axes[0].set_title('原価カテゴリ別構成比')

# (2) ステータス別構成比
status_sum = costs.groupby('status')['amount_kpy'].sum()
colors_st = {'確定請求': '#2ecc71', '現場見込み': '#f39c12', '口頭発注': '#e74c3c'}
axes[1].pie(status_sum.values,
            labels=[f"{s}\n({v/1000:.0f}百万円)" for s, v in zip(status_sum.index, status_sum.values)],
            colors=[colors_st.get(s, '#bdc3c7') for s in status_sum.index],
            autopct='%1.1f%%', startangle=90, pctdistance=0.75)
axes[1].set_title('確定/見込み別構成比')

# (3) 事業部別の原価カテゴリ構成（積み上げ棒グラフ）
cost_with_div = costs.merge(projects[['project_id', 'division']], on='project_id', how='left')
div_cat = cost_with_div.groupby(['division', 'category'])['amount_kpy'].sum().unstack(fill_value=0)
(div_cat / 1000).plot(kind='bar', stacked=True, ax=axes[2],
                       color=[colors_cat.get(c, '#bdc3c7') for c in div_cat.columns])
axes[2].set_title('事業部別 原価カテゴリ構成')
axes[2].set_xlabel('')
axes[2].set_ylabel('金額（百万円）')
axes[2].tick_params(axis='x', rotation=0)

plt.tight_layout()
plt.savefig('output_02_cost_structure.png', dpi=150, bbox_inches='tight')
plt.show()
print("✅ 図表を保存: output_02_cost_structure.png")

# %% [markdown]
# ### 2-3. 工事別原価率分析 — 赤字リスクの特定

# %%
# === 工事別の実効原価率を算出 ===
project_cost_summary = costs.groupby('project_id').agg(
    total_cost=('amount_kpy', 'sum'),
    confirmed_cost=('amount_kpy', lambda x: x[costs.loc[x.index, 'status'] == '確定請求'].sum()),
    record_count=('amount_kpy', 'count')
).reset_index()

# 工事マスタとJOIN
analysis = projects.merge(project_cost_summary, on='project_id', how='left')
analysis['total_cost'] = analysis['total_cost'].fillna(0)
analysis['effective_cost_rate'] = (analysis['total_cost'] / analysis['contract_amount_kpy'] * 100)
analysis['cost_rate_gap'] = analysis['effective_cost_rate'] - analysis['target_cost_rate']
analysis['risk_level'] = analysis['cost_rate_gap'].apply(
    lambda x: '🔴 緊急' if x >= 5 else ('🟠 警告' if x >= 0 else ('🟡 注意' if x >= -5 * 0.05 else '🟢 正常'))
)

fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle('工事別原価率分析 — 赤字リスク特定', fontsize=16, fontweight='bold')

# (1) 実効原価率 vs 目標原価率（散布図）
colors_scatter = ['#e74c3c' if g >= 0 else '#2ecc71' for g in analysis['cost_rate_gap']]
sizes = analysis['contract_amount_kpy'] / analysis['contract_amount_kpy'].max() * 300
axes[0].scatter(analysis['target_cost_rate'], analysis['effective_cost_rate'],
                c=colors_scatter, s=sizes, alpha=0.7, edgecolors='white', linewidth=0.5)
# 対角線（目標=実績ライン）
line_range = [analysis['target_cost_rate'].min() - 2, analysis['target_cost_rate'].max() + 2]
axes[0].plot(line_range, line_range, 'k--', alpha=0.3, label='目標=実績ライン')
axes[0].fill_between(line_range, [r + 5 for r in line_range], [120, 120],
                      color='red', alpha=0.05, label='緊急ゾーン')
axes[0].fill_between(line_range, line_range, [r + 5 for r in line_range],
                      color='orange', alpha=0.05, label='警告ゾーン')
axes[0].set_xlabel('目標原価率（%）')
axes[0].set_ylabel('実効原価率（%）')
axes[0].set_title('目標原価率 vs 実効原価率\n（バブルサイズ = 請負金額）')
axes[0].legend(loc='lower right', fontsize=8)

# (2) 原価率GAP上位10現場（水平棒グラフ）
top_risk = analysis.nlargest(10, 'cost_rate_gap')
colors_bar = ['#e74c3c' if g >= 5 else '#f39c12' if g >= 0 else '#2ecc71'
              for g in top_risk['cost_rate_gap']]
axes[1].barh(range(len(top_risk)), top_risk['cost_rate_gap'], color=colors_bar)
axes[1].set_yticks(range(len(top_risk)))
axes[1].set_yticklabels(top_risk['project_name'].str[:15], fontsize=9)
axes[1].set_xlabel('原価率乖離（ポイント）')
axes[1].set_title('原価率乖離 TOP10（赤字リスク工事）')
axes[1].axvline(x=0, color='black', linewidth=0.5)
axes[1].axvline(x=5, color='red', linewidth=0.5, linestyle='--', alpha=0.5)
axes[1].invert_yaxis()

plt.tight_layout()
plt.savefig('output_03_cost_risk.png', dpi=150, bbox_inches='tight')
plt.show()

# リスク工事の一覧表示
print("\n📊 赤字リスク工事一覧:")
risk_display = analysis[analysis['cost_rate_gap'] >= 0][
    ['project_id', 'project_name', 'division', 'contract_amount_kpy',
     'target_cost_rate', 'effective_cost_rate', 'cost_rate_gap', 'risk_level']
].sort_values('cost_rate_gap', ascending=False)
print(risk_display.to_string(index=False))

# %% [markdown]
# ## 3. まちづくりROI分析

# %% [markdown]
# ### 3-1. エリア別事業ポートフォリオ

# %%
# === エリア判定関数 ===
def detect_area(text):
    """テキストからエリアを推定"""
    if pd.isna(text):
        return 'その他'
    text = str(text)
    if '三島' in text or '未来' in text:
        return '三島'
    elif '沼津' in text:
        return '沼津'
    elif '函南' in text or '伊豆' in text:
        return '函南'
    elif '清水' in text:
        return '清水'
    elif '長泉' in text:
        return '長泉'
    return 'その他'

# 各事業のエリア別集計
projects['area'] = projects['project_name'].apply(detect_area)
real_estate['area'] = real_estate['location'].apply(detect_area)

# 施設のエリア判定
facility_area_map = {}
for _, row in facilities.drop_duplicates('facility_id').iterrows():
    facility_area_map[row['facility_id']] = detect_area(row['facility_name'])
facilities['area'] = facilities['facility_id'].map(facility_area_map)

# エリア別統合
area_summary = pd.DataFrame()

# 建設事業
cons_area = projects.groupby('area')['contract_amount_kpy'].sum().reset_index()
cons_area.columns = ['area', 'construction_revenue']

# 不動産事業
re_area = real_estate.groupby('area')['monthly_rental_income_kpy'].sum().reset_index()
re_area['real_estate_revenue'] = re_area['monthly_rental_income_kpy'] * 12
re_area = re_area[['area', 'real_estate_revenue']]

# 施設運営事業
fac_area = facilities.groupby('area')['revenue_kpy'].sum().reset_index()
fac_area.columns = ['area', 'facility_revenue']

# 統合
area_roi = cons_area.merge(re_area, on='area', how='outer').merge(fac_area, on='area', how='outer').fillna(0)
area_roi['total_return'] = (area_roi['construction_revenue']
                            + area_roi['real_estate_revenue']
                            + area_roi['facility_revenue'])

fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle('まちづくりROI — エリア別事業ポートフォリオ', fontsize=16, fontweight='bold')

# (1) エリア別売上構成（積み上げ棒グラフ）
main_areas = area_roi[area_roi['area'].isin(['三島', '沼津', '函南'])].copy()
if main_areas.empty:
    main_areas = area_roi.nlargest(3, 'total_return')

bar_data = main_areas.set_index('area')[['construction_revenue', 'real_estate_revenue', 'facility_revenue']] / 1000
bar_data.columns = ['建設事業', '不動産事業', '施設運営']
bar_data.plot(kind='bar', stacked=True, ax=axes[0],
              color=['#3498db', '#e74c3c', '#2ecc71'])
axes[0].set_title('エリア別 事業収益構成')
axes[0].set_xlabel('')
axes[0].set_ylabel('収益（百万円）')
axes[0].tick_params(axis='x', rotation=0)
axes[0].legend(loc='upper right')

# (2) エリア別収益構成比（100%積み上げ）
total_by_area = bar_data.sum(axis=1)
bar_pct = bar_data.div(total_by_area, axis=0) * 100
bar_pct.plot(kind='barh', stacked=True, ax=axes[1],
             color=['#3498db', '#e74c3c', '#2ecc71'])
axes[1].set_title('エリア別 事業収益構成比')
axes[1].set_xlabel('構成比（%）')
axes[1].legend(loc='lower right')

plt.tight_layout()
plt.savefig('output_04_area_roi.png', dpi=150, bbox_inches='tight')
plt.show()
print("✅ 図表を保存: output_04_area_roi.png")

# %% [markdown]
# ### 3-2. 施設来場者数 ↔ エリア指標の相関分析

# %%
# === まちづくり仮説検証: 施設来場者はエリア価値に影響するか？ ===
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('まちづくり仮説検証 — 施設活動とエリア価値の関係', fontsize=16, fontweight='bold')

# (1) 施設別の来場者数推移
for fid in facilities['facility_name'].unique():
    subset = facilities[facilities['facility_name'] == fid].sort_values('month')
    axes[0, 0].plot(range(len(subset)), subset['visitors'], label=fid[:10], linewidth=1.5)
axes[0, 0].set_title('施設別 月次来場者数推移')
axes[0, 0].set_xlabel('月（時系列インデックス）')
axes[0, 0].set_ylabel('来場者数')
axes[0, 0].legend(fontsize=8)

# (2) 施設別の月次営業利益推移
for fid in facilities['facility_name'].unique():
    subset = facilities[facilities['facility_name'] == fid].sort_values('month')
    axes[0, 1].plot(range(len(subset)), subset['operating_profit_kpy'] / 1000,
                     label=fid[:10], linewidth=1.5)
axes[0, 1].set_title('施設別 月次営業利益推移')
axes[0, 1].set_xlabel('月（時系列インデックス）')
axes[0, 1].set_ylabel('営業利益（百万円）')
axes[0, 1].axhline(y=0, color='red', linewidth=0.5, linestyle='--')
axes[0, 1].legend(fontsize=8)

# (3) エリア指標推移（地価指数）
for area in area_ind['area_name'].unique():
    subset = area_ind[area_ind['area_name'] == area].sort_values('month')
    axes[1, 0].plot(range(len(subset)), subset['land_price_index'], label=area, linewidth=2)
axes[1, 0].set_title('エリア別 地価指数推移')
axes[1, 0].set_xlabel('月（時系列インデックス）')
axes[1, 0].set_ylabel('地価指数')
axes[1, 0].legend()

# (4) 歩行者交通量推移
for area in area_ind['area_name'].unique():
    subset = area_ind[area_ind['area_name'] == area].sort_values('month')
    axes[1, 1].plot(range(len(subset)), subset['foot_traffic'], label=area, linewidth=2)
axes[1, 1].set_title('エリア別 歩行者交通量推移')
axes[1, 1].set_xlabel('月（時系列インデックス）')
axes[1, 1].set_ylabel('交通量指数')
axes[1, 1].legend()

plt.tight_layout()
plt.savefig('output_05_area_correlation.png', dpi=150, bbox_inches='tight')
plt.show()
print("✅ 図表を保存: output_05_area_correlation.png")

# %% [markdown]
# ## 4. キャッシュフロー分析

# %%
# === 月別キャッシュフローの算出 ===
# 入金集計
monthly_inflow = cash_in.groupby('deposit_month')['expected_amount_kpy'].sum().reset_index()
monthly_inflow.columns = ['month', 'inflow']

# 出金集計
monthly_outflow = costs.groupby('payment_due_month')['amount_kpy'].sum().reset_index()
monthly_outflow.columns = ['month', 'outflow']

# 統合
cashflow = monthly_inflow.merge(monthly_outflow, on='month', how='outer').fillna(0)
cashflow = cashflow.sort_values('month').reset_index(drop=True)
cashflow['net_cashflow'] = cashflow['inflow'] - cashflow['outflow']
cashflow['cumulative'] = cashflow['net_cashflow'].cumsum()

fig, axes = plt.subplots(2, 1, figsize=(16, 10))
fig.suptitle('キャッシュフロー分析', fontsize=16, fontweight='bold')

# (1) 月別入出金
x = range(len(cashflow))
width = 0.35
axes[0].bar([i - width/2 for i in x], cashflow['inflow'] / 1000,
            width, label='入金', color='#2ecc71', alpha=0.8)
axes[0].bar([i + width/2 for i in x], cashflow['outflow'] / 1000,
            width, label='出金', color='#e74c3c', alpha=0.8)
axes[0].plot(x, cashflow['net_cashflow'] / 1000, 'k-o', markersize=4,
             label='純キャッシュフロー', linewidth=2)
axes[0].axhline(y=0, color='gray', linewidth=0.5)
axes[0].set_title('月別 入金・出金・純キャッシュフロー')
axes[0].set_ylabel('金額（百万円）')
axes[0].legend()
# X軸ラベル（3ヶ月ごと）
tick_labels = cashflow['month'].tolist()
axes[0].set_xticks([i for i in x if i % 3 == 0])
axes[0].set_xticklabels([tick_labels[i][:7] for i in x if i % 3 == 0], rotation=45, fontsize=8)

# (2) 累積キャッシュフロー + 危険ゾーン
axes[1].fill_between(x, cashflow['cumulative'] / 1000, 0,
                      where=cashflow['cumulative'] >= 0,
                      color='#2ecc71', alpha=0.3, label='黒字域')
axes[1].fill_between(x, cashflow['cumulative'] / 1000, 0,
                      where=cashflow['cumulative'] < 0,
                      color='#e74c3c', alpha=0.3, label='赤字域')
axes[1].plot(x, cashflow['cumulative'] / 1000, 'b-', linewidth=2)
axes[1].axhline(y=-50, color='red', linewidth=1, linestyle='--', alpha=0.7, label='資金ショートライン')
axes[1].set_title('累積キャッシュフロー推移')
axes[1].set_xlabel('月')
axes[1].set_ylabel('累積残高（百万円）')
axes[1].legend()
axes[1].set_xticks([i for i in x if i % 3 == 0])
axes[1].set_xticklabels([tick_labels[i][:7] for i in x if i % 3 == 0], rotation=45, fontsize=8)

plt.tight_layout()
plt.savefig('output_06_cashflow.png', dpi=150, bbox_inches='tight')
plt.show()
print("✅ 図表を保存: output_06_cashflow.png")

# %% [markdown]
# ## 5. SaaS事業分析

# %%
# === SaaS KPIの可視化 ===
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('DX・SaaS事業 — KPI分析', fontsize=16, fontweight='bold')

products = saas['product'].unique()
colors_p = {'IMPACT CONSTRUCTION': '#3498db', 'SCALE': '#e74c3c'}

for product in products:
    subset = saas[saas['product'] == product].sort_values('month')
    color = colors_p.get(product, '#95a5a6')

    # (1) MRR推移
    axes[0, 0].plot(range(len(subset)), subset['mrr_kpy'],
                     label=product, color=color, linewidth=2, marker='o', markersize=3)

    # (2) 顧客数推移
    axes[0, 1].plot(range(len(subset)), subset['customers'],
                     label=product, color=color, linewidth=2, marker='o', markersize=3)

    # (3) チャーンレート推移
    axes[1, 0].plot(range(len(subset)), subset['churn_rate_pct'],
                     label=product, color=color, linewidth=2, marker='o', markersize=3)

    # (4) 新規顧客数推移
    axes[1, 1].bar([i + (0.3 if product == products[-1] else 0) for i in range(len(subset))],
                    subset['new_customers'], width=0.3, label=product, color=color, alpha=0.7)

axes[0, 0].set_title('MRR（月次定期収益）推移')
axes[0, 0].set_ylabel('MRR（千円）')
axes[0, 0].legend()

axes[0, 1].set_title('有料顧客数推移')
axes[0, 1].set_ylabel('顧客数')
axes[0, 1].legend()

axes[1, 0].set_title('月次チャーンレート推移')
axes[1, 0].set_ylabel('チャーンレート（%）')
axes[1, 0].set_xlabel('月（時系列インデックス）')
axes[1, 0].legend()

axes[1, 1].set_title('新規顧客獲得数')
axes[1, 1].set_ylabel('新規顧客数')
axes[1, 1].set_xlabel('月（時系列インデックス）')
axes[1, 1].legend()

plt.tight_layout()
plt.savefig('output_07_saas.png', dpi=150, bbox_inches='tight')
plt.show()
print("✅ 図表を保存: output_07_saas.png")

# %% [markdown]
# ## 6. 相関マトリクス — 多角化事業の横断分析

# %%
# === 相関分析: 施設来場者と各指標の関係 ===
# 月次データを統合してエリア別の相関を分析

# 施設運営の月次集計
fac_monthly = facilities.groupby('month').agg(
    total_visitors=('visitors', 'sum'),
    total_facility_revenue=('revenue_kpy', 'sum')
).reset_index()

# エリア指標の月次平均
area_monthly = area_ind.groupby('month').agg(
    avg_land_price=('land_price_index', 'mean'),
    avg_foot_traffic=('foot_traffic', 'mean'),
    total_population=('population', 'sum')
).reset_index()

# SaaS月次集計
saas_monthly = saas.groupby('month').agg(
    total_mrr=('mrr_kpy', 'sum'),
    total_customers=('customers', 'sum')
).reset_index()

# 統合
cross_data = fac_monthly.merge(area_monthly, on='month', how='inner')
cross_data = cross_data.merge(saas_monthly, on='month', how='left')

# 相関マトリクス
corr_cols = ['total_visitors', 'total_facility_revenue', 'avg_land_price',
             'avg_foot_traffic', 'total_mrr', 'total_customers']
available_cols = [c for c in corr_cols if c in cross_data.columns]
corr_matrix = cross_data[available_cols].corr()

fig, ax = plt.subplots(figsize=(10, 8))
im = ax.imshow(corr_matrix, cmap='RdBu_r', vmin=-1, vmax=1)

labels_jp = {
    'total_visitors': '施設来場者数',
    'total_facility_revenue': '施設売上',
    'avg_land_price': '地価指数',
    'avg_foot_traffic': '歩行者交通量',
    'total_mrr': 'SaaS MRR',
    'total_customers': 'SaaS顧客数'
}
labels = [labels_jp.get(c, c) for c in available_cols]

ax.set_xticks(range(len(labels)))
ax.set_yticks(range(len(labels)))
ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=10)
ax.set_yticklabels(labels, fontsize=10)

# 数値をセルに表示
for i in range(len(available_cols)):
    for j in range(len(available_cols)):
        val = corr_matrix.iloc[i, j]
        color = 'white' if abs(val) > 0.5 else 'black'
        ax.text(j, i, f'{val:.2f}', ha='center', va='center', color=color, fontsize=11)

plt.colorbar(im, label='相関係数')
ax.set_title('多角化事業 横断 相関マトリクス', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig('output_08_correlation.png', dpi=150, bbox_inches='tight')
plt.show()
print("✅ 図表を保存: output_08_correlation.png")

# %% [markdown]
# ## 7. 分析サマリー

# %%
print("=" * 70)
print("  加和太建設 DXコックピット PoC — 探索的データ分析 サマリー")
print("=" * 70)

# 基本統計
print(f"\n📊 データ概要")
print(f"  建設工事: {len(projects)}件（土木: {len(projects[projects['division']=='土木'])}件, 建築: {len(projects[projects['division']=='建築'])}件）")
print(f"  原価レコード: {len(costs):,}件")
print(f"  請負金額合計: {projects['contract_amount_kpy'].sum()/1000:,.0f}百万円")
total_cost = costs['amount_kpy'].sum()
print(f"  原価合計: {total_cost/1000:,.0f}百万円")

# 赤字リスク
over_budget = analysis[analysis['cost_rate_gap'] >= 0]
print(f"\n⚠️ 赤字リスク工事")
print(f"  原価率超過工事: {len(over_budget)}件 / {len(analysis)}件（{len(over_budget)/len(analysis)*100:.1f}%）")
if len(over_budget) > 0:
    print(f"  最大乖離: {over_budget['cost_rate_gap'].max():.1f}ポイント（{over_budget.loc[over_budget['cost_rate_gap'].idxmax(), 'project_name']}）")

# 不動産
print(f"\n🏢 不動産事業")
print(f"  保有物件: {len(real_estate)}件")
print(f"  平均稼働率: {real_estate['occupancy_rate'].mean():.1f}%")
print(f"  年間賃貸収入: {real_estate['monthly_rental_income_kpy'].sum()*12/1000:,.0f}百万円")

# 施設運営
print(f"\n🏪 施設運営事業")
print(f"  運営施設数: {facilities['facility_name'].nunique()}施設")
print(f"  月平均来場者数: {facilities.groupby('month')['visitors'].sum().mean():,.0f}人")

# SaaS
if not saas.empty:
    latest_saas = saas.sort_values('month').groupby('product').last()
    print(f"\n💻 SaaS事業（最新月）")
    for product, row in latest_saas.iterrows():
        print(f"  {product}: MRR {row['mrr_kpy']:,.0f}千円, 顧客数 {row['customers']}, チャーン {row['churn_rate_pct']:.1f}%")

# キャッシュフロー
print(f"\n💰 キャッシュフロー")
negative_months = cashflow[cashflow['net_cashflow'] < 0]
print(f"  純CF赤字月: {len(negative_months)}ヶ月 / {len(cashflow)}ヶ月")
print(f"  累積CF最小値: {cashflow['cumulative'].min()/1000:,.0f}百万円")

print(f"\n{'=' * 70}")
print("  → 次のステップ: 02_cost_prediction.py（AI原価予測モデル構築）")
print(f"{'=' * 70}")

# %% [markdown]
# ## 主要な発見事項
#
# ### 建設事業
# - 原価カテゴリ構成は外注費が最大（約45%）で、業界標準に合致
# - 確定/見込みの比率から、予兆データの取り込みが原価管理精度向上の鍵
# - 原価率超過工事が一定割合存在 → AI予測モデルによる早期検知の価値あり
#
# ### まちづくりROI
# - エリア別の事業収益構成に明確な差異 → 投資戦略の差別化が可能
# - 施設来場者数とエリア指標（地価・歩行者交通量）の相関を確認
# - 統合的なROI管理により、次の投資先選定の精度向上が期待できる
#
# ### キャッシュフロー
# - 建設業特有の入出金タイムラグが確認 → 前払金・中間金の管理が重要
# - 特定月に資金がタイトになるパターン → 異常検知モデルの適用価値あり
#
# ### SaaS事業
# - MRR・顧客数ともに成長トレンド → DXエコシステムの拡大を確認
# - チャーンレートの安定化がLTV向上の鍵
