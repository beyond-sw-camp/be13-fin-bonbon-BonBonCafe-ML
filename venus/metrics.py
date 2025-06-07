# metrics.py

import sys
import pandas as pd
import numpy as np
from prophet import Prophet
from prophet.diagnostics import cross_validation, performance_metrics
import holidays
import matplotlib.pyplot as plt


def plot_cv_scatter(df, initial="876 days", period="30 days", horizon="30 days"):
    """
    교차검증(CV)을 수행하고, 실제 vs 예측 산점도를 그립니다.
    df: load_history()로 반환된 DataFrame (ds, y 컬럼)
    initial/period/horizon: prophet.cross_validation 파라미터
    """
    # 1) 모델 학습
    m = Prophet(
        growth='linear',
        changepoint_prior_scale=0.05,
        daily_seasonality=True,
        weekly_seasonality=True,
        yearly_seasonality=True
    )
    m.fit(df[['ds','y']])

    # 2) 교차검증 실행
    print(f"▶ CV 수행: initial={initial}, period={period}, horizon={horizon}")
    cv = cross_validation(
        m, initial=initial, period=period, horizon=horizon, parallel="processes"
    )

    # 3) 산점도 그리기
    plt.figure(figsize=(6,6))
    plt.scatter(cv['y'], cv['yhat'], alpha=0.3, s=10, label='CV 예측 vs 실제')
    # 이상적 대각선
    mn = 0
    mx = df['y'].max() * 1.1
    plt.plot([mn, mx], [mn, mx], 'r--', linewidth=1, label='y = yhat')

    # 축 범위 설정
    plt.xlim(mn, mx)
    plt.ylim(mn, mx)

    plt.xlabel('실제 매출 (y)')
    plt.ylabel('예측 매출 (yhat)')
    plt.title('CV 결과: 실제값 vs 예측값 산점도')
    plt.legend()
    plt.grid(alpha=0.2)
    plt.tight_layout()
    plt.savefig('cv_actual_vs_predicted_scatter.png')
    print("▶ cv_actual_vs_predicted_scatter.png 저장 완료")


def load_history(path):
    print(f"▶ 데이터를 로드: {path}")
    if path.endswith('.json'):
        import json
        with open(path, 'r', encoding='utf-8') as f:
            history = json.load(f)
        df = pd.DataFrame(history)
    else:
        df = pd.read_csv(path)
    print("  원본 컬럼:", df.columns.tolist())

    # 컬럼명 표준화
    col_map = {}
    if 'ds' in df.columns:
        col_map['ds'] = 'ds'
    elif 'salesDate' in df.columns:
        col_map['salesDate'] = 'ds'
    elif 'sales_date' in df.columns:
        col_map['sales_date'] = 'ds'
    if 'y' in df.columns:
        col_map['y'] = 'y'
    elif 'totalAmount' in df.columns:
        col_map['totalAmount'] = 'y'
    elif 'amount' in df.columns:
        col_map['amount'] = 'y'
    df = df.rename(columns=col_map)
    print("  매핑 후 컬럼:", df.columns.tolist())

    # 날짜 변환 및 일별 집계
    df['ds'] = pd.to_datetime(df['ds'])
    df = df.groupby('ds', as_index=False)['y'].sum()
    print(f"  일별 집계 후 레코드 수: {len(df)}")

    return df.sort_values('ds')


def evaluate(df):
    # 로그 변환
    df['y'] = np.log1p(df['y'])

    # 한국 공휴일
    years = df['ds'].dt.year.unique().tolist()
    kr_holidays = holidays.KR(years=years)
    holiday_rows = [{'ds': pd.to_datetime(d), 'holiday': n} for d,n in kr_holidays.items()]
    holidays_df = pd.DataFrame(holiday_rows)

    # 모델 학습
    m = Prophet(
        growth='linear',
        changepoint_prior_scale=0.05,
        daily_seasonality=True,
        weekly_seasonality=True,
        yearly_seasonality=True,
        holidays=holidays_df
    )
    m.fit(df)

    # 교차검증 성능 평가
    total_days = len(df)
    initial = f"{int(total_days * 0.8)} days"
    print(f"▶ cross_validation initial = {initial}")
    cv = cross_validation(
        m, initial=initial, period="30 days", horizon="30 days", parallel="processes"
    )
    perf = performance_metrics(cv)

    print("=== CV 성능 지표 ===")
    print(f"MSE:  {perf['mse'].mean():.2f}")
    print(f"MAE:  {perf['mae'].mean():.2f}")
    print(f"RMSE: {perf['rmse'].mean():.2f}")
    print(f"MAPE: {perf['mape'].mean():.2%}")

    # MAPE 분포 저장
    plt.figure(figsize=(8,4))
    plt.hist(perf['mape'], bins=20, edgecolor='k')
    plt.title("MAPE 분포")
    plt.xlabel("MAPE")
    plt.ylabel("빈도")
    plt.tight_layout()
    plt.savefig('mape_distribution.png')
    print("▶ mape_distribution.png 저장 완료")


def plot_actual_vs_predicted(df):
    """
    인-샘플 예측 시각화: 실제값과 예측값을 비교
    """
    # raw y 사용
    y_series = df['y']

    # 모델 학습
    m = Prophet(
        growth='linear',
        changepoint_prior_scale=0.05,
        daily_seasonality=True,
        weekly_seasonality=True,
        yearly_seasonality=True
    )
    m.fit(df[['ds','y']])

    # 예측
    future = m.make_future_dataframe(periods=0)
    fcst = m.predict(future)
    fcst['yhat_orig'] = fcst['yhat']

    # 시각화
    fig, ax = plt.subplots(figsize=(12,6))
    ax.scatter(
        df['ds'], y_series,
        color='lightgray', alpha=0.5, s=20, label='실제 매출', zorder=1
    )
    ax.plot(
    fcst['ds'], fcst['yhat_orig'],
    color='orange',
    linewidth=1,        # 가는 선
    linestyle='-',      # 실선
    label='예측 매출',
    zorder=2
    )

    end_date = df['ds'].max()
    start_date = end_date - pd.DateOffset(months=3)
    ax.set_xlim(start_date, end_date)

    # y축도 약간 여유롭게
    ax.set_ylim(0, df['y'].max() * 1.1)

    ax.set_xlabel('날짜')
    ax.set_ylabel('매출')
    ax.set_title('실제값 vs 예측값 매출 비교 (최근 1년)')
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig('actual_vs_predicted_zoomed.png')
    print("▶ actual_vs_predicted_zoomed.png 저장 완료")


if __name__ == '__main__':
    path = '/content/drive/MyDrive/history.csv'
    df = load_history(path)
    evaluate(df.copy())
    plot_actual_vs_predicted(df.copy())
    plot_cv_scatter(df.copy())
