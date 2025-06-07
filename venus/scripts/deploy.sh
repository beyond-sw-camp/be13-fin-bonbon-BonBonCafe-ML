#!/usr/bin/env bash

set -e  # 오류 발생 시 스크립트 중단
echo "> Starting deploy script..."

REPOSITORY=/home/ec2-user/app
FLASK_APP_DIR=/home/ec2-user/app
ENV_PATH=$FLASK_APP_DIR/.env
LOG_FILE=$FLASK_APP_DIR/app.log
VENV_DIR=$FLASK_APP_DIR/venv

cd $REPOSITORY

# Flask 앱 인스턴스 종료
echo "> Killing existing Flask (gunicorn) process if any..."
FLASK_PID=$(pgrep -f 'gunicorn.*app' || true)
if [ -z "$FLASK_PID" ]; then
  echo "> 종료할 Flask 애플리케이션이 없습니다."
else
  echo "> kill Flask app with PID: $FLASK_PID"
  kill -15 $FLASK_PID || echo "> kill 실패 - 이미 종료된 프로세스일 수 있음"
  sleep 2
fi

if [ -f "$ENV_PATH" ]; then
    source $ENV_PATH
fi

# 의존성 설치 (가상 환경 없이)
echo "> Installing dependencies"
pip install --no-cache-dir -r $FLASK_APP_DIR/requirements.txt

echo "> Starting Flask app with gunicorn"
cd $FLASK_APP_DIR
nohup gunicorn -w 4 app:app -b 0.0.0.0:8082 > $FLASK_APP_DIR/app.log 2>&1 &

echo "> Flask app has been started."
