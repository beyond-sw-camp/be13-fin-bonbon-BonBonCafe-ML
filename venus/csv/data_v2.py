import pandas as pd
import numpy as np
import holidays

# 1) 설정
np.random.seed(42)
start_date = '2025-01-01'
end_date   = '2025-12-31'
dates = pd.date_range(start_date, end_date, freq='D')
n_days = len(dates)

# 2) 공휴일 정보 (한국)
kr_holidays = holidays.KR(years=[2022,2023,2024,2025])
# 키들을 datetime64[ns] 로 변환
holiday_dates = pd.to_datetime(list(kr_holidays.keys()))

# 3) 구조적 패턴
base_level   = 1000
trend_slope  = 1.5
weekly_amp   = 200
yearly_amp   = 400

day_of_year  = dates.dayofyear
weekday      = dates.weekday
trend        = base_level + trend_slope * np.arange(n_days)
weekly       = weekly_amp * np.sin(2*np.pi*weekday/7)
yearly       = yearly_amp * np.sin(2*np.pi*day_of_year/365)


holiday_mask = dates.isin(holiday_dates)
holiday_eff  = np.where(holiday_mask, -800, 0)

# 4) 기대 판매량 μ 계산
mu = trend + weekly + yearly + holiday_eff
mu = np.clip(mu, a_min=50, a_max=None)

# 4) 일별 실제 판매량 Poisson 샘플링
daily_sales = np.random.poisson(lam=mu)

# 5) 메뉴·가맹점 분배
menu_prices   = {i:p for i,p in enumerate(
    [1600,1800,2000,2100,2200,2300,2400,2500,2600,2700,
    2800,2900,3000,2900,3000,3200,3300,3400,3600,3700], start=1)}
franchise_ids = list(range(291,303))

records = []
for date, sold in zip(dates, daily_sales):
    # 메뉴별 분배
    menu_counts = np.random.multinomial(sold, [1/len(menu_prices)]*len(menu_prices))
    for menu_id, qty in enumerate(menu_counts, start=1):
        if qty==0: continue
        # 가맹점별 분배
        store_counts = np.random.multinomial(qty, [1/len(franchise_ids)]*len(franchise_ids))
        for fid, sub_qty in zip(franchise_ids, store_counts):
            if sub_qty==0: continue
            records.append({
                'menu_id':      menu_id,
                'franchise_id': fid,
                'product_count':int(sub_qty),
                'amount':       int(sub_qty*menu_prices[menu_id]),
                'sales_date':   date.strftime('%Y-%m-%d')
            })

df = pd.DataFrame(records)
df.to_csv('bonbon_sales_detail1_2025.csv', index=False, encoding='utf-8-sig')
