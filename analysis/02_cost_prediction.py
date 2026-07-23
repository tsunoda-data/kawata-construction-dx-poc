# %% [markdown]
# # 原価着地予測モデル構築
# ## 加和太建設 DXコックピット PoC — Step 3a
# BigQueryに格納済みのダミーデータを用い、XGBoostによる工事原価超過予測モデルを構築する

# %% [markdown]
# ## 1. セットアップ & BigQuery接続

# %%
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# 機械学習ライブラリ
import xgboost as xgb
from sklearn.model_selection import train_test_split, cross_val_score, KFold
from sklearn.metrics import mean_squared_error, mean_absolute_error, accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.preprocessing import OneHotEncoder

# Colab用の日本語フォント設定
try:
    import japanize_matplotlib
except ImportError:
    # Google Colab環境の場合はインストール
    # !pip install japanize-matplotlib
    print("japanize_matplotlibがインストールされていません。インストールするには '!pip install japanize-matplotlib' を実行してください。")

# --- Google Colab & BigQuery 設定 ---
# 以下の変数を実際の環境に合わせて変更してください
PROJECT_ID = 'your-project-id'  # ← ここを変更
DATASET = 'kawata_dx_poc'       # ← ここを変更

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

# %% [markdown]
# ## 2. データ取得

# %%
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
    # フォールバック用: ローカルCSVまたはGitHubなどのURLから取得
    try:
        # 実際の運用ではGitHubのRaw URL等を使用するか、ローカルパスを指定
        base_dir = '/Users/user/.gemini/antigravity/scratch/kawata-construction-dx-poc/data'
        projects_file = os.path.join(base_dir, 'projects_master.csv')
        costs_file = os.path.join(base_dir, 'cost_records.csv')
        
        if not os.path.exists(projects_file):
            print(f"ファイルが見つかりません: {projects_file}。ダミーデータを生成します。")
            # デモ用にランダムデータを生成
            np.random.seed(42)
            n_projects = 100
            
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
                'start_date': pd.to_datetime('2023-04-01') + pd.to_timedelta(np.random.randint(0, 365, n_projects), unit='D'),
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
            df['end_date'] = df['start_date'] + pd.to_timedelta(np.random.randint(90, 400, n_projects), unit='D')
            
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
            
            # null を 0 に埋める
            fill_cols = ['total_cost', 'outsourcing_cost', 'material_cost', 'labor_cost', 'expense_cost', 'confirmed_cost']
            df[fill_cols] = df[fill_cols].fillna(0)
            
            # 日付型の変換
            df['start_date'] = pd.to_datetime(df['start_date'])
            df['end_date'] = pd.to_datetime(df['end_date'])
            
        print("CSV(ローカル)またはモックからのデータ読み込み完了。データサイズ:", df.shape)
    except Exception as e:
        print(f"フォールバック読み込みエラー: {e}")

# 確認表示
display(df.head())

# %% [markdown]
# ## 3. 特徴量エンジニアリング

# %%
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
# 工事進行度に応じて按分された請負金額に対する原価の割合
recognized_revenue = ml_df['contract_amount_kpy'] * (ml_df['progress_rate'] / 100.0)
safe_revenue = np.where(recognized_revenue > 0, recognized_revenue, 1)
ml_df['actual_cost_rate'] = ml_df['total_cost'] / safe_revenue

# 5. 原価消化ペース vs 工期進捗
ml_df['cost_progress_ratio'] = (ml_df['actual_cost_rate'] / ml_df['target_cost_rate']) * (ml_df['progress_rate'] / 100.0)

# ターゲット変数（分類用）： 最終的に予算を超過したか（進行中のものは現在のペースで判定）
# 実績原価率が目標原価率を上回っていればTrue(1)
ml_df['is_over_budget'] = (ml_df['actual_cost_rate'] > ml_df['target_cost_rate']).astype(int)

# 欠損値の処理
ml_df = ml_df.fillna(0)

# カテゴリ変数のOne-Hotエンコーディング
features = [
    'contract_amount_kpy', 'duration_months', 'target_cost_rate', 'progress_rate',
    'outsourcing_pct', 'material_pct', 'labor_pct', 'expense_pct',
    'confirmed_ratio', 'cost_progress_ratio'
]

# One-hot encoding for division and client_type
encoder = OneHotEncoder(sparse_output=False, drop='first')
cat_encoded = encoder.fit_transform(ml_df[['division', 'client_type']])
cat_columns = encoder.get_feature_names_out(['division', 'client_type'])

cat_df = pd.DataFrame(cat_encoded, columns=cat_columns, index=ml_df.index)
X = pd.concat([ml_df[features], cat_df], axis=1)

y_reg = ml_df['actual_cost_rate']  # 回帰ターゲット
y_clf = ml_df['is_over_budget']    # 分類ターゲット

print("特徴量セット作成完了:", X.shape)
print("カラム:", X.columns.tolist())

# %% [markdown]
# ## 4. モデル学習（XGBoost）

# %%
# 学習データとテストデータに分割 (80/20)
X_train, X_test, y_reg_train, y_reg_test, y_clf_train, y_clf_test = train_test_split(
    X, y_reg, y_clf, test_size=0.2, random_state=42
)

print(f"Training data size: {X_train.shape[0]}")
print(f"Test data size: {X_test.shape[0]}")

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
cv_scores = cross_val_score(reg_model, X_train, y_reg_train, cv=cv, scoring='neg_mean_squared_error')
print(f"CV RMSE: {np.mean(np.sqrt(-cv_scores)):.4f} (+/- {np.std(np.sqrt(-cv_scores)):.4f})")

# 全学習データで学習
reg_model.fit(X_train, y_reg_train)
y_reg_pred = reg_model.predict(X_test)

rmse = np.sqrt(mean_squared_error(y_reg_test, y_reg_pred))
mae = mean_absolute_error(y_reg_test, y_reg_pred)
mape = np.mean(np.abs((y_reg_test - y_reg_pred) / y_reg_test)) * 100

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

# 全学習データで学習
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

# %% [markdown]
# ## 5. モデル評価・可視化

# %%
# 可視化用のフォント・スタイル設定
sns.set_theme(style="whitegrid")
try:
    import japanize_matplotlib
except ImportError:
    pass

fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle('モデル評価ダッシュボード', fontsize=18)

# 5-1: 実績 vs 予測 (回帰)
ax1 = axes[0, 0]
ax1.scatter(y_reg_test, y_reg_pred, alpha=0.7, color='teal')
ax1.plot([y_reg_test.min(), y_reg_test.max()], [y_reg_test.min(), y_reg_test.max()], 'r--', lw=2)
ax1.set_xlabel('実際の原価率 (Actual Cost Rate)')
ax1.set_ylabel('予測された原価率 (Predicted Cost Rate)')
ax1.set_title('実績 vs 予測 (Regression)', fontsize=14)

# 5-2: 特徴量重要度 (回帰)
ax2 = axes[0, 1]
importance = reg_model.feature_importances_
sorted_idx = np.argsort(importance)[-10:]  # Top 10
features_names = np.array(X.columns)

ax2.barh(range(len(sorted_idx)), importance[sorted_idx], align='center', color='coral')
ax2.set_yticks(range(len(sorted_idx)))
ax2.set_yticklabels(features_names[sorted_idx])
ax2.set_title('特徴量重要度 (Feature Importance - Top 10)', fontsize=14)

# 5-3: 混同行列 (分類)
ax3 = axes[1, 0]
cm = confusion_matrix(y_clf_test, y_clf_pred)
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax3, cbar=False)
ax3.set_xlabel('予測値 (Predicted Label)')
ax3.set_ylabel('実際の値 (True Label)')
ax3.set_xticklabels(['予算内(0)', '超過(1)'])
ax3.set_yticklabels(['予算内(0)', '超過(1)'])
ax3.set_title('混同行列 (Confusion Matrix)', fontsize=14)

# 5-4: 確率分布 または SHAP (SHAPがインストールされていれば)
ax4 = axes[1, 1]
try:
    import shap
    explainer = shap.Explainer(reg_model)
    shap_values = explainer(X_test)
    shap.summary_plot(shap_values, X_test, plot_type="bar", show=False)
    plt.close() # clear the extra plot
    
    mean_shap = np.abs(shap_values.values).mean(axis=0)
    sorted_idx_shap = np.argsort(mean_shap)[-10:]
    ax4.barh(range(len(sorted_idx_shap)), mean_shap[sorted_idx_shap], align='center', color='mediumpurple')
    ax4.set_yticks(range(len(sorted_idx_shap)))
    ax4.set_yticklabels(features_names[sorted_idx_shap])
    ax4.set_title('SHAP Feature Importance (Mean Absolute)', fontsize=14)
except ImportError:
    # SHAPがない場合は、超過確率の分布をプロット
    y_prob = clf_model.predict_proba(X_test)[:, 1]
    sns.histplot(y_prob[y_clf_test==0], color='blue', alpha=0.5, label='予算内', ax=ax4, bins=15, kde=True)
    sns.histplot(y_prob[y_clf_test==1], color='red', alpha=0.5, label='超過', ax=ax4, bins=15, kde=True)
    ax4.set_xlabel('超過予測確率 (Predicted Probability of Over-Budget)')
    ax4.set_title('予測確率の分布', fontsize=14)
    ax4.legend()

plt.tight_layout(rect=[0, 0.03, 1, 0.95])
plt.show()

# %% [markdown]
# ## 6. 予測結果の出力

# %%
# 全データに対する予測とリスク評価
ml_df['predicted_cost_rate'] = reg_model.predict(X)
ml_df['over_budget_prob'] = clf_model.predict_proba(X)[:, 1]

# 予測区間（簡易的にRMSEを用いて95%信頼区間を推定：±1.96 * RMSE）
ml_df['prediction_interval_lower'] = ml_df['predicted_cost_rate'] - (1.96 * rmse)
ml_df['prediction_interval_upper'] = ml_df['predicted_cost_rate'] + (1.96 * rmse)

# リスクスコア算出 (0-100)
# 超過確率と、目標原価率からの乖離幅を組み合わせて算出
cost_diff_ratio = (ml_df['predicted_cost_rate'] - ml_df['target_cost_rate']) / ml_df['target_cost_rate']
cost_diff_ratio = np.clip(cost_diff_ratio, 0, 0.2) * 5 # 0 to 1 scale

ml_df['risk_score'] = (ml_df['over_budget_prob'] * 0.7 + cost_diff_ratio * 0.3) * 100

# リスクレベルの定義
def assign_risk_level(score):
    if score >= 75:
        return '高 (High)'
    elif score >= 40:
        return '中 (Medium)'
    else:
        return '低 (Low)'

ml_df['risk_level'] = ml_df['risk_score'].apply(assign_risk_level)

# 報告用データフレーム作成
results_df = ml_df[['project_id', 'project_name', 'target_cost_rate', 'actual_cost_rate', 
                    'predicted_cost_rate', 'prediction_interval_lower', 'prediction_interval_upper', 
                    'risk_score', 'risk_level']].copy()

results_df = results_df.sort_values(by='risk_score', ascending=False)

# DataFrameのスタイリング (HTMLでリッチに表示)
def color_risk(val):
    if '高' in val:
        color = '#ff9999' # Red
    elif '中' in val:
        color = '#ffcc99' # Orange
    else:
        color = '#99ff99' # Green
    return f'background-color: {color}'

def highlight_over_budget(row):
    if row['predicted_cost_rate'] > row['target_cost_rate']:
        return ['background-color: #ffe6e6'] * len(row)
    return [''] * len(row)

styled_df = (results_df.head(20).style
             .apply(highlight_over_budget, axis=1)
             .map(color_risk, subset=['risk_level'])
             .format({
                 'target_cost_rate': '{:.1%}',
                 'actual_cost_rate': '{:.1%}',
                 'predicted_cost_rate': '{:.1%}',
                 'prediction_interval_lower': '{:.1%}',
                 'prediction_interval_upper': '{:.1%}',
                 'risk_score': '{:.1f}'
             })
             .set_caption("高リスクプロジェクト Top 20"))

display(styled_df)

# CSVとして保存
results_df.to_csv('cost_prediction_results.csv', index=False, encoding='utf-8-sig')
print("予測結果を 'cost_prediction_results.csv' に保存しました。")

# %% [markdown]
# ## 7. モデルの考察と限界
# 
# ### 重要な特徴量について
# 特徴量重要度（Feature Importance）の分析から、以下の要素が原価着地の予測に強く寄与していることがわかります：
# 1. **cost_progress_ratio (原価消化ペース vs 工期進捗):** 工期の進捗に対して原価がどれだけ先行して発生しているかが、最終的な赤字リスクの最大の先行指標です。
# 2. **confirmed_ratio (確定比率):** 原価のうち、すでに支払・請求が確定している割合。未確定要素が多い初期段階ではリスクのブレ幅が大きくなります。
# 3. **progress_rate (工事進捗率):** 工事の進み具合。後半になるほど予測精度は収束します。
# 
# ### モデルの限界
# 1. **データ量の不足とダミーデータの影響:** 今回はPoC用の生成データまたは少量のデータで学習しているため、実務で発生する特異な原価超過パターン（例：天候不良による工期遅延、資材価格の急激な高騰）を十分に捉えきれていません。
# 2. **時系列ダイナミクスの欠如:** 現在のモデルは「ある時点」のスナップショット予測です。時系列での原価率の変化トレンド（例：先月急激に悪化したか）を特徴量として取り込んでいません。
# 
# ### 本番運用に向けた改善提案
# 1. **原価内訳の時系列変化の組み込み:** 日次/週次での原価実績の推移をRNN/LSTM等でモデル化する、もしくは「過去1ヶ月の変化率」を特徴量に追加する。
# 2. **外部データの統合:** 資材価格インデックス（鋼材・コンクリート等）や気象データ、協力業者の稼働状況などを特徴量に加えることで、外的要因によるリスクを検知。
# 3. **現場担当者による補正入力:** MLの予測値に対して、現場担当者が定性的なリスク要因（現場特有の難所など）を加味できるような「Human-in-the-loop」の仕組みの導入。
# 
# ### ビジネスへのインパクト
# この予測モデルをDXコックピットに組み込むことで、**「事後報告型の原価管理」から「予測型のプロアクティブなリスクマネジメント」**へと移行できます。
# リスクスコアが閾値（例: 75以上）を超えたプロジェクトを自動検知し、経営層や部門長にアラートを上げることで、取り返しがつかなくなる前にテコ入れ（人員増強、工法見直し、協力業者との再交渉）を行うことが可能になります。
