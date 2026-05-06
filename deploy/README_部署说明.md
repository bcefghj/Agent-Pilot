# Agent-Pilot v12 阿里云部署说明

## 🚀 一键部署

### 前置要求
1. 安装 `sshpass` (macOS):
   ```bash
   brew install sshpass
   ```

2. 确保本地代码是最新版本:
   ```bash
   cd /Users/daishanghao/Desktop/20260506_飞书AI校园挑战赛_Agent-Pilot/github_public/Agent-Pilot
   git status  # 确保所有改动已提交推送
   ```

### 执行部署
```bash
cd /Users/daishanghao/Desktop/20260506_飞书AI校园挑战赛_Agent-Pilot/github_public/Agent-Pilot/deploy
bash deploy_v12_to_aliyun.sh
```

## 📋 部署包含内容

### 1. 服务架构
- **Bot 服务** (端口 8000): 飞书消息处理和 Agent 核心逻辑
- **Dashboard 服务** (端口 8001): Web 管理界面和 API
- **Sync Hub 服务** (端口 8002): WebSocket 实时同步

### 2. Nginx 配置
```
http://118.178.242.26/dashboard     → Dashboard 界面
http://118.178.242.26/api/          → API 接口
http://118.178.242.26/ws/           → WebSocket 同步
http://118.178.242.26/health        → 健康检查
http://118.178.242.26/              → 自动重定向到 Dashboard
```

### 3. 环境配置
- 飞书 App ID/Secret (已配置)
- 火山引擎 ARK API (已配置)  
- MiniMax API (备用，已配置)
- 随机生成的 WebSocket 安全密钥

## 🔧 部署后运维

### 查看服务状态
```bash
ssh root@118.178.242.26

# 查看所有服务状态
systemctl status agent-pilot-v12-*

# 查看具体服务
systemctl status agent-pilot-v12-bot.service
systemctl status agent-pilot-v12-dashboard.service  
systemctl status agent-pilot-v12-sync.service
```

### 查看日志
```bash
# 实时日志
journalctl -u agent-pilot-v12-bot.service -f

# 最近日志
journalctl -u agent-pilot-v12-bot.service -n 50

# 所有服务日志
journalctl -u agent-pilot-v12-* -n 20
```

### 重启服务
```bash
# 重启单个服务
systemctl restart agent-pilot-v12-bot.service

# 重启所有服务
systemctl restart agent-pilot-v12-*

# 重启 Nginx
systemctl restart nginx
```

### 更新代码
```bash
ssh root@118.178.242.26
cd /opt/agent-pilot-v12

# 拉取最新代码
git pull origin main

# 安装新依赖 (如有)
source venv/bin/activate
pip install -r requirements.txt

# 重启服务
systemctl restart agent-pilot-v12-*
```

## 🔍 健康检查

### 自动检查
```bash
curl http://118.178.242.26/health
```

### 手动验证
1. **Dashboard**: http://118.178.242.26/dashboard/pilot.html
2. **DAG 可视化**: http://118.178.242.26/v12/dag/
3. **API 文档**: http://118.178.242.26/api/docs

### 飞书 Bot 测试
1. 在飞书群里发消息 "帮我整理一下会议纪要"
2. 检查 Bot 是否正确响应和识别任务意图
3. 查看 Dashboard 是否显示任务进度

## 🚨 故障排查

### 常见问题

#### 1. 服务启动失败
```bash
# 检查端口占用
netstat -tlnp | grep -E ':(8000|8001|8002)'

# 检查 Python 环境
cd /opt/agent-pilot-v12
source venv/bin/activate
python --version
pip list | grep -E '(fastapi|uvicorn|lark-oapi)'
```

#### 2. Nginx 502 错误
```bash
# 检查 Nginx 配置
nginx -t

# 检查后端服务
curl http://127.0.0.1:8001/health
```

#### 3. 飞书 WebSocket 连接失败
```bash
# 检查 Sync Hub 服务
systemctl status agent-pilot-v12-sync.service
journalctl -u agent-pilot-v12-sync.service -n 10

# 检查 WebSocket 端口
curl -I http://127.0.0.1:8002/
```

### 回滚到旧版本
```bash
ssh root@118.178.242.26

# 停止 v12 服务
systemctl stop agent-pilot-v12-*
systemctl disable agent-pilot-v12-*

# 恢复旧版本 (如果需要)
# ls /root/agent-pilot-backup-*
# mv /root/agent-pilot-backup-XXXXXX /opt/agent-pilot-v12

# 启动旧服务
systemctl start larkmentor*
```

## 📊 监控指标

### 系统资源
```bash
# CPU 和内存
htop

# 磁盘空间
df -h

# 网络连接
netstat -an | grep ESTABLISHED | wc -l
```

### 应用指标
- **响应时间**: Dashboard -> 网络面板
- **任务成功率**: `/api/pilot/stats` 接口
- **WebSocket 连接数**: Sync Hub 日志
- **LLM 调用统计**: Bot 服务日志

---

## 🎉 部署成功后

恭喜！Agent-Pilot v12 已成功部署到阿里云。

**访问地址**: http://118.178.242.26/dashboard/pilot.html

现在可以在飞书中测试完整的 Agent-Pilot 工作流程了！