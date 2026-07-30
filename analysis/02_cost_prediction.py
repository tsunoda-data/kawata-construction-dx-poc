# %% [markdown]
# # 原価着地予測モデル構築
# ## 加和太建設 DXコックピット PoC — Step 3a
# BigQueryに格納済みのダミーデータを用い、XGBoostによる工事原価超過予測モデルを構築する

# %% [markdown]
# ## 1. セットアップ & BigQuery接続

# %%
import os
import sys
import subprocess
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
from datetime import datetime

# 機械学習ライブラリ
import xgboost as xgb
from sklearn.model_selection import train_test_split, cross_val_score, KFold
from sklearn.metrics import (mean_squared_error, mean_absolute_error,
                             accuracy_score, precision_score, recall_score,
                             f1_score, confusion_matrix)
from sklearn.preprocessing import OneHotEncoder



# --- Google Colab & BigQuery 設定 ---
# 以下の変数を実際の環境に合わせて変更してください
PROJECT_ID = 'kawata-dx-poc'      # ← GCPプロジェクトID
DATASET = 'kawata_dx_cockpit'     # ← BigQueryデータセット名

try:
    # Google Colab環境の判定
    import google.colab
    IN_COLAB = True
    print("Google Colab環境を検出しました。認証を開始します...")
    from google.colab import auth
    auth.authenticate_user()
    from google.cloud import bigquery
    client = bigquery.Client(project=PROJECT_ID)
    bq_available = True
    print("BigQueryへの接続準備が完了しました。")
except ImportError:
    IN_COLAB = False
    bq_available = False
    print("ローカル環境です。BigQueryクライアントの設定をスキップします。")
except Exception as e:
    IN_COLAB = True
    bq_available = False
    print(f"BigQuery認証エラー: {e}")

# BigQueryからML特徴量ビュー（vw_ml_features）または結合データを取得するクエリ
# 実際には dbt 等でビュー化しておく想定ですが、ここではクエリで生成します
query = f"""
WITH project_totals AS (
  SELECT
    project_id,
    SUM(amount_kpy) as total_cost,
    SUM(CASE WHEN category = '外注費' THEN amount_kpy ELSE 0 END) as outsourcing_cost,
    SUM(CASE WHEN category = '材料費' THEN amount_kpy ELSE 0 END) as material_cost,
    SUM(CASE WHEN category = '労務費' THEN amount_kpy ELSE 0 END) as labor_cost,
    SUM(CASE WHEN category = '経費' THEN amount_kpy ELSE 0 END) as expense_cost,
    SUM(CASE WHEN status = '支払済' OR status = '請求済' THEN amount_kpy ELSE 0 END) as confirmed_cost
  FROM `{PROJECT_ID}.{DATASET}.cost_records`
  GROUP BY project_id
)
SELECT
  p.project_id,
  p.project_name,
  p.division,
  p.client_type,
  p.contract_amount_kpy,
  p.start_date,
  p.end_date,
  p.target_cost_rate,
  p.progress_rate,
  p.status as project_status,
  t.total_cost,
  t.outsourcing_cost,
  t.material_cost,
  t.labor_cost,
  t.expense_cost,
  t.confirmed_cost
FROM `{PROJECT_ID}.{DATASET}.projects_master` p
LEFT JOIN project_totals t ON p.project_id = t.project_id
WHERE p.status != '計画'
"""

df = None

if bq_available:
    try:
        print("BigQueryからデータを取得します...")
        df = client.query(query).to_dataframe()
        print("BigQueryからのデータ取得成功！")
    except Exception as e:
        print(f"BigQueryからの取得失敗: {e}")
        df = None

if df is None:
    print("フォールバック: CSVファイルからデータを読み込みます。")
    try:
        base_dir = '/Users/user/.gemini/antigravity/scratch/kawata-construction-dx-poc/data'
        projects_file = os.path.join(base_dir, 'projects_master.csv')
        costs_file = os.path.join(base_dir, 'cost_records.csv')

        if not os.path.exists(projects_file):
            print(f"ファイルが見つかりません: {projects_file}。ダミーデータを生成します。")
            np.random.seed(42)
            n_projects = 200

            project_ids = [f'PRJ-{str(i).zfill(3)}' for i in range(1, n_projects+1)]
            divisions = np.random.choice(['土木', '建築'], n_projects)
            client_types = np.random.choice(['官公庁', '民間'], n_projects)
            contracts = np.random.uniform(50000, 500000, n_projects)
            target_rates = np.random.uniform(0.75, 0.88, n_projects)
            progresses = np.random.uniform(10, 100, n_projects)

            # 実績原価（予算内に収まるものと超過するもの）
            actual_rates = target_rates + np.random.normal(0.02, 0.05, n_projects)
            total_costs = contracts * actual_rates * (progresses / 100.0)

            df = pd.DataFrame({
                'project_id': project_ids,
                'project_name': [f'ダミー工事_{i}' for i in range(n_projects)],
                'division': divisions,
                'client_type': client_types,
                'contract_amount_kpy': contracts,
                'start_date': pd.to_datetime('2023-04-01') + pd.to_timedelta(
                    np.random.randint(0, 365, n_projects), unit='D'),
                'target_cost_rate': target_rates,
                'progress_rate': progresses,
                'project_status': np.where(progresses == 100, '竣工', '施工中'),
                'total_cost': total_costs,
                'outsourcing_cost': total_costs * 0.6,
                'material_cost': total_costs * 0.25,
                'labor_cost': total_costs * 0.1,
                'expense_cost': total_costs * 0.05,
                'confirmed_cost': total_costs * np.random.uniform(0.7, 0.95, n_projects)
            })
            df['end_date'] = df['start_date'] + pd.to_timedelta(
                np.random.randint(90, 400, n_projects), unit='D')

        else:
            projects_df = pd.read_csv(projects_file)
            costs_df = pd.read_csv(costs_file)

            # 集計ロジック (BigQueryクエリ相当)
            cost_totals = costs_df.groupby('project_id').agg(
                total_cost=('amount_kpy', 'sum'),
                outsourcing_cost=('amount_kpy', lambda x: x[costs_df.loc[x.index, 'category'] == '外注費'].sum()),
                material_cost=('amount_kpy', lambda x: x[costs_df.loc[x.index, 'category'] == '材料費'].sum()),
                labor_cost=('amount_kpy', lambda x: x[costs_df.loc[x.index, 'category'] == '労務費'].sum()),
                expense_cost=('amount_kpy', lambda x: x[costs_df.loc[x.index, 'category'] == '経費'].sum()),
                confirmed_cost=('amount_kpy', lambda x: x[costs_df.loc[x.index, 'status'].isin(['支払済', '請求済'])].sum())
            ).reset_index()

            df = pd.merge(projects_df, cost_totals, on='project_id', how='left')
            df = df[df['status'] != '計画'].copy()
            df.rename(columns={'status': 'project_status'}, inplace=True)

            fill_cols = ['total_cost', 'outsourcing_cost', 'material_cost',
                         'labor_cost', 'expense_cost', 'confirmed_cost']
            df[fill_cols] = df[fill_cols].fillna(0)

            df['start_date'] = pd.to_datetime(df['start_date'])
            df['end_date'] = pd.to_datetime(df['end_date'])

        print("CSV(ローカル)またはモックからのデータ読み込み完了。データサイズ:", df.shape)
    except Exception as e:
        print(f"フォールバック読み込みエラー: {e}")

# 確認表示
display(df.head())

# 解析用データフレーム作成
ml_df = df.copy()

# 1. 期間 (月数) の算出
ml_df['duration_months'] = (ml_df['end_date'] - ml_df['start_date']).dt.days / 30.44

# 2. 原価内訳比率の算出 (0除算回避)
safe_total = np.where(ml_df['total_cost'] > 0, ml_df['total_cost'], 1)
ml_df['outsourcing_pct'] = ml_df['outsourcing_cost'] / safe_total
ml_df['material_pct'] = ml_df['material_cost'] / safe_total
ml_df['labor_pct'] = ml_df['labor_cost'] / safe_total
ml_df['expense_pct'] = ml_df['expense_cost'] / safe_total

# 3. 確定比率 (発生原価のうち支払済・請求済の割合)
ml_df['confirmed_ratio'] = ml_df['confirmed_cost'] / safe_total

# 4. 現在の実績原価率 (進行基準)
# ★ target_cost_rate はパーセント形式（例: 85.0）で格納されているため、
#    actual_cost_rate も同じパーセント形式に揃える（×100）
recognized_revenue = ml_df['contract_amount_kpy'] * (ml_df['progress_rate'] / 100.0)
safe_revenue = np.where(recognized_revenue > 0, recognized_revenue, 1)
ml_df['actual_cost_rate'] = (ml_df['total_cost'] / safe_revenue) * 100  # ← パーセント形式に統一

# 5. 原価消化ペース vs 工期進捗
# 両方ともパーセント形式なので、比率計算はそのまま正しく機能する
ml_df['cost_progress_ratio'] = (
    (ml_df['actual_cost_rate'] / ml_df['target_cost_rate'])
    * (ml_df['progress_rate'] / 100.0)
)

# ターゲット変数（分類用）: 実績原価率が目標原価率を上回ればTrue(1)
# 例: actual=92.3% > target=88.0% → 超過(1)
ml_df['is_over_budget'] = (ml_df['actual_cost_rate'] > ml_df['target_cost_rate']).astype(int)

# 欠損値の処理
# 日付列は数値の0で埋められないため、先に削除する
ml_df = ml_df.drop(columns=['start_date', 'end_date'], errors='ignore')
ml_df = ml_df.fillna(0)
# inf値の処理（0除算で発生する可能性）
ml_df = ml_df.replace([np.inf, -np.inf], 0)

# カテゴリ変数のOne-Hotエンコーディング
features = [
    'contract_amount_kpy', 'duration_months', 'target_cost_rate', 'progress_rate',
    'outsourcing_pct', 'material_pct', 'labor_pct', 'expense_pct',
    'confirmed_ratio', 'cost_progress_ratio'
]

encoder = OneHotEncoder(sparse_output=False, drop='first')
cat_encoded = encoder.fit_transform(ml_df[['division', 'client_type']])
cat_columns = encoder.get_feature_names_out(['division', 'client_type'])

cat_df = pd.DataFrame(cat_encoded, columns=cat_columns, index=ml_df.index)
X = pd.concat([ml_df[features], cat_df], axis=1)

y_reg = ml_df['actual_cost_rate']  # 回帰ターゲット
y_clf = ml_df['is_over_budget']    # 分類ターゲット

print(f"特徴量セット作成完了: {X.shape}")
print(f"カラム: {X.columns.tolist()}")
print(f"分類ターゲット分布: 予算内={sum(y_clf==0)}, 超過={sum(y_clf==1)}")

# 学習データとテストデータに分割 (80/20)
# stratify=y_clf で分類ターゲットの比率を維持する
X_train, X_test, y_reg_train, y_reg_test, y_clf_train, y_clf_test = train_test_split(
    X, y_reg, y_clf, test_size=0.2, random_state=42, stratify=y_clf
)

print(f"学習データサイズ: {X_train.shape[0]}")
print(f"テストデータサイズ: {X_test.shape[0]}")
print(f"テストデータの分類比率: 予算内={sum(y_clf_test==0)}, 超過={sum(y_clf_test==1)}")

# --- 1. 回帰モデル (原価率の予測) ---
print("\n--- 回帰モデル（原価率予測） ---")
reg_model = xgb.XGBRegressor(
    objective='reg:squarederror',
    n_estimators=100,
    learning_rate=0.1,
    max_depth=5,
    random_state=42
)

# 5分割交差検証
cv = KFold(n_splits=5, shuffle=True, random_state=42)
cv_scores = cross_val_score(reg_model, X_train, y_reg_train, cv=cv,
                            scoring='neg_mean_squared_error')
print(f"CV RMSE: {np.mean(np.sqrt(-cv_scores)):.4f} (+/- {np.std(np.sqrt(-cv_scores)):.4f})")

# 全学習データで学習
reg_model.fit(X_train, y_reg_train)
y_reg_pred = reg_model.predict(X_test)

rmse = np.sqrt(mean_squared_error(y_reg_test, y_reg_pred))
mae = mean_absolute_error(y_reg_test, y_reg_pred)
mape = np.mean(np.abs((y_reg_test - y_reg_pred) / np.where(y_reg_test != 0, y_reg_test, 1))) * 100

print(f"Test RMSE: {rmse:.4f}")
print(f"Test MAE: {mae:.4f}")
print(f"Test MAPE: {mape:.2f}%")

# --- 2. 分類モデル (予算超過の予測) ---
print("\n--- 分類モデル（予算超過アラート） ---")
clf_model = xgb.XGBClassifier(
    objective='binary:logistic',
    n_estimators=100,
    learning_rate=0.1,
    max_depth=5,
    random_state=42,
    eval_metric='logloss'
)

clf_model.fit(X_train, y_clf_train)
y_clf_pred = clf_model.predict(X_test)

accuracy = accuracy_score(y_clf_test, y_clf_pred)
precision = precision_score(y_clf_test, y_clf_pred, zero_division=0)
recall = recall_score(y_clf_test, y_clf_pred, zero_division=0)
f1 = f1_score(y_clf_test, y_clf_pred, zero_division=0)

print(f"Test Accuracy: {accuracy:.4f}")
print(f"Test Precision: {precision:.4f}")
print(f"Test Recall: {recall:.4f}")
print(f"Test F1 Score: {f1:.4f}")

# =====================================================
# 可視化（日本語フォント設定済み）
# =====================================================
# %%
# 可視化用のフォント・スタイル設定
sns.set_theme(style="whitegrid")

# japanize_matplotlib を呼び出し、日本語フォントを適用 (セットアップセルで既に呼び出されています)
import japanize_matplotlib
japanize_matplotlib.japanize()

# 明示的なフォント設定は japanize_matplotlib に任せます。以前の設定は競合を避けるため削除します。
# plt.rcParams['font.sans-serif'] = ['Noto Sans CJK JP', 'Arial Unicode MS']
# plt.rcParams['font.family'] = 'sans-serif'

plt.rcParams['axes.unicode_minus'] = False # マイナス記号を正しく表示


fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle('モデル評価ダッシュボード', fontsize=18, fontweight='bold')

# --- 5-1: 実績 vs 予測 (回帰) ---
ax1 = axes[0, 0]
ax1.scatter(y_reg_test, y_reg_pred, alpha=0.7, color='teal', edgecolors='white', s=60)
line_min = min(y_reg_test.min(), y_reg_pred.min())
line_max = max(y_reg_test.max(), y_reg_pred.max())
ax1.plot([line_min, line_max], [line_min, line_max], 'r--', lw=2, label='理想線 (y=x)')
ax1.set_xlabel('実際の原価率')
ax1.set_ylabel('予測原価率')
ax1.set_title('実績 vs 予測（回帰モデル）', fontsize=14)
ax1.legend()

# --- 5-2: 特徴量重要度 (回帰) ---
ax2 = axes[0, 1]
importance = reg_model.feature_importances_
sorted_idx = np.argsort(importance)[-10:]  # Top 10

# 日本語の特徴量名マッピング
feature_name_jp = {
    'contract_amount_kpy': '請負金額',
    'duration_months': '工期（月）',
    'target_cost_rate': '目標原価率',
    'progress_rate': '工事進捗率',
    'outsourcing_pct': '外注費比率',
    'material_pct': '材料費比率',
    'labor_pct': '労務費比率',
    'expense_pct': '経費比率',
    'confirmed_ratio': '確定比率',
    'cost_progress_ratio': '原価消化ペース',
    'division_建築': '事業部:建築',
    'client_type_民間': '発注者:民間',
}
feature_labels = [feature_name_jp.get(X.columns[i], X.columns[i]) for i in sorted_idx]

ax2.barh(range(len(sorted_idx)), importance[sorted_idx], align='center', color='coral')
ax2.set_yticks(range(len(sorted_idx)))
ax2.set_yticklabels(feature_labels, fontsize=10)
ax2.set_title('特徴量重要度 Top10（XGBoost）', fontsize=14)
ax2.set_xlabel('重要度スコア')

# --- 5-3: 混同行列 (分類) ---
ax3 = axes[1, 0]
cm = confusion_matrix(y_clf_test, y_clf_pred)
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax3, cbar=False,
            annot_kws={"size": 16})
ax3.set_xlabel('予測値', fontsize=12)
ax3.set_ylabel('実際の値', fontsize=12)
ax3.set_xticklabels(['予算内 (0)', '超過 (1)'], fontsize=11)
ax3.set_yticklabels(['予算内 (0)', '超過 (1)'], fontsize=11)
ax3.set_title('混同行列', fontsize=14)

# --- 5-4: SHAP分析 ---
ax4 = axes[1, 1]

shap_success = False
try:
    import shap
    print("SHAP分析を実行中...")

    # ★ XGBoostには TreeExplainer を明示的に使用（安定性・速度ともに最適）
    explainer = shap.TreeExplainer(reg_model)

    # ★ shap_values() は numpy array を直接返す（.values アクセス不要）
    shap_values = explainer.shap_values(X_test)

    # SHAP値の平均絶対値で特徴量重要度を算出
    mean_shap = np.abs(shap_values).mean(axis=0)

    # 値が全てゼロでないことを確認
    if mean_shap.sum() > 0:
        sorted_idx_shap = np.argsort(mean_shap)[-10:]
        shap_labels = [feature_name_jp.get(X.columns[i], X.columns[i])
                       for i in sorted_idx_shap]

        ax4.barh(range(len(sorted_idx_shap)), mean_shap[sorted_idx_shap],
                 align='center', color='mediumpurple')
        ax4.set_yticks(range(len(sorted_idx_shap)))
        ax4.set_yticklabels(shap_labels, fontsize=10)
        ax4.set_title('SHAP特徴量重要度（平均絶対値）', fontsize=14)
        ax4.set_xlabel('平均|SHAP値|')
        shap_success = True
        print(f"✅ SHAP分析完了（テストデータ {X_test.shape[0]}件）")
    else:
        print("⚠️ SHAP値がすべてゼロです。フォールバック表示に切り替えます。")

except ImportError:
    print("⚠️ shapライブラリが未インストールです。"
          "インストールするには: !pip install shap")
except Exception as e:
    print(f"⚠️ SHAP分析でエラー: {e}")

# SHAPが失敗した場合のフォールバック: 超過確率の分布をプロット
if not shap_success:
    y_prob = clf_model.predict_proba(X_test)[:, 1]
    ax4.hist(y_prob[y_clf_test == 0], bins=15, alpha=0.6,
             color='#3498db', label='予算内', edgecolor='white')
    ax4.hist(y_prob[y_clf_test == 1], bins=15, alpha=0.6,
             color='#e74c3c', label='超過', edgecolor='white')
    ax4.set_xlabel('予算超過の予測確率')
    ax4.set_ylabel('件数')
    ax4.set_title('予測確率の分布', fontsize=14)
    ax4.legend()

plt.tight_layout(rect=[0, 0.03, 1, 0.95])
plt.savefig('output_model_evaluation.png', dpi=150, bbox_inches='tight')
plt.show()
print("✅ 図表を保存: output_model_evaluation.png")

# =====================================================
# SHAP詳細分析（Beeswarm Plot — 各特徴量の影響方向を可視化）
# =====================================================
try:
    import shap

    explainer = shap.TreeExplainer(reg_model)
    shap_values_obj = explainer(X_test)  # Explanation オブジェクトを取得

    fig_shap, ax_shap = plt.subplots(figsize=(12, 8))
    shap.summary_plot(shap_values_obj, X_test,
                      feature_names=[feature_name_jp.get(c, c) for c in X.columns],
                      show=False, plot_size=None)
    plt.title('SHAP Beeswarm Plot — 各特徴量が原価率予測に与える影響', fontsize=14)
    plt.tight_layout()
    plt.savefig('output_shap_beeswarm.png', dpi=150, bbox_inches='tight')
    plt.show()
    print("✅ SHAP Beeswarm Plot を保存: output_shap_beeswarm.png")
except Exception as e:
    print(f"⚠️ SHAP Beeswarm Plot をスキップ: {e}")

# 全データに対する予測とリスク評価
ml_df['predicted_cost_rate'] = reg_model.predict(X)
ml_df['over_budget_prob'] = clf_model.predict_proba(X)[:, 1]

# 予測区間（簡易的にRMSEを用いて95%信頼区間を推定：±1.96 * RMSE）
ml_df['prediction_interval_lower'] = ml_df['predicted_cost_rate'] - (1.96 * rmse)
ml_df['prediction_interval_upper'] = ml_df['predicted_cost_rate'] + (1.96 * rmse)

# リスクスコア算出 (0-100)
cost_diff_ratio = (ml_df['predicted_cost_rate'] - ml_df['target_cost_rate']) / ml_df['target_cost_rate']
cost_diff_ratio = np.clip(cost_diff_ratio, 0, 0.2) * 5  # 0 to 1 scale

ml_df['risk_score'] = (ml_df['over_budget_prob'] * 0.7 + cost_diff_ratio * 0.3) * 100

def assign_risk_level(score):
    if score >= 75:
        return '🔴 高リスク'
    elif score >= 40:
        return '🟠 中リスク'
    else:
        return '🟢 低リスク'

ml_df['risk_level'] = ml_df['risk_score'].apply(assign_risk_level)

# 報告用データフレーム作成
results_df = ml_df[['project_id', 'project_name', 'target_cost_rate', 'actual_cost_rate',
                     'predicted_cost_rate', 'prediction_interval_lower',
                     'prediction_interval_upper', 'risk_score', 'risk_level']].copy()

results_df = results_df.sort_values(by='risk_score', ascending=False)

# DataFrameのスタイリング
def color_risk(val):
    if '高' in str(val):
        return 'background-color: #ff9999'
    elif '中' in str(val):
        return 'background-color: #ffcc99'
    else:
        return 'background-color: #99ff99'

def highlight_over_budget(row):
    if row['predicted_cost_rate'] > row['target_cost_rate']:
        return ['background-color: #ffe6e6'] * len(row)
    return [''] * len(row)

styled_df = (results_df.head(20).style
             .apply(highlight_over_budget, axis=1)
             .map(color_risk, subset=['risk_level'])
             .format({
                 'target_cost_rate': '{:.1f}%',
                 'actual_cost_rate': '{:.1f}%',
                 'predicted_cost_rate': '{:.1f}%',
                 'prediction_interval_lower': '{:.1f}%',
                 'prediction_interval_upper': '{:.1f}%',
                 'risk_score': '{:.1f}'
             })
             .set_caption("⚠️ 高リスクプロジェクト Top 20"))

display(styled_df)

# CSVとして保存
results_df.to_csv('cost_prediction_results.csv', index=False, encoding='utf-8-sig')
print("✅ 予測結果を 'cost_prediction_results.csv' に保存しました。")

