#!/bin/bash

# 1. 시스템 업데이트 및 패키지 설치
sudo dnf -y update
sudo dnf -y install python3 python3-pip python3-devel httpd httpd-devel gcc git mariadb105-devel

# 2. Python 가상환경 생성 및 설정
cd /home/ec2-user
python3 -m pip install virtualenv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install django==3.11 mysqlclient mod_wsgi

# 2. 프로젝트 디렉터리 구성 및 Apache 설정
git clone https://github.com/choijongun/django_sample.git localeats
sudo tee /etc/httpd/conf.d/django.conf > /dev/null << EOF
<VirtualHost *:80>
    ServerName localhost
    DocumentRoot /home/ec2-user/localeats
    ErrorLog logs/localeats-error_log
    CustomLog logs/localeats-access_log combined

    <Directory "/home/ec2-user/localeats">
        Require all granted
    </Directory>

    WSGIPassAuthorization On
    WSGIProcessGroup django
    WSGIDaemonProcess django python-home=/home/ec2-user/venv python-path=/home/ec2-user/localeats
    WSGIScriptAlias / /home/ec2-user/localeats/config/wsgi.py

    <Directory /home/ec2-user/localeats/config>
        <Files wsgi.py>
            Require all granted
        </Files>
    </Directory>

    Alias /static/ /home/ec2-user/localeats/staticfiles/
    <Directory /home/ec2-user/localeats/staticfiles>
        Require all granted
    </Directory>

    Alias /media/ /home/ec2-user/localeats/media/
    <Directory "/home/ec2-user/localeats/media">
                Require all granted
    </Directory>
</VirtualHost>
EOF
chmod 701 /home/ec2-user
sudo chown -R ec2-user:ec2-user /home/ec2-user/localeats/staticfiles
mkdir /home/ec2-user/localeats/media
sudo chown apache:apache /home/ec2-user/localeats/media

# 3. mod_wsgi 모듈 설정 및 Apache 시작 실행
MOD_WSGI_CONFIG=$(mod_wsgi-express module-config)
echo "$MOD_WSGI_CONFIG" | sudo tee /etc/httpd/conf.modules.d/00-wsgi.conf > /dev/null
sudo systemctl enable httpd
sudo systemctl start httpd
