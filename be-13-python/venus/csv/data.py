import pandas as pd
import numpy as np

# 1) 설정
menu_prices = {
    1:3000, 2:4000, 3:4500, 4:5000, 5:5500,
    6:5000, 7:4500, 8:3000, 9:4000, 10:4500,
    11:4800, 12:5200, 13:5500, 14:5000, 15:5500,
    16:5500, 17:5800, 18:4700, 19:4800, 20:4500
}
franchise_ids = list(range(62, 72))
dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')

# 2) 한국 공휴일 직접 지정
holidays = pd.to_datetime([
    '2024-01-01',                  # 신정
    '2024-01-28', '2024-01-29', '2024-01-30',  # 설날
    '2024-03-01',                  # 삼일절
    '2024-05-05',                  # 어린이날
    '2024-06-06',                  # 현충일
    '2024-08-15',                  # 광복절
    '2024-10-03',                  # 개천절
    '2024-10-05', '2024-10-06', '2024-10-07',  # 추석
    '2024-10-09',                  # 한글날
    '2024-12-25',                  # 성탄절
    '2025-01-01',                  # 신정(익년)
    '2025-02-09', '2025-02-10', '2025-02-11',  # 설날(2025년)
    '2025-03-01',                  # 삼일절
    '2025-05-05'                   # 어린이날
])

# 3) 요일·공휴일 팩터 계산
df_dates = pd.DataFrame({'sales_date': dates})
df_dates['is_weekend'] = df_dates['sales_date'].dt.weekday >= 5

# 주말 판매 건수 30% 감소 
df_dates['weekly_factor'] = np.where(df_dates['is_weekend'], 0.7, 1.0)

# 공휴일 판매 건수 50% 감소
df_dates['is_holiday'] = df_dates['sales_date'].isin(holidays)
df_dates['holiday_factor'] = np.where(df_dates['is_holiday'], 0.5, 1.0)

# 4) 더미 판매 내역 생성
np.random.seed(42)
records = []
target_rows = 150_000
base_rows = target_rows / len(dates)

for _, row in df_dates.iterrows():
    lam = base_rows * row['weekly_factor'] * row['holiday_factor']
    n = np.random.poisson(lam)
    for _ in range(n):
        menu_id = np.random.choice(list(menu_prices.keys()))
        franchise_id = np.random.choice(franchise_ids)
        count = np.random.randint(1, 6)
        amount = menu_prices[menu_id] * count
        records.append({
            'menu_id': menu_id,
            'franchise_id': franchise_id,
            'product_count': count,
            'amount': amount,
            'sales_date': row['sales_date'].strftime('%Y-%m-%d')
        })

df_sales = pd.DataFrame(records)

# 5) CSV로 저장
df_sales.to_csv('sales_detail_2023.csv', index=False, encoding='utf-8-sig')