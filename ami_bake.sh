#!/bin/bash
# ============================================================
#  LocalEats - AMI 굽기 스크립트
#  용도  : EC2에 직접 1회 실행 → AMI 스냅샷 생성
#  AMI   : Amazon Linux 2023 (kernel-6.1)
#  Region: ap-northeast-2
#  Updated: 2026-04-14
#
#  ※ 크리덴셜(DB, SECRET_KEY 등) 은 절대 여기 포함하지 않음
#     → 인스턴스 시작 시 userdata.sh 에서 SSM으로 주입
# ============================================================

set -xe
exec > /var/log/ami_bake.log 2>&1
echo "===== AMI 굽기 시작: $(date) ====="


# ============================================================
# 1. 시스템 업데이트
# ============================================================
echo "[1/9] 시스템 패키지 업데이트"
dnf update -y
dnf install -y --allowerasing gcc git curl wget unzip tar make \
    openssl-devel bzip2-devel libffi-devel


# ============================================================
# 2. Python 3.11 설치
# ============================================================
echo "[2/9] Python 3.11 설치"
dnf install -y python3.11 python3.11-devel
# /usr/local/bin에 심링크 → dnf가 쓰는 /usr/bin/python3(3.9)는 건드리지 않음
ln -sf /usr/bin/python3.11 /usr/local/bin/python3
ln -sf /usr/bin/python3.11 /usr/local/bin/python3.11
python3.11 --version
# pip 업그레이드
python3.11 -m ensurepip --upgrade 2>/dev/null || true


# ============================================================
# 3. Nginx 설치 + 설정
# ============================================================
echo "[3/9] Nginx 설치 및 설정"
dnf install -y nginx

# 메인 설정
cat > /etc/nginx/nginx.conf << 'EOF'
user nginx;
worker_processes auto;
worker_rlimit_nofile 65535;
error_log /var/log/nginx/error.log warn;
pid /run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include             /etc/nginx/mime.types;
    default_type        application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    access_log /var/log/nginx/access.log main;

    sendfile            on;
    tcp_nopush          on;
    tcp_nodelay         on;
    keepalive_timeout   65;
    server_tokens       off;

    client_max_body_size 10m;
    client_body_timeout  30s;

    gzip on;
    gzip_comp_level 5;
    gzip_min_length 256;
    gzip_proxied any;
    gzip_vary on;
    gzip_types
        text/plain text/css text/javascript
        application/json application/javascript
        application/x-javascript image/svg+xml;

    upstream gunicorn {
        server unix:/run/gunicorn.sock fail_timeout=0;
        keepalive 32;
    }

    include /etc/nginx/conf.d/*.conf;
}
EOF

# 가상호스트 설정
cat > /etc/nginx/conf.d/localeats.conf << 'EOF'
server {
    listen 80;
    server_name _;

    add_header X-Content-Type-Options  nosniff;
    add_header X-Frame-Options         SAMEORIGIN;
    add_header X-XSS-Protection        "1; mode=block";
    add_header Referrer-Policy         "strict-origin-when-cross-origin";

    location /static/ {
        alias /home/ec2-user/localeats/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    location /media/ {
        alias /mnt/efs/media/;
        expires 7d;
        add_header Cache-Control "public";
        access_log off;
    }

    location / {
        proxy_pass          http://gunicorn;
        proxy_http_version  1.1;
        proxy_set_header    Connection        "";
        proxy_set_header    Host              $host;
        proxy_set_header    X-Real-IP         $remote_addr;
        proxy_set_header    X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header    X-Forwarded-Proto $scheme;
        proxy_read_timeout  120s;
        proxy_connect_timeout 5s;
        proxy_send_timeout  120s;
        proxy_buffering     on;
        proxy_buffer_size   8k;
        proxy_buffers       8 8k;
    }

    location /health/ {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF

systemctl enable nginx


# ============================================================
# 4. Python 패키지 설치 (requirements.txt 기준)
# ============================================================
echo "[4/9] Python 패키지 설치"
python3.11 -m pip install --upgrade pip

# requirements.txt 직접 다운로드 후 설치 (sparse-checkout 대신)
curl -fsSL -o /tmp/requirements.txt \
    https://raw.githubusercontent.com/tjsrhffk-stu/2Team-git/main/requirements.txt
python3.11 -m pip install -r /tmp/requirements.txt
rm -f /tmp/requirements.txt


# ============================================================
# 5. AWS CodeDeploy Agent 설치
# ============================================================
echo "[5/9] CodeDeploy Agent 설치"
dnf install -y ruby
cd /tmp
wget https://aws-codedeploy-ap-northeast-2.s3.ap-northeast-2.amazonaws.com/latest/install
chmod +x ./install
./install auto
systemctl enable codedeploy-agent


# ============================================================
# 6. CloudWatch Agent 설치 + 설정
# ============================================================
echo "[6/9] CloudWatch Agent 설치"
dnf install -y amazon-cloudwatch-agent

cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'CWEOF'
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/nginx/access.log",
            "log_group_name": "/localeats/nginx/access",
            "log_stream_name": "{instance_id}"
          },
          {
            "file_path": "/var/log/nginx/error.log",
            "log_group_name": "/localeats/nginx/error",
            "log_stream_name": "{instance_id}"
          },
          {
            "file_path": "/var/log/gunicorn/access.log",
            "log_group_name": "/localeats/gunicorn/access",
            "log_stream_name": "{instance_id}"
          },
          {
            "file_path": "/var/log/gunicorn/error.log",
            "log_group_name": "/localeats/gunicorn/error",
            "log_stream_name": "{instance_id}"
          },
          {
            "file_path": "/var/log/userdata.log",
            "log_group_name": "/localeats/ec2/userdata",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  },
  "metrics": {
    "namespace": "LocalEats/EC2",
    "metrics_collected": {
      "cpu": {
        "measurement": ["cpu_usage_idle", "cpu_usage_user", "cpu_usage_system"],
        "metrics_collection_interval": 60
      },
      "mem": {
        "measurement": ["mem_used_percent", "mem_available_percent"],
        "metrics_collection_interval": 60
      },
      "disk": {
        "measurement": ["disk_used_percent"],
        "resources": ["/"],
        "metrics_collection_interval": 60
      },
      "net": {
        "measurement": ["net_bytes_recv", "net_bytes_sent"],
        "metrics_collection_interval": 60
      }
    }
  }
}
CWEOF

systemctl enable amazon-cloudwatch-agent


# ============================================================
# 7. AWS X-Ray Daemon 설치
# ============================================================
echo "[7/9] X-Ray Daemon 설치"
cd /tmp
wget https://s3.ap-northeast-2.amazonaws.com/aws-xray-assets.ap-northeast-2/xray-daemon/aws-xray-daemon-3.x.rpm
rpm -Uvh aws-xray-daemon-3.x.rpm
systemctl enable xray


# ============================================================
# 8. Prometheus Node Exporter 설치
# ============================================================
echo "[8/9] Prometheus Node Exporter 설치"
useradd --no-create-home --shell /bin/false prometheus 2>/dev/null || true

NODE_EXPORTER_VER="1.8.2"
cd /tmp
wget "https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VER}/node_exporter-${NODE_EXPORTER_VER}.linux-amd64.tar.gz"
tar xzf "node_exporter-${NODE_EXPORTER_VER}.linux-amd64.tar.gz"
cp "node_exporter-${NODE_EXPORTER_VER}.linux-amd64/node_exporter" /usr/local/bin/
chown prometheus:prometheus /usr/local/bin/node_exporter

cat > /etc/systemd/system/node_exporter.service << 'EOF'
[Unit]
Description=Prometheus Node Exporter
After=network.target

[Service]
User=prometheus
ExecStart=/usr/local/bin/node_exporter \
    --web.listen-address=":9100" \
    --collector.systemd \
    --collector.processes
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable node_exporter


# ============================================================
# 9. 디렉토리 구조 + Gunicorn 서비스 등록
# ============================================================
echo "[9/9] 디렉토리 구조 및 서비스 파일 등록"

# EFS 마운트 포인트
dnf install -y amazon-efs-utils
mkdir -p /mnt/efs/media

# 앱 디렉토리 (CodeDeploy가 코드 배포할 경로)
APP_DIR="/home/ec2-user/localeats"
mkdir -p "$APP_DIR"
chown ec2-user:ec2-user "$APP_DIR"

# Gunicorn 로그 디렉토리
mkdir -p /var/log/gunicorn
chown ec2-user:ec2-user /var/log/gunicorn

# Gunicorn worker 수 동적 계산 래퍼 스크립트
cat > /usr/local/bin/start-gunicorn.sh << 'EOF'
#!/bin/bash
WORKERS=$((2 * $(nproc) + 1))
exec /usr/local/bin/gunicorn \
    --workers "$WORKERS" \
    --bind unix:/run/gunicorn.sock \
    --timeout 120 \
    --graceful-timeout 30 \
    --access-logfile /var/log/gunicorn/access.log \
    --error-logfile /var/log/gunicorn/error.log \
    config.wsgi:application
EOF
chmod +x /usr/local/bin/start-gunicorn.sh

# Gunicorn systemd 서비스 (enable만, start는 userdata에서)
cat > /etc/systemd/system/gunicorn.service << 'EOF'
[Unit]
Description=LocalEats Gunicorn Daemon
After=network.target

[Service]
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/localeats
EnvironmentFile=/home/ec2-user/localeats/.env
ExecStart=/usr/local/bin/start-gunicorn.sh
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=60
PrivateTmp=true
Restart=on-failure
RestartSec=5
RestartPreventExitStatus=143

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable gunicorn

# SSM Agent
systemctl enable amazon-ssm-agent


# ============================================================
# 완료
# ============================================================
echo ""
echo "===== AMI 굽기 완료: $(date) ====="
echo "  이제 이 인스턴스로 AMI 스냅샷을 생성하세요."
echo "  생성된 AMI ID를 Launch Template에 등록하면 됩니다."
echo ""
echo "[ 설치 확인 ]"
echo "  Python     : $(python3 --version)"
echo "  Nginx      : $(nginx -v 2>&1)"
echo "  Gunicorn   : $(gunicorn --version)"
echo "  CodeDeploy : $(systemctl is-enabled codedeploy-agent)"
echo "  CloudWatch : $(systemctl is-enabled amazon-cloudwatch-agent)"
echo "  X-Ray      : $(systemctl is-enabled xray)"
echo "  Node Exp   : $(systemctl is-enabled node_exporter)"
