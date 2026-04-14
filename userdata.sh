#!/bin/bash
# ============================================================
#  LocalEats - Launch Template 사용자 데이터
#  용도  : ASG가 인스턴스를 띄울 때마다 자동 실행
#  선행  : ami_bake.sh 로 구운 AMI 사용 필수
#  Updated: 2026-04-14
# ============================================================

set -xe
exec > /var/log/userdata.log 2>&1
echo "===== 인스턴스 초기화 시작: $(date) ====="

REGION="ap-northeast-2"

# SSM에서 값을 가져오는 함수 (실패 시 기본값 반환)
get_ssm() {
  aws ssm get-parameter --region "$REGION" --name "$1" --with-decryption \
      --query Parameter.Value --output text 2>/dev/null || echo "$2"
}


# ============================================================
# 1. SSM Parameter Store에서 크리덴셜 로드
# ============================================================
echo "[1/4] SSM에서 환경 변수 로드"
DB_HOST=$(get_ssm "/localeats/prod/DB_HOST"           "REPLACE_WITH_RDS_ENDPOINT")
DB_NAME=$(get_ssm "/localeats/prod/DB_NAME"           "localeats")
DB_USER=$(get_ssm "/localeats/prod/DB_USER"           "localeats_user")
DB_PASSWORD=$(get_ssm "/localeats/prod/DB_PASSWORD"   "REPLACE_WITH_DB_PASSWORD")
REDIS_HOST=$(get_ssm "/localeats/prod/REDIS_HOST"     "REPLACE_WITH_REDIS_ENDPOINT")
DJANGO_SECRET_KEY=$(get_ssm "/localeats/prod/DJANGO_SECRET_KEY" "REPLACE_WITH_SECRET_KEY")
S3_BUCKET=$(get_ssm "/localeats/prod/S3_BUCKET"       "localeats-media")
MONITORING_IP=$(get_ssm "/localeats/prod/MONITORING_IP" "192.168.20.10")
EFS_ID=$(get_ssm "/localeats/prod/EFS_ID"             "")
DOMAIN=$(get_ssm "/localeats/prod/DOMAIN"             "")

echo "  DB_HOST      : $DB_HOST"
echo "  REDIS_HOST   : $REDIS_HOST"
echo "  EFS_ID       : $EFS_ID"


# ============================================================
# 2. .env 파일 생성 (크리덴셜 주입)
# ============================================================
echo "[2/4] .env 파일 생성"
APP_DIR="/home/ec2-user/localeats"
mkdir -p "$APP_DIR"

cat > "$APP_DIR/.env" << ENVEOF
# ── Django ──────────────────────────────────────
DJANGO_SETTINGS_MODULE=config.settings
SECRET_KEY=${DJANGO_SECRET_KEY}
DEBUG=False
ALLOWED_HOSTS=${DOMAIN:-*}
CSRF_TRUSTED_ORIGINS=https://${DOMAIN:-localhost}

# ── Database (Aurora PostgreSQL) ─────────────────
DB_ENGINE=django.db.backends.postgresql
DB_HOST=${DB_HOST}
DB_PORT=5432
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}

# ── Cache (Redis ElastiCache) ────────────────────
REDIS_URL=redis://${REDIS_HOST}:6379/0

# ── Storage (S3) ─────────────────────────────────
AWS_STORAGE_BUCKET_NAME=${S3_BUCKET}
AWS_S3_REGION_NAME=ap-northeast-2
AWS_S3_CUSTOM_DOMAIN=${S3_BUCKET}.s3.ap-northeast-2.amazonaws.com

# ── Media (EFS 마운트 경로) ───────────────────────
MEDIA_ROOT=/mnt/efs/media

# ── Monitoring ────────────────────────────────────
MONITORING_IP=${MONITORING_IP}
ENVEOF

chown ec2-user:ec2-user "$APP_DIR/.env"
chmod 600 "$APP_DIR/.env"


# ============================================================
# 3. EFS 마운트 (다중 인스턴스 미디어 파일 공유)
# ============================================================
echo "[3/4] EFS 마운트"
if [ -n "$EFS_ID" ]; then
  mount -t efs -o tls "${EFS_ID}":/ /mnt/efs/media
  echo "${EFS_ID}:/ /mnt/efs/media efs tls,_netdev 0 0" >> /etc/fstab
  echo "  EFS 마운트 완료: $EFS_ID"
else
  echo "  [경고] EFS_ID 미설정 - 미디어 파일이 로컬 저장됩니다"
  echo "         SSM /localeats/prod/EFS_ID 등록 필요"
fi


# ============================================================
# 4. 서비스 시작
# ============================================================
echo "[4/4] 서비스 시작"

systemctl daemon-reload
systemctl start gunicorn
systemctl restart nginx
systemctl start amazon-cloudwatch-agent
systemctl start xray
systemctl start node_exporter
systemctl start amazon-ssm-agent


# ============================================================
# 완료
# ============================================================
echo ""
echo "===== 인스턴스 초기화 완료: $(date) ====="
echo ""
echo "[ 서비스 상태 ]"
echo "  Gunicorn   : $(systemctl is-active gunicorn)"
echo "  Nginx      : $(systemctl is-active nginx)"
echo "  CloudWatch : $(systemctl is-active amazon-cloudwatch-agent)"
echo "  X-Ray      : $(systemctl is-active xray)"
echo "  Node Exp   : $(systemctl is-active node_exporter)"
echo "  CodeDeploy : $(systemctl is-active codedeploy-agent)"
