#!/bin/bash
# Agent-Pilot v12 阿里云部署脚本
# 使用方法: bash deploy_v12_to_aliyun.sh

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
echo_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }
echo_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }

# 服务器配置
SERVER_IP="118.178.242.26"
SERVER_USER="root"
SERVER_PASSWORD="bcefghj@Github666"
DEPLOY_DIR="/opt/agent-pilot-v12"
SERVICE_NAME="agent-pilot-v12"

echo_info "🚀 开始部署 Agent-Pilot v12 到阿里云服务器"
echo_info "目标服务器: ${SERVER_USER}@${SERVER_IP}"
echo_info "部署目录: ${DEPLOY_DIR}"

# 1. 测试服务器连接
echo_info "📡 测试服务器连接..."
if sshpass -p "${SERVER_PASSWORD}" ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_IP} "echo 'Connection OK'"; then
    echo_success "服务器连接成功"
else
    echo_error "服务器连接失败，请检查网络和凭据"
    exit 1
fi

# 2. 备份旧版本
echo_info "💾 备份旧版本..."
sshpass -p "${SERVER_PASSWORD}" ssh ${SERVER_USER}@${SERVER_IP} "
    if [ -d '${DEPLOY_DIR}' ]; then
        backup_dir='/root/agent-pilot-backup-\$(date +%Y%m%d_%H%M%S)'
        echo '备份到: \$backup_dir'
        mv '${DEPLOY_DIR}' '\$backup_dir'
        echo '备份完成'
    fi
"

# 3. 创建部署目录并克隆代码
echo_info "📦 克隆最新代码..."
sshpass -p "${SERVER_PASSWORD}" ssh ${SERVER_USER}@${SERVER_IP} "
    mkdir -p ${DEPLOY_DIR}
    cd ${DEPLOY_DIR}
    
    # 克隆最新代码
    git clone https://github.com/bcefghj/Agent-Pilot.git .
    
    echo '代码克隆完成'
    echo '当前版本信息:'
    git log -1 --oneline
"

# 4. 上传环境配置
echo_info "⚙️  配置环境变量..."
sshpass -p "${SERVER_PASSWORD}" ssh ${SERVER_USER}@${SERVER_IP} "
    cd ${DEPLOY_DIR}
    
    # 创建生产环境配置
    cat > .env << 'EOL'
# === 飞书配置 ===
FEISHU_APP_ID=cli_a968cdd5fbf8dcc4
FEISHU_APP_SECRET=ctcVIYayUdPKeOpR8QyE7esxOKqrfCHQ

# === 火山引擎 ARK（已禁用，使用 MiMo/MiniMax） ===
# ARK_API_KEY=
# ARK_CHAT_URL=https://ark.cn-beijing.volces.com/api/coding/v3
# ARK_CHAT_MODEL=doubao-seed-2.0-pro
ARK_EMBED_URL=https://ark.cn-beijing.volces.com/api/v3
ARK_EMBED_MODEL=doubao-embedding-text-240715

# === MiniMax 备用 ===
MINIMAX_API_KEY=sk-cp-vX4T-YhmjkytkOexcwZ-uAdmALWR8ggXmtGOymuJQ1lfNLOR1phT0Ju09VggOTENL-y1pGe-KC4fTQppbzn_X_WPxVIApwG71PlvZHCGgfaIRH2zYoAI_RA
MINIMAX_BASE_URL=https://api.minimax.chat/v1
MINIMAX_MODEL=MiniMax-M2.7

# === 服务配置 ===
SERVER_HOST=0.0.0.0
BOT_PORT=8000
DASHBOARD_PORT=8001
SYNC_HUB_PORT=8002
DEBUG=false

# === Dashboard ===
DASHBOARD_PUBLIC_URL=http://118.178.242.26

# === Sync & Security ===
AGENT_PILOT_SHARE_SECRET=\$(openssl rand -hex 32)

EOL
    echo '环境配置完成'
"

# 5. 安装依赖
echo_info "📚 安装 Python 依赖..."
sshpass -p "${SERVER_PASSWORD}" ssh ${SERVER_USER}@${SERVER_IP} "
    cd ${DEPLOY_DIR}
    
    # 确保 Python 3.11+ 可用
    python3 --version
    
    # 创建虚拟环境
    python3 -m venv venv
    source venv/bin/activate
    
    # 升级 pip
    pip install --upgrade pip
    
    # 安装依赖
    pip install -r requirements.txt
    
    echo 'Python 依赖安装完成'
"

# 6. 创建 systemd 服务
echo_info "🔧 配置 systemd 服务..."
sshpass -p "${SERVER_PASSWORD}" ssh ${SERVER_USER}@${SERVER_IP} "
    # Bot 主服务
    cat > /etc/systemd/system/${SERVICE_NAME}-bot.service << 'EOL'
[Unit]
Description=Agent-Pilot v12 Bot Service
After=network.target

[Service]
Type=exec
User=root
WorkingDirectory=${DEPLOY_DIR}
Environment=PATH=${DEPLOY_DIR}/venv/bin
ExecStart=${DEPLOY_DIR}/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOL

    # Dashboard 服务
    cat > /etc/systemd/system/${SERVICE_NAME}-dashboard.service << 'EOL'
[Unit]
Description=Agent-Pilot v12 Dashboard Service
After=network.target

[Service]
Type=exec
User=root
WorkingDirectory=${DEPLOY_DIR}
Environment=PATH=${DEPLOY_DIR}/venv/bin
ExecStart=${DEPLOY_DIR}/venv/bin/python -m uvicorn dashboard.server:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOL

    # Sync Hub 服务
    cat > /etc/systemd/system/${SERVICE_NAME}-sync.service << 'EOL'
[Unit]
Description=Agent-Pilot v12 Sync Hub Service
After=network.target

[Service]
Type=exec
User=root
WorkingDirectory=${DEPLOY_DIR}
Environment=PATH=${DEPLOY_DIR}/venv/bin
ExecStart=${DEPLOY_DIR}/venv/bin/python -m core.sync.ws_server
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOL

    # 重载 systemd
    systemctl daemon-reload
    
    echo 'systemd 服务配置完成'
"

# 7. 配置 Nginx
echo_info "🌐 配置 Nginx 反向代理..."
sshpass -p "${SERVER_PASSWORD}" ssh ${SERVER_USER}@${SERVER_IP} "
    # 备份现有配置
    if [ -f /etc/nginx/sites-available/default ]; then
        cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.backup.\$(date +%Y%m%d_%H%M%S)
    fi
    
    # 创建 Agent-Pilot v12 配置
    cat > /etc/nginx/sites-available/agent-pilot-v12 << 'EOL'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    
    server_name 118.178.242.26;
    
    # Agent-Pilot v12 主要路由
    
    # Dashboard 前端
    location /dashboard {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }
    
    # API 路由
    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # WebSocket 同步
    location /ws/ {
        proxy_pass http://127.0.0.1:8002;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \"upgrade\";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
    
    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:8001/health;
    }
    
    # 静态文件 (Dashboard)
    location /static/ {
        proxy_pass http://127.0.0.1:8001;
    }
    
    # DAG 可视化
    location /v12/dag/ {
        proxy_pass http://127.0.0.1:8001;
    }
    
    # 首页重定向到 Dashboard
    location = / {
        return 301 /dashboard/pilot.html;
    }
    
    # 默认 404
    location / {
        return 404;
    }
}
EOL

    # 启用站点
    rm -f /etc/nginx/sites-enabled/default
    ln -sf /etc/nginx/sites-available/agent-pilot-v12 /etc/nginx/sites-enabled/
    
    # 测试配置
    nginx -t
    
    echo 'Nginx 配置完成'
"

# 8. 启动服务
echo_info "🚀 启动所有服务..."
sshpass -p "${SERVER_PASSWORD}" ssh ${SERVER_USER}@${SERVER_IP} "
    # 停止可能冲突的旧服务
    systemctl stop larkmentor* flowguard* 2>/dev/null || true
    
    # 启动 Agent-Pilot v12 服务
    systemctl enable ${SERVICE_NAME}-bot.service
    systemctl enable ${SERVICE_NAME}-dashboard.service  
    systemctl enable ${SERVICE_NAME}-sync.service
    
    systemctl start ${SERVICE_NAME}-bot.service
    systemctl start ${SERVICE_NAME}-dashboard.service
    systemctl start ${SERVICE_NAME}-sync.service
    
    # 重启 Nginx
    systemctl restart nginx
    
    echo '所有服务已启动'
"

# 9. 验证部署
echo_info "✅ 验证部署状态..."
sshpass -p "${SERVER_PASSWORD}" ssh ${SERVER_USER}@${SERVER_IP} "
    echo '=== 服务状态 ==='
    systemctl status ${SERVICE_NAME}-bot.service --no-pager -l
    echo
    systemctl status ${SERVICE_NAME}-dashboard.service --no-pager -l
    echo
    systemctl status ${SERVICE_NAME}-sync.service --no-pager -l
    echo
    systemctl status nginx --no-pager -l
    
    echo '=== 端口监听 ==='
    netstat -tlnp | grep -E ':(8000|8001|8002|80)\\s'
    
    echo '=== 最近日志 ==='
    journalctl -u ${SERVICE_NAME}-bot.service --no-pager -n 5
"

# 10. 健康检查
echo_info "🔍 执行健康检查..."
sleep 5

if curl -f -s http://118.178.242.26/health > /dev/null; then
    echo_success "✅ 健康检查通过！"
    echo_success "🎉 Agent-Pilot v12 部署成功！"
    echo
    echo_info "📱 访问地址:"
    echo "   Dashboard: http://118.178.242.26/dashboard/pilot.html"
    echo "   DAG 可视化: http://118.178.242.26/v12/dag/"
    echo "   健康检查: http://118.178.242.26/health"
    echo "   API 文档: http://118.178.242.26/api/docs"
else
    echo_warn "⚠️  健康检查失败，请检查服务日志"
    echo_info "查看日志命令:"
    echo "   ssh root@118.178.242.26"
    echo "   journalctl -u ${SERVICE_NAME}-bot.service -f"
fi

echo_success "🎊 部署完成！"