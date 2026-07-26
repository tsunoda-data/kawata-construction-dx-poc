# %% [markdown]
# # 探索的データ分析（EDA）
# ## 加和太建設 DXコックピット PoC — Step 2

# %%
# === 1. セットアップ & 日本語フォントインストール ===
!pip install -q japanize-matplotlib

import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import japanize_matplotlib

from google.colab import auth
from google.cloud import bigquery

# === BigQuery接続設定 ===
PROJECT_ID = 'kawata-dx-poc'      # ← GCPプロジェクトID
DATASET = 'kawata_dx_cockpit'     # ← BigQueryデータセット名

auth.authenticate_user()
client = bigquery.Client(project=PROJECT_ID)

def query_bq(sql):
    """BigQueryからデータを取得するヘルパー関数"""
    return client.query(sql).to_dataframe()

print(f"✅ BigQuery接続完了: {PROJECT_ID}.{DATASET}")

# %%
# === 2. データ取得 ===
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
# ## 3. 建設事業の分析

# %%
# === 3-1. 工事ポートフォリオ概要 ===
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('建設事業 — 工事ポートフォリオ分析', fontsize=16, fontweight='bold')

ct = projects.groupby(['division', 'client_type']).size().unstack(fill_value=0)
ct.plot(kind='bar', ax=axes[0, 0], color=['#3498db', '#e74c3c'])
axes[0, 0].set_title('事業部別・発注者別 工事件数')
axes[0, 0].set_xlabel('')
axes[0, 0].set_ylabel('件数')
axes[0, 0].tick_params(axis='x', rotation=0)
axes[0, 0].legend(title='発注者')

for div in projects['division'].unique():
    subset = projects[projects['division'] == div]['contract_amount_kpy'] / 1000
    axes[0, 1].hist(subset, bins=15, alpha=0.6, label=div)
axes[0, 1].set_title('請負金額の分布')
axes[0, 1].set_xlabel('請負金額（百万円）')
axes[0, 1].set_ylabel('件数')
axes[0, 1].legend()

status_counts = projects['status'].value_counts()
colors_status = {'進行中': '#3498db', '完了': '#2ecc71', '未着工': '#95a5a6'}
axes[1, 0].pie(status_counts.values,
               labels=status_counts.index,
               colors=[colors_status.get(s, '#bdc3c7') for s in status_counts.index],
               autopct='%1.1f%%', startangle=90)
axes[1, 0].set_title('工事ステータス構成')

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

# %%
# === 3-2. 原価構造分析 ===
fig, axes = plt.subplots(1, 3, figsize=(18, 6))
fig.suptitle('建設事業 — 原価構造分析', fontsize=16, fontweight='bold')

category_sum = costs.groupby('category')['amount_kpy'].sum()
colors_cat = {'外注費': '#3498db', '材料費': '#e74c3c', '労務費': '#2ecc71', '経費': '#f39c12'}
axes[0].pie(category_sum.values,
            labels=[f"{c}\n({v/1000:.0f}百万円)" for c, v in zip(category_sum.index, category_sum.values)],
            colors=[colors_cat.get(c, '#bdc3c7') for c in category_sum.index],
            autopct='%1.1f%%', startangle=90, pctdistance=0.75)
axes[0].set_title('原価カテゴリ別構成比')

status_sum = costs.groupby('status')['amount_kpy'].sum()
colors_st = {'確定請求': '#2ecc71', '現場見込み': '#f39c12', '口頭発注': '#e74c3c'}
axes[1].pie(status_sum.values,
            labels=[f"{s}\n({v/1000:.0f}百万円)" for s, v in zip(status_sum.index, status_sum.values)],
            colors=[colors_st.get(s, '#bdc3c7') for s in status_sum.index],
            autopct='%1.1f%%', startangle=90, pctdistance=0.75)
axes[1].set_title('確定/見込み別構成比')

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

# %%
# === 3-3. 赤字リスク特定 ===
project_cost_summary = costs.groupby('project_id').agg(
    total_cost=('amount_kpy', 'sum'),
    confirmed_cost=('amount_kpy', lambda x: x[costs.loc[x.index, 'status'] == '確定請求'].sum()),
    record_count=('amount_kpy', 'count')
).reset_index()

analysis = projects.merge(project_cost_summary, on='project_id', how='left')
analysis['total_cost'] = analysis['total_cost'].fillna(0)
analysis['effective_cost_rate'] = (analysis['total_cost'] / analysis['contract_amount_kpy'] * 100)
analysis['cost_rate_gap'] = analysis['effective_cost_rate'] - analysis['target_cost_rate']

fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle('工事別原価率分析 — 赤字リスク特定', fontsize=16, fontweight='bold')

colors_scatter = ['#e74c3c' if g >= 0 else '#2ecc71' for g in analysis['cost_rate_gap']]
sizes = analysis['contract_amount_kpy'] / analysis['contract_amount_kpy'].max() * 300
axes[0].scatter(analysis['target_cost_rate'], analysis['effective_cost_rate'],
                c=colors_scatter, s=sizes, alpha=0.7, edgecolors='white', linewidth=0.5)
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

# %%
# === 4. 多角化事業 横断相関マトリクス ===
fac_monthly = facilities.groupby('month').agg(
    total_visitors=('visitors', 'sum'),
    total_facility_revenue=('revenue_kpy', 'sum')
).reset_index()

area_monthly = area_ind.groupby('month').agg(
    avg_land_price=('land_price_index', 'mean'),
    avg_foot_traffic=('foot_traffic', 'mean'),
    total_population=('population', 'sum')
).reset_index()

saas_monthly = saas.groupby('month').agg(
    total_mrr=('mrr_kpy', 'sum'),
    total_customers=('customers', 'sum')
).reset_index()

cross_data = fac_monthly.merge(area_monthly, on='month', how='inner')
cross_data = cross_data.merge(saas_monthly, on='month', how='left')

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
