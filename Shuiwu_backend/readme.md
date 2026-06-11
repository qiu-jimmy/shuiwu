# 税小通 - 部署文档

## 项目概述

**税小通**是一个基于 FastAPI 的智能税务咨询平台，提供 AI 驱动的税务咨询、文档处理、知识库管理和会员订阅服务。

### 技术栈

- **框架**: FastAPI 0.124.0 (异步)
- **AI 框架**: Agno 2.3.23
- **数据库**: PostgreSQL + SQLAlchemy 2.0.36
- **支付**: 微信支付 API v3
- **认证**: JWT + bcrypt

---

## 环境要求

### 系统要求

- **操作系统**: Linux (推荐 Ubuntu 20.04+ / CentOS 8+)
- **Python**: 3.9+
- **PostgreSQL**: 13+
- **内存**: 最低 2GB，推荐 4GB+
- **磁盘**: 最低 20GB

### Python 依赖

见 [requirements.txt](requirements.txt)

---

## 快速部署

### 1. 克隆代码

```bash
git clone <repository-url> Shuiwu_backend
cd Shuiwu_backend
git checkout feature/ycc  # 或主分支 master
```

### 2. 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

复制并编辑 `.env` 文件：

```bash
cp .env.example .env
vi .env
```

必填配置项：

```bash
# 数据库
PG_HOST=localhost
PG_PORT=5432
PG_USER=postgres
PG_PASSWORD=your_password
PG_DATABASE=Agno

# OpenAI
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1

# 微信支付（必需）
WECHAT_PAY_MCHID=1234567890
WECHAT_PAY_APPID=wxabcdef123456
WECHAT_PAY_CERT_SERIAL_NO=ABC123...
WECHAT_PAY_API_V3_KEY=xxx
WECHAT_PAY_PRIVATE_KEY_PATH=./certs/apiclient_key.pem
WECHAT_PAY_NOTIFY_URL=https://your-domain.com/api/payment/notify
WECHAT_PAY_CERT_DIR=./certs
```

### 4. 初始化数据库

```bash
# 数据库迁移 SQL 文件位于 app/infra/sql/migrations/
# 手动执行迁移文件或使用自动化脚本
```

### 5. 修复微信支付 SDK（重要！）

**微信支付官方 SDK 存在一个已知 bug，需要手动修复：**

```bash
python scripts/fix_wechatpay_sdk.py
```

该脚本会：
- 自动定位 `wechatpayv3` SDK 安装位置
- 备份原始文件
- 修复 `PUB_KEY_ID_` 格式解析问题

### 6. 启动服务

#### 开发模式（自动重载）

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 生产模式（单 Worker）

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

#### 使用 systemd 服务

创建 `/etc/systemd/system/shuiwu.service`:

```ini
[Unit]
Description=Shuiwu Backend Service
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/Shuiwu_backend
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable shuiwu
sudo systemctl start shuiwu
sudo systemctl status shuiwu
```

---

## 定时任务配置

项目包含分销系统结算任务，需要配置 crontab：

```bash
crontab -e
```

添加以下行（每小时执行一次）：

```cron
0 * * * * cd /path/to/Shuiwu_backend && /path/to/venv/bin/python scripts/run_tasks.py all >> logs/tasks.log 2>&1
```

任务说明：
- `settle` - 结算待处理佣金
- `upgrade` - 升级分销商等级
- `all` - 执行所有任务

---

## 微信支付配置详解

### 1. 获取商户证书

1. 登录 [微信支付商户平台](https://pay.weixin.qq.com/)
2. 下载商户证书（apiclient_cert.pem, apiclient_key.pem）
3. 获取 API 证书序列号
4. 设置 API v3 密钥

### 2. 证书文件放置

```
Shuiwu_backend/
├── certs/
│   ├── apiclient_cert.pem    # 商户证书
│   ├── apiclient_key.pem     # 商户私钥（注意保密！）
│   └── platform_public_key.pem  # 平台公钥（可选，运行脚本获取）
```

### 3. 获取平台公钥（可选）

如果需要手动配置平台公钥：

```bash
python scripts/get_wechatpay_platform_key.py
```

输出示例：

```
证书 1:
  序列号: 6B5D3...
  公钥ID: PUB_KEY_ID_6B5D3...
  有效期: 2024-01-01 ~ 2029-01-01

请在 .env 文件中添加：
WECHAT_PAY_PUBLIC_KEY_PATH=./certs/platform_public_key.pem
WECHAT_PAY_PUBLIC_KEY_ID=PUB_KEY_ID_6B5D3...
```

---

## 日志配置

### 日志目录结构

```
Shuiwu_backend/
├── logs/
│   ├── app.log          # 应用日志
│   ├── tasks.log        # 定时任务日志
│   └── error.log        # 错误日志
```

### 日志级别配置

在 `.env` 中设置：

```bash
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
LOG_DIR=logs
```

---

## 健康检查

服务启动后，访问以下地址验证：

```bash
# 健康检查
curl http://localhost:8000/health

# API 文档
http://localhost:8000/docs
```

预期响应：

```json
{"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}
```

---

## 常见问题

### Q1: 微信支付签名验证失败

**错误信息**: `invalid literal for int() with base 16: '0xPUB_KEY_ID_...'`

**解决方案**:

```bash
# 运行 SDK 修复脚本
python scripts/fix_wechatpay_sdk.py

# 重启服务
sudo systemctl restart shuiwu
```

### Q2: 数据库连接失败

**检查步骤**:

1. 确认 PostgreSQL 服务运行: `sudo systemctl status postgresql`
2. 验证连接: `psql -h localhost -U postgres -d Agno`
3. 检查防火墙: `sudo ufw allow 5432`

### Q3: 内存占用过高

**优化方案**:

1. 减少启动 workers 数量（微信支付 SDK 只支持单进程）
2. 使用 Nginx 作为反向代理进行负载均衡

### Q4: 定时任务不执行

**检查步骤**:

1. 验证 crontab: `crontab -l`
2. 检查日志: `tail -f logs/tasks.log`
3. 手动测试: `python scripts/run_tasks.py all`

---

## Nginx 反向代理配置

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 文件上传大小限制
    client_max_body_size 100M;
}
```

启用 HTTPS：

```bash
sudo certbot --nginx -d your-domain.com
```

---

## 监控和维护

### 日志轮转

创建 `/etc/logrotate.d/shuiwu`:

```
/path/to/Shuiwu_backend/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload shuiwu > /dev/null 2>&1 || true
    endscript
}
```

### 性能监控

推荐工具：
- **Prometheus + Grafana** - 指标监控
- **Sentry** - 错误追踪
- **New Relic** - APM 监控

---

## 安全建议

1. **生产环境必须**:
   - 使用 HTTPS
   - 配置防火墙
   - 定期更新依赖
   - 使用强密码和 JWT 密钥

2. **敏感文件保护**:
   - `.env` - 环境配置
   - `certs/` - 证书目录
   - `logs/` - 日志目录

3. **备份策略**:
   - 数据库每日备份
   - 证书文件异地备份
   - 代码版本控制

---

## 更新部署

### 代码更新

```bash
cd /path/to/Shuiwu_backend
git pull origin feature/ycc  # 或 master
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart shuiwu
```

### 数据库迁移

```bash
# 检查待执行的迁移
ls app/infra/sql/migrations/

# 按序号执行迁移文件
psql -h localhost -U postgres -d Agno -f app/infra/sql/migrations/006_xxx.sql
```

---

## 联系支持

- **文档**: [CLAUDE.md](CLAUDE.md)
- **问题反馈**: 提交 Issue
- **紧急联系**: 系统管理员

---

## 附录：目录结构

```
Shuiwu_backend/
├── app/
│   ├── api/           # API 路由
│   ├── services/       # 业务逻辑
│   ├── infra/         # 基础设施（数据库、支付）
│   ├── schemas/       # Pydantic 模型
│   └── agno/         # AI Agent 配置
├── scripts/          # 工具脚本
│   ├── run_tasks.py           # 定时任务
│   ├── fix_wechatpay_sdk.py   # SDK 修复
│   └── get_wechatpay_platform_key.py
├── docs/             # 文档
├── logs/             # 日志目录（运行时创建）
├── certs/            # 证书目录（需创建）
├── .env              # 环境配置（需创建）
├── main.py           # 应用入口
├── requirements.txt   # 依赖列表
└── readme.md         # 本文档
```
