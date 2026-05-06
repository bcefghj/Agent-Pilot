#!/bin/bash
# Agent-Pilot v12 清理并重新部署脚本
# 清理旧服务和代码，部署最新的 v12 版本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
echo_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
echo_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 服务器信息
SERVER_IP="118.178.242.26"
SERVER_USER="root"
SERVER_PASSWORD="bcefghj@Github666"

echo_info "🚀 开始 Agent-Pilot v12 清理部署"
echo_info "目标服务器: ${SERVER_USER}@${SERVER_IP}"

# 创建 SSH 辅助脚本
cat > ssh_deploy.exp << 'EOF'
#!/usr/bin/expect -f
set timeout 120
set server_ip "118.178.242.26"
set server_user "root"
set server_password "bcefghj@Github666"

if {[llength $argv] == 0} {
    puts "用法: ./ssh_deploy.exp \"命令\""
    exit 1
}

set command [lindex $argv 0]
spawn ssh -o StrictHostKeyChecking=no $server_user@$server_ip $command

expect {
    "password:" {
        send "$server_password\r"
        expect eof
    }
    "Password:" {
        send "$server_password\r"
        expect eof
    }
    eof {}
    timeout {
        puts "连接超时"
        exit 1
    }
}
wait
EOF

chmod +x ssh_deploy.exp

echo_info "🧹 1. 清理旧服务和进程..."

./ssh_deploy.exp "
echo '=== 停止所有相关服务 ==='
systemctl stop larkmentor* flowguard* agent-pilot* 2>/dev/null || true
systemctl disable larkmentor* flowguard* agent-pilot* 2>/dev/null || true

echo '=== 杀死相关进程 ==='
pkill -f 'python.*uvicorn' 2>/dev/null || true
pkill -f 'python.*main.py' 2>/dev/null || true  
pkill -f 'python.*dashboard' 2>/dev/null || true
pkill -f 'nginx.*larkmentor' 2>/dev/null || true

echo '=== 清理 systemd 服务文件 ==='
rm -f /etc/systemd/system/larkmentor*
rm -f /etc/systemd/system/flowguard*
rm -f /etc/systemd/system/agent-pilot*
systemctl daemon-reload

echo '=== 检查进程清理结果 ==='
ps aux | grep -E '(larkmentor|flowguard|agent-pilot|uvicorn)' | grep -v grep || echo '进程清理完成'
"

echo_info "🗂️ 2. 备份并清理旧代码..."

./ssh_deploy.exp "
echo '=== 备份旧项目 ==='
cd /opt
if [ -d 'larkmentor' ]; then
    mv larkmentor larkmentor_backup_\$(date +%Y%m%d_%H%M%S)
    echo 'LarkMentor 已备份'
fi

if [ -d 'agent-pilot-v12' ]; then
    mv agent-pilot-v12 agent-pilot-v12_backup_\$(date +%Y%m%d_%H%M%S)  
    echo 'Agent-Pilot v12 已备份'
fi

if [ -d 'flowguard' ]; then
    mv flowguard flowguard_backup_\$(date +%Y%m%d_%H%M%S)
    echo 'FlowGuard 已备份'
fi

echo '=== 清理临时文件 ==='
rm -rf /tmp/*larkmentor* /tmp/*agent-pilot* /tmp/*flowguard* 2>/dev/null || true

echo '当前 /opt 目录:'
ls -la /opt/
"

echo_info "📦 3. 下载最新 Agent-Pilot v12 代码..."

./ssh_deploy.exp "
echo '=== 克隆最新代码 ==='
cd /opt
mkdir -p agent-pilot-v12
cd agent-pilot-v12

# 克隆最新的 v12 代码
git clone https://github.com/bcefghj/Agent-Pilot.git . --depth 1

echo '=== 验证代码版本 ==='
git log -1 --oneline
ls -la

echo '代码下载完成'
"

echo_info "⚙️ 4. 配置环境..."

./ssh_deploy.exp "
cd /opt/agent-pilot-v12

echo '=== 创建生产环境配置 ==='
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
cat .env | head -5
"

echo_info "🐍 5. 安装 Python 依赖..."

./ssh_deploy.exp "
cd /opt/agent-pilot-v12

echo '=== 检查 Python 版本 ==='
python3 --version

echo '=== 创建虚拟环境 ==='
python3 -m venv venv
source venv/bin/activate

echo '=== 升级 pip ==='
pip install --upgrade pip

echo '=== 安装项目依赖 ==='
pip install -r requirements.txt

echo '=== 验证关键依赖 ==='
pip list | grep -E '(fastapi|uvicorn|lark-oapi|pydantic)'

echo 'Python 环境设置完成'
"

echo_info "🔧 6. 创建 systemd 服务..."

./ssh_deploy.exp "
echo '=== 创建 Agent-Pilot v12 systemd 服务 ==='

# Bot 主服务
cat > /etc/systemd/system/agent-pilot-v12-bot.service << 'EOL'
[Unit]
Description=Agent-Pilot v12 Bot Service
After=network.target

[Service]
Type=exec
User=root
WorkingDirectory=/opt/agent-pilot-v12
Environment=PATH=/opt/agent-pilot-v12/venv/bin
ExecStart=/opt/agent-pilot-v12/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOL

# Dashboard 服务
cat > /etc/systemd/system/agent-pilot-v12-dashboard.service << 'EOL'
[Unit]
Description=Agent-Pilot v12 Dashboard Service  
After=network.target

[Service]
Type=exec
User=root
WorkingDirectory=/opt/agent-pilot-v12
Environment=PATH=/opt/agent-pilot-v12/venv/bin
ExecStart=/opt/agent-pilot-v12/venv/bin/python -m uvicorn dashboard.server:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOL

# Sync Hub 服务
cat > /etc/systemd/system/agent-pilot-v12-sync.service << 'EOL'
[Unit]
Description=Agent-Pilot v12 Sync Hub Service
After=network.target

[Service]
Type=exec
User=root
WorkingDirectory=/opt/agent-pilot-v12
Environment=PATH=/opt/agent-pilot-v12/venv/bin
ExecStart=/opt/agent-pilot-v12/venv/bin/python -m core.sync.ws_server
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOL

systemctl daemon-reload
echo 'systemd 服务创建完成'
"

echo_info "🌐 7. 配置 Nginx..."

./ssh_deploy.exp "
echo '=== 备份现有 Nginx 配置 ==='
if [ -f '/etc/nginx/sites-available/default' ]; then
    cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.backup.\$(date +%Y%m%d_%H%M%S)
fi

echo '=== 创建 Agent-Pilot v12 Nginx 配置 ==='
cat > /etc/nginx/sites-available/agent-pilot-v12 << 'EOL'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    
    server_name 118.178.242.26;
    
    # 主要路由
    
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
    
    # API 接口
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
    
    # 静态文件
    location /static/ {
        proxy_pass http://127.0.0.1:8001;
    }
    
    # DAG 可视化
    location /v12/ {
        proxy_pass http://127.0.0.1:8001;
    }
    
    # 首页重定向
    location = / {
        return 301 /dashboard/pilot.html;
    }
    
    # 其他请求
    location / {
        proxy_pass http://127.0.0.1:8001;
    }
}
EOL

# 启用新配置
rm -f /etc/nginx/sites-enabled/default
rm -f /etc/nginx/sites-enabled/*larkmentor*
rm -f /etc/nginx/sites-enabled/*flowguard*
ln -sf /etc/nginx/sites-available/agent-pilot-v12 /etc/nginx/sites-enabled/

# 测试配置
nginx -t

echo 'Nginx 配置完成'
"

echo_info "🚀 8. 启动所有服务..."

./ssh_deploy.exp "
echo '=== 启动 Agent-Pilot v12 服务 ==='

# 启用并启动服务
systemctl enable agent-pilot-v12-bot.service
systemctl enable agent-pilot-v12-dashboard.service
systemctl enable agent-pilot-v12-sync.service

systemctl start agent-pilot-v12-bot.service
systemctl start agent-pilot-v12-dashboard.service  
systemctl start agent-pilot-v12-sync.service

# 重启 Nginx
systemctl restart nginx

echo '=== 等待服务启动 ==='
sleep 10

echo '=== 检查服务状态 ==='
systemctl status agent-pilot-v12-bot.service --no-pager -l | head -10
systemctl status agent-pilot-v12-dashboard.service --no-pager -l | head -5
systemctl status agent-pilot-v12-sync.service --no-pager -l | head -5
systemctl status nginx --no-pager -l | head -5

echo '=== 检查端口监听 ==='
netstat -tlnp | grep -E ':(80|8000|8001|8002)\\s'

echo '部署完成！'
"

echo_info "✅ 9. 验证部署..."

sleep 15

# 健康检查
if curl -f -s -m 10 http://118.178.242.26/health > /dev/null 2>&1; then
    echo_success "🎉 部署成功！Agent-Pilot v12 正在运行"
    echo
    echo_info "🌐 访问地址："
    echo "   主页: http://118.178.242.26/"
    echo "   Dashboard: http://118.178.242.26/dashboard/pilot.html"
    echo "   DAG 可视化: http://118.178.242.26/v12/dag/"
    echo "   健康检查: http://118.178.242.26/health"
    echo "   API 文档: http://118.178.242.26/api/docs"
else
    echo_warn "⚠️ 服务可能还在启动中，请稍后检查"
    echo_info "查看日志: ssh root@118.178.242.26 'journalctl -u agent-pilot-v12-* -f'"
fi

# 清理临时文件
rm -f ssh_deploy.exp

echo_success "🎊 Agent-Pilot v12 部署完成！"
echo_info "💡 管理命令："
echo "   查看服务状态: ssh root@118.178.242.26 'systemctl status agent-pilot-v12-*'"
echo "   查看日志: ssh root@118.178.242.26 'journalctl -u agent-pilot-v12-bot.service -f'"
echo "   重启服务: ssh root@118.178.242.26 'systemctl restart agent-pilot-v12-*'"