# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np
from prophet import Prophet
import holidays

app = Flask(__name__)
CORS(app)


def train_and_forecast(df: pd.DataFrame, periods: int):
    # — 날짜별 매출 합계 집계
    df = df.groupby('ds', as_index=False)['y'].sum()
    df['ds'] = pd.to_datetime(df['ds'])
    df.sort_values('ds', inplace=True)
    df['y'] = np.log1p(df['y'])

    # — 한국 휴일
    years = df['ds'].dt.year.unique().tolist()
    kr_holidays = holidays.KR(years=years)
    hol_df = pd.DataFrame([
        {'ds': pd.to_datetime(d), 'holiday': name}
        for d, name in kr_holidays.items()
    ])

    # — Prophet 학습
    m = Prophet(
        growth='linear',
        changepoint_prior_scale=0.05,
        daily_seasonality=True,
        weekly_seasonality=True,
        yearly_seasonality=True,
        holidays=hol_df
    )
    m.fit(df)

    # — 예측
    future = m.make_future_dataframe(periods=periods, freq='D')
    fcst = m.predict(future)

    # — 결과 후처리(로그 역변환 & 날짜 포맷)
    last = df['ds'].max()
    out = (
        fcst[fcst['ds'] > last]
        .head(periods)[['ds','yhat','yhat_lower','yhat_upper']]
        .copy()
    )
    for col in ['yhat','yhat_lower','yhat_upper']:
        out[col] = np.expm1(out[col]).clip(lower=0)
    out['ds'] = out['ds'].dt.strftime('%Y-%m-%d')

    return out.to_dict(orient='records')


@app.route('/forecast/global', methods=['POST'])
def forecast_global():
    """
    전체 가맹점 매출 합계로 예측
    Java → GLOBAL_URL = http://127.0.0.1:8082/forecast/global
    """
    payload = request.get_json()
    df = (
        pd.DataFrame(payload.get('history', []))
          .rename(columns={'salesDate':'ds', 'totalAmount':'y'})
    )
    periods = int(payload.get('periods', 90))
    return jsonify(train_and_forecast(df, periods))


@app.route('/forecast/franchise/<int:franchise_id>', methods=['POST'])
def forecast_franchise(franchise_id):
    """
    특정 가맹점 매출만 필터해서 예측
    Java → FRANCHISE_URL = http://127.0.0.1:8082/forecast/franchise/{id}
    """
    payload = request.get_json()
    raw = pd.DataFrame(payload.get('history', []))
    raw = raw.rename(columns={'salesDate':'ds', 'totalAmount':'y'})
    raw['ds'] = pd.to_datetime(raw['ds'])

    # franchise_id 로 필터링
    df = raw[['ds','y']]  # 이미 Java 쪽에서 franchiseId 로 분기했으므로, 바로 사용

    periods = int(payload.get('periods', 7))
    return jsonify(train_and_forecast(df, periods))


if __name__ == '__main__':
    app.run(debug=True, port=8082)
