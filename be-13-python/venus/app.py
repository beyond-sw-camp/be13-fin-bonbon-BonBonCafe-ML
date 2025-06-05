from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np
from prophet import Prophet

# 고정 휴일
fixed_holidays = {
    'new_year':         (1,  1),
    'seollal':          (1, 28),
    'sam_il':           (3,  1),
    'children':         (5,  5),
    'memorial':         (6,  6),
    'liberation':       (8, 15),
    'national':         (10, 3),
    'chuseok_start':    (10, 5),
    'hangul':           (10, 9),
    'christmas':        (12,25)
}

app = Flask(__name__)
CORS(app, resources={r"/forecast": {"origins": "*"}})

@app.route('/forecast', methods=['POST'])
def forecast(): 
    # JSON 파싱
    payload = request.get_json()
    history = payload.get('history', [])
    periods = payload.get('periods', 7)

    # DataFrame 준비
    df = pd.DataFrame(history).rename(columns={
        'salesDate': 'ds',
        'totalAmount': 'y'
    })
    df['ds'] = pd.to_datetime(df['ds'])
    
    # 로그 변환으로 음수 방지
    df['y']  = np.log1p(df['y'])

    # holidays DataFrame 생성
    years = df['ds'].dt.year.unique()
    holiday_rows = []
    for y in years:
        for name, (m, d) in fixed_holidays.items():
            try:
                holiday_rows.append({'ds': pd.Timestamp(year=y, month=m, day=d),
                                    'holiday': name})
            except ValueError:
                # 잘못된 날짜 무시
                pass
    holidays_df = pd.DataFrame(holiday_rows)

    # Prophet 모델 학습
    m = Prophet(
        growth='linear',
        changepoint_prior_scale=0.01,
        daily_seasonality=True, 
        weekly_seasonality=True, 
        yearly_seasonality=False,   
        holidays=holidays_df
    )
    m.fit(df)

    # 미래 일별 DataFrame 생성 & 예측
    future = m.make_future_dataframe(periods=periods, freq='D')
    forecast_df = m.predict(future)

    last_date = df['ds'].max()
    future_only = forecast_df.loc[forecast_df['ds'] > last_date].head(periods).copy()

    # 역변환 및 음수 클리핑
    for col in ['yhat','yhat_lower','yhat_upper']:
        future_only[col] = np.expm1(future_only[col]).clip(lower=0)

    # JSON 포맷
    future_only['ds'] = future_only['ds'].dt.strftime('%Y-%m-%d')
    result = future_only[['ds','yhat','yhat_lower','yhat_upper']].to_dict(orient='records')

    return jsonify(result)

if __name__=='__main__':
    app.run(host='0.0.0.0', port=8082, debug=True)
