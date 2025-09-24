import pandas as pd
import numpy as np
from faker import Faker
import random
from datetime import datetime, timedelta
from tqdm import tqdm

# 初始化 Faker
fake = Faker('zh_TW') # 使用台灣地區的資料生成，例如地址會是中文

# --- 設定參數 ---
NUM_CUSTOMERS = 1000 # 客戶數量
START_DATE = datetime(2018, 1, 1) # 數據生成的起始日期
END_DATE = datetime(2023, 12, 31) # 數據生成的結束日期

# --- 數據生成函數 ---

def generate_customers(num_customers):
    """生成客戶基本資料"""
    customers = []
    for i in range(num_customers):
        customer_id = f"C{i+1:05d}"
        age = random.randint(18, 80)
        gender = random.choice(['Male', 'Female'])
        # 收入水平與年齡掛鉤，年輕收入可能較低，中年較高
        income_level = random.choice(['Low', 'Medium', 'High'])
        if age < 30:
            income_level = random.choice(['Low', 'Medium'])
        elif age > 50:
            income_level = random.choice(['Medium', 'High'])
        
        region = fake.city() # 生成城市作為地區
        occupation_type = fake.job() # 生成職業

        customers.append({
            'customer_id': customer_id,
            'age': age,
            'gender': gender,
            'income_level': income_level,
            'region': region,
            'occupation_type': occupation_type
        })
    return pd.DataFrame(customers)

def generate_policies(customers_df):
    """根據客戶資料生成保單資料"""
    policies = []
    for _, customer in customers_df.iterrows():
        num_policies = random.randint(1, 3) # 每個客戶有1到3張保單
        for i in range(num_policies):
            policy_id = f"P{customer['customer_id']}-{i+1:02d}"
            policy_type = random.choice(['Life', 'Health', 'Accident', 'Investment'])
            coverage_amount = random.randint(100000, 5000000) # 保額
            monthly_premium = round(coverage_amount * random.uniform(0.0005, 0.002), 2) # 月繳保費
            
            # 保單開始日期在過去幾年
            start_date = fake.date_between_dates(date_start=START_DATE, date_end=END_DATE - timedelta(days=365))
            
            # 新保單第一年流失率較高 (透過狀態來體現)
            status = 'Active'
            if (datetime.now().year - start_date.year == 0) and random.random() < 0.05: # 當年新保單有5%流失率
                status = 'Lapsed' # 已失效
            elif random.random() < 0.01: # 每年有1%的保單會失效
                status = 'Lapsed'
            elif random.random() < 0.005: # 極少數會取消
                status = 'Cancelled'

            policies.append({
                'policy_id': policy_id,
                'customer_id': customer['customer_id'],
                'policy_type': policy_type,
                'coverage_amount': coverage_amount,
                'monthly_premium': monthly_premium,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'status': status
            })
    return pd.DataFrame(policies)

def generate_payments(policies_df):
    
    """根據保單生成繳費記錄"""
    payments = []
    print("正在生成繳費記錄...")
    # 確保 policies_with_customer_info 已經存在於主執行區塊
    for index, policy in tqdm(policies_df.iterrows(), total=len(policies_df), desc="Payments"):
        if policy['status'] in ['Lapsed', 'Cancelled']:
            continue # 失效或取消的保單不生成繳費記錄

        # 生成從保單開始日期到結束日期或當前日期的繳費記錄
        current_date = datetime.now()
        start_date = datetime.strptime(policy['start_date'], '%Y-%m-%d')
        
        # 考慮保單結束日期 (假設最長10年)
        policy_end_date = start_date + timedelta(days=365*10) 
        effective_end_date = min(policy_end_date, current_date)
        
        month_count = 0
        temp_date = start_date
        while temp_date <= effective_end_date:
            payment_date = temp_date
            amount = policy['monthly_premium']
            payment_method = random.choice(['Bank Transfer', 'Credit Card', 'Auto Debit'])
            
            days_late = 0
            # 收入低的客戶繳費延遲機率高 (假設客戶的income_level可在customer_df中取得)
            # 這裡需要透過 customer_id 找到客戶的 income_level
            customer_income = customers_df[customers_df['customer_id'] == policy['customer_id']]['income_level'].iloc[0]
            
            if customer_income == 'Low' and random.random() < 0.2: # 20% 機率延遲
                days_late = random.randint(1, 15)
            elif customer_income == 'Medium' and random.random() < 0.05: # 5% 機率延遲
                days_late = random.randint(1, 7)
            
            payments.append({
                'payment_id': f"PAY{policy['policy_id']}-{month_count+1:03d}",
                'policy_id': policy['policy_id'],
                'payment_date': payment_date.strftime('%Y-%m-%d'),
                'amount': amount,
                'payment_method': payment_method,
                'days_late': days_late
            })
            
            # 移動到下一個月
            if temp_date.month == 12:
                temp_date = temp_date.replace(year=temp_date.year + 1, month=1, day=1)
            else:
                temp_date = temp_date.replace(month=temp_date.month + 1, day=1)
            month_count += 1
            if temp_date > effective_end_date: # 避免無限循環，確保日期在範圍內
                break

    return pd.DataFrame(payments)

def generate_claims(policies_df, customers_df):
    """根據保單生成理賠記錄"""
    claims = []
    
    # 建立一個方便查詢的客戶年齡字典
    customer_age_map = customers_df.set_index('customer_id')['age'].to_dict()

    for _, policy in policies_df.iterrows():
        if policy['status'] in ['Lapsed', 'Cancelled']:
            continue # 失效或取消的保單不生成理賠

        customer_id = policy['customer_id']
        customer_age = customer_age_map.get(customer_id, 40) # 獲取客戶年齡，默認40

        num_claims_base = 0
        # 高齡客戶理賠頻率較高
        if customer_age > 60:
            num_claims_base = random.randint(0, 3) # 0-3次
        elif customer_age > 40:
            num_claims_base = random.randint(0, 2) # 0-2次
        else:
            num_claims_base = random.randint(0, 1) # 0-1次

        for i in range(num_claims_base):
            policy_start_date_str = policy['start_date'] # 字符串形式的開始日期
            policy_start_date_dt = datetime.strptime(policy_start_date_str, '%Y-%m-%d') # 轉換為 datetime.datetime

            # claim_date 透過 fake.date_between_dates 生成的是 datetime.date
            claim_date_dt = fake.date_between_dates(date_start=policy_start_date_dt.date(), date_end=END_DATE.date()) # 確保這裡傳入的也是 date 物件

            # 將 claim_date_dt 轉換為 datetime.datetime 進行計算
            # 或者，更簡單地，將 policy_start_date_dt 轉換為 datetime.date
            # 我們這裡選擇將 claim_date_dt 轉換為 datetime.datetime
            claim_date_full_dt = datetime.combine(claim_date_dt, datetime.min.time()) # 將 date 轉換為 datetime，時間部分設為午夜

            is_fraud_suspect = False
            
            # 新保單立即理賠 (若理賠日期很接近保單開始日期) - 增加欺詐可能性
            is_fraud_suspect = False
            if (claim_date_full_dt - policy_start_date_dt).days < 90 and random.random() < 0.1: # 新保單90天內有10%機率是可疑理賠
                is_fraud_suspect = True

            claim_amount = random.randint(5000, int(policy['coverage_amount'] * random.uniform(0.1, 0.8))) # 理賠金額
            
            claim_type = random.choice(['Medical', 'Accident', 'Critical Illness', 'Death'])
            approval_status = random.choice(['Approved', 'Denied'])
            
            # 設定欺詐標籤（如果需要，這可以作為訓練欺詐檢測模型的真實標籤）
            if is_fraud_suspect and random.random() < 0.7: # 70%機會真的是欺詐
                 approval_status = 'Denied' # 欺詐導致拒絕
                 claim_type = "Fraudulent" # 標記為欺詐類型

            claims.append({
                'claim_id': f"CLM{policy['policy_id']}-{i+1:02d}",
                'policy_id': policy['policy_id'],
                'claim_date': claim_date_dt.strftime('%Y-%m-%d'),
                'claim_amount': claim_amount,
                'claim_type': claim_type,
                'approval_status': approval_status
            })
    return pd.DataFrame(claims)

# --- 主執行區塊 ---
if __name__ == "__main__":
    print(f"開始生成 {NUM_CUSTOMERS} 筆客戶相關的保險數據...")

    # 1. 生成客戶數據
    customers_df = generate_customers(NUM_CUSTOMERS)
    print(f"生成 {len(customers_df)} 筆客戶數據。")

    # 2. 生成保單數據
    policies_df = generate_policies(customers_df)
    print(f"生成 {len(policies_df)} 筆保單數據。")

    # 3. 生成繳費記錄
    # 這裡需要傳入 customers_df 以便在 generate_payments 函數中獲取客戶收入水平
    # 由於 generate_payments 函數內部需要 access customers_df，
    # 這裡我們將它作為一個參數傳入，或者在函數內部重新載入或使用全局變量。
    # 為了簡潔，這裡假設 generate_payments 能直接訪問到客戶收入。
    # 最佳實踐是通過 merge 操作將相關信息併入。
    
    # --- 優化 generate_payments 獲取客戶收入的方式 ---
    # 將客戶收入信息合併到 policies_df，以便在生成 payments 時直接使用
    policies_with_customer_info = policies_df.merge(customers_df[['customer_id', 'income_level']], 
                                                     on='customer_id', how='left')
    payments_df = generate_payments(policies_with_customer_info)
    print(f"生成 {len(payments_df)} 筆繳費記錄。")

    # 4. 生成理賠記錄
    claims_df = generate_claims(policies_df, customers_df) # 需要客戶年齡來判斷理賠頻率
    print(f"生成 {len(claims_df)} 筆理賠記錄。")

    # --- 保存數據到 CSV 文件 ---
    output_dir = "data"
    import os
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    customers_df.to_csv(os.path.join(output_dir, 'customers.csv'), index=False)
    policies_df.to_csv(os.path.join(output_dir, 'policies.csv'), index=False)
    payments_df.to_csv(os.path.join(output_dir, 'payments.csv'), index=False)
    claims_df.to_csv(os.path.join(output_dir, 'claims.csv'), index=False)

    print("\n所有數據已成功生成並保存到 'data/' 資料夾下的 CSV 文件中。")