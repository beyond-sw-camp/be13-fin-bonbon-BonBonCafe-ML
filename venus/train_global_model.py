import pandas as pd
import numpy as np
from prophet import Prophet
from sqlalchemy import text
from sqlalchemy import create_engine
from apscheduler.schedulers.blocking import BlockingScheduler
import joblib, os

# ─── DB 연결 설정 ──────────────────────────────────────────────────────────
from sqlalchemy import create_engine
# pip install mysqlclient
DB_USER = 'bonbon1'
DB_PASS = '0000'
DB_HOST = 'localhost'
DB_PORT = '3306'
DB_NAME = 'bonbon'

# C 드라이버(mysqlclient) 사용
engine = create_engine(
    f"mysql+mysqldb://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ─── 이하 생략 ────────────────────────────────────────────────────────────────


# 2) 고정 휴일 정의
fixed_holidays = {
    'new_year':      (1,  1),
    'seollal':       (1, 28),
    'sam_il':        (3,  1),
    'children':      (5,  5),
    'memorial':      (6,  6),
    'liberation':    (8, 15),
    'national':      (10,3),
    'chuseok_start': (10,5),
    'hangul':        (10,9),
    'christmas':     (12,25)
}

def load_global_sales():
    """
    sales_record 테이블의 실제 컬럼명을 사용해
    지난 2년간 일별 매출 합계를 가져오는 함수
    """
    with engine.connect() as conn:
        # (디버그용) 컬럼/샘플 출력
        cols = conn.execute(text("SHOW COLUMNS FROM sales_record")).fetchall()
        print("columns:", cols)
        sample = conn.execute(text("SELECT * FROM sales_record LIMIT 5")).fetchall()
        print("sample rows:", sample)

        # 실제 매출 합계 컬럼명이 'sales_amount' 라고 가정
        sql = """
        SELECT 
            DATE(sales_date) AS ds, 
            SUM(sales_amount) AS y
        FROM sales_record
        WHERE sales_date >= DATE_SUB(CURDATE(), INTERVAL 2 YEAR)
        GROUP BY DATE(sales_date)
        ORDER BY DATE(sales_date)
        """
        df = pd.read_sql(sql, conn)

    df['y']  = np.log1p(df['y'])
    df['ds'] = pd.to_datetime(df['ds'])
    return df


def make_holidays_df(years):
    """
    fixed_holidays 딕셔너리를 바탕으로 Prophet용 holidays DataFrame 생성
    """
    rows = []
    for y in years:
        for name, (m, d) in fixed_holidays.items():
            try:
                rows.append({'ds': pd.Timestamp(year=y, month=m, day=d), 'holiday': name})
            except ValueError:
                continue
    return pd.DataFrame(rows)

def train_and_save():
    """
    1) 데이터 로드
    2) Prophet 모델 학습
    3) joblib으로 모델 직렬화 저장
    """
    df = load_global_sales()
    years = df['ds'].dt.year.unique()
    holidays_df = make_holidays_df(years)

    model = Prophet(
        growth='linear',
        changepoint_prior_scale=0.01,
        daily_seasonality=True,
        weekly_seasonality=True,
        yearly_seasonality=False,
        holidays=holidays_df
    )
    model.fit(df)

    # 저장 디렉터리 없으면 생성
    os.makedirs('models', exist_ok=True)
    # 전역 모델 파일로 저장
    joblib.dump(model, 'models/global_sales_prophet.pkl')
    print("✔️ 모델 학습 및 저장 완료:", pd.Timestamp.now())

if __name__ == "__main__":
    # 즉시 한 번 학습
    train_and_save()

    # 3️⃣ 스케줄러 설정: 매일 자정(00:00)에 학습 실행
    scheduler = BlockingScheduler(timezone="Asia/Seoul")
    scheduler.add_job(train_and_save, 'cron', hour=0, minute=0)
    print("📅 매일 자정 재학습 스케줄러 시작")
    scheduler.start()
