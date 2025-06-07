from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np
import joblib
import os
from datetime import timedelta
# ─── Flask 앱 초기화 ───────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app, resources={r"/forecast": {"origins": "*"}})

# ─── 모델 로드 ────────────────────────────────────────────────────────────────
MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "global_sales_prophet.pkl")
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"모델 파일이 없습니다: {MODEL_PATH}")
model = joblib.load(MODEL_PATH)
print("✔️ 모델 로드 완료:", MODEL_PATH)

# ─── 예측 엔드포인트 ──────────────────────────────────────────────────────────
@app.route('/forecast', methods=['POST'])
def forecast():
    payload = request.get_json(force=True)
    periods    = payload.get('periods', 7)
    start_date = payload.get('startDate')  # e.g. "2025-03-17"

    # 1) start_date 가 주어졌으면 그 다음 날부터, 아니면 model.history 끝 다음 날부터
    if start_date:
        last = pd.to_datetime(start_date)
    else:
        last = model.history['ds'].max()

    # 2) start_date + 1일 부터 periods 만큼 날짜 생성
    future_dates = pd.date_range(start= last + timedelta(days=1),
                                 periods=periods, freq='D')
    future = pd.DataFrame({'ds': future_dates})

    # 3) 예측만 수행
    fc = model.predict(future)

    # 4) 로그 역변환
    for col in ('yhat','yhat_lower','yhat_upper'):
        fc[col] = np.expm1(fc[col]).clip(lower=0)

    # 5) JSON 직렬화
    result = [{
        "ds": row['ds'].strftime("%Y-%m-%d"),
        "yhat": float(row['yhat']),
        "yhat_lower": float(row['yhat_lower']),
        "yhat_upper": float(row['yhat_upper'])
    } for _, row in fc.iterrows()]
    

    return jsonify(result)



if __name__ == '__main__':
    # 개발용: 8082 포트로 실행
    app.run(host='0.0.0.0', port=8082, debug=True)
