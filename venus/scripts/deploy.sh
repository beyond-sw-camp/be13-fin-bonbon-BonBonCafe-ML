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

FLASK_PID=$(pgrep -f 'gunicorn.*app')
if [ -z $FLASK_PID ]
then
  echo "> 종료할 Flask 애플리케이션이 없습니다."
else
  echo "> kill Flask app with PID: $FLASK_PID"
  kill -15 $FLASK_PID
  sleep 2  # 5초 대신 조금 더 짧게
fi

if [ -f $ENV_PATH ]; then
    source $ENV_PATH
fi

echo "> Removing existing venv directory"
rm -rf $FLASK_APP_DIR/venv

echo "> Setting up new virtual environment"
python3 -m venv $FLASK_APP_DIR/venv
source $FLASK_APP_DIR/venv/bin/activate

echo "> Installing dependencies"
pip install -r $FLASK_APP_DIR/requirements.txt

# Flask 앱 시작
echo "> Starting Flask app with gunicorn"
cd $FLASK_APP_DIR
nohup gunicorn -w 4 app:app -b 0.0.0.0:5002 > $FLASK_APP_DIR/app.log 2>&1 &

echo "> Flask app has been started."
