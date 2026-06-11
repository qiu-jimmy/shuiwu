# 用户个人中心 API - Postman 测试指南

## 📦 文件说明

1. **`user-center-postman.json`** - Postman Collection（包含所有 API 请求）
2. **`user-center-environment.json`** - 环境变量配置
3. **本文档** - 快速开始指南

## 🚀 快速开始（3 步）

### 步骤 1: 导入环境变量

1. 打开 Postman
2. 点击右上角 **Manage Environments** 图标（⚙️）
3. 点击 **Import** 按钮
4. 选择 `user-center-environment.json`
5. 导入后在环境选择器中选择 `User Center Dev`

### 步骤 2: 导入 Collection

1. 点击左上角 **Import** 按钮
2. 选择 `user-center-postman.json`
3. 导入后会看到 `用户个人中心 API` collection

### 步骤 3: 修改登录凭证并测试

1. 展开 `用户个人中心 API` collection
2. 找到 `1. Login - Get Token` 请求
3. 修改请求体中的用户名和密码：
   ```json
   {
     "username": "your_phone_or_user_id",
     "password": "your_password"
   }
   ```
4. 点击 **Send** 执行登录（token 会自动保存）
5. 继续执行其他请求

## 📋 API 接口列表

| # | 接口 | 方法 | 路径 | 说明 |
|---|------|------|------|------|
| 1 | Login - Get Token | POST | `/api/auth/login` | 登录获取 JWT Token |
| 2 | Get User Profile | GET | `/api/user/center` | 获取个人信息 |
| 3 | Update Nickname | PUT | `/api/user/center/nickname` | 更新昵称 |
| 4 | Update Avatar | PUT | `/api/user/center/avatar` | 更新头像 |
| 5 | Bind Phone | PUT | `/api/user/center/phone` | 绑定/更换手机号 |
| 6 | Change Password | PUT | `/api/user/center/password` | 修改密码 |
| 7 | Get Privacy Settings | GET | `/api/user/center/privacy` | 获取隐私设置 |
| 8 | Update Privacy Settings | PUT | `/api/user/center/privacy` | 更新隐私设置 |
| 9 | Deactivate Account | DELETE | `/api/user/center` | 账号注销（谨慎） |

## 📝 详细测试说明

### 1. 登录获取 Token

**请求：**
```json
POST /api/auth/login
{
  "username": "13800138000",
  "password": "password123"
}
```

**响应：**
```json
{
  "code": 1,
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 604800,
    "user_info": {...}
  }
}
```

✅ Token 会自动保存到环境变量 `{{token}}`

---

### 2. 获取个人信息

**请求：**
```
GET /api/user/center
Authorization: Bearer {{token}}
```

**响应：**
```json
{
  "code": 1,
  "message": "success",
  "data": {
    "user_id": "user_1234567890",
    "nickname": "测试用户",
    "avatar_url": null,
    "phone": "13800138000",
    "status": "normal",
    "user_type": "individual",
    "member_level": "free",
    "member_expire_at": null,
    "register_time": "2025-01-19T10:00:00",
    "last_login_time": "2025-01-19T15:30:00"
  }
}
```

---

### 3. 更新昵称

**请求：**
```json
PUT /api/user/center/nickname
{
  "nickname": "新昵称测试"
}
```

**响应：**
```json
{
  "code": 1,
  "message": "昵称更新成功",
  "data": null
}
```

---

### 4. 更新头像

**请求：**
```json
PUT /api/user/center/avatar
{
  "avatar_data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
  "file_name": "avatar.png"
}
```

**说明：**
- `avatar_data`: Base64 编码的图片数据
- 支持带或不带 `data:image/png;base64,` 前缀
- 图片大小限制：最大 5MB

**准备 Base64 数据的方法：**

**Python 脚本：**
```python
import base64

with open("avatar.jpg", "rb") as f:
    base64_data = base64.b64encode(f.read()).decode("utf-8")
    print(base64_data)
```

**在线工具：**
- https://www.base64-image.de/

**响应：**
```json
{
  "code": 1,
  "message": "头像更新成功",
  "data": {
    "avatar_url": "https://bucket.oss-cn-hangzhou.aliyuncs.com/avatars/user_xxx/xxx.jpg"
  }
}
```

---

### 5. 绑定/更换手机号

**请求：**
```json
PUT /api/user/center/phone
{
  "phone": "13900139000",
  "sms_code": "123456"
}
```

**说明：**
- `phone`: 新手机号，11位数字
- `sms_code`: 短信验证码（当前版本可填任意6位数字）

**响应：**
```json
{
  "code": 1,
  "message": "手机号绑定成功",
  "data": null
}
```

---

### 6. 修改密码

**请求：**
```json
PUT /api/user/center/password
{
  "old_password": "password123",
  "new_password": "newpassword456"
}
```

**响应：**
```json
{
  "code": 1,
  "message": "密码修改成功",
  "data": null
}
```

⚠️ **注意：** 修改密码后需要使用新密码重新执行步骤 1

---

### 7. 获取隐私设置

**请求：**
```
GET /api/user/center/privacy
Authorization: Bearer {{token}}
```

**响应：**
```json
{
  "code": 1,
  "message": "success",
  "data": {
    "show_phone": false,
    "show_member_info": false,
    "allow_search": true
  }
}
```

**字段说明：**
- `show_phone`: 是否公开手机号
- `show_member_info`: 是否公开会员信息
- `allow_search`: 是否允许通过手机号搜索

---

### 8. 更新隐私设置

**请求：**
```json
PUT /api/user/center/privacy
{
  "show_phone": true,
  "show_member_info": true,
  "allow_search": true
}
```

**响应：**
```json
{
  "code": 1,
  "message": "隐私设置更新成功",
  "data": null
}
```

---

### 9. 账号注销

**⚠️⚠️⚠️ 警告：此操作会禁用账号，请谨慎测试！**

**请求：**
```json
DELETE /api/user/center
{
  "password": "password123",
  "reason": "测试账号注销功能"
}
```

**响应：**
```json
{
  "code": 1,
  "message": "账号已成功注销",
  "data": null
}
```

**说明：**
- 软删除：用户状态变为 `disabled`
- 需要提供正确的密码验证身份
- 数据仍保留在数据库中，但无法登录

---

## 🔧 环境变量说明

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `base_url` | `http://127.0.0.1:8000` | API 基础 URL |
| `token` | *自动填充* | JWT 访问令牌（登录后自动保存） |

---

## 🧪 测试流程建议

### 完整测试流程

1. **准备环境**
   ```bash
   # 执行数据库迁移
   psql -U postgres -d Agno -f app/infra/sql/migration_user_center_20250119.sql

   # 启动应用
   python main.py
   ```

2. **执行测试**
   - 按顺序执行 Collection 中的请求 1-8
   - 跳过请求 9（账号注销）或使用测试账号

3. **验证数据**
   - 使用 PostgreSQL 客户端查看数据库
   - 确认头像 URL 已保存到 OSS
   - 确认隐私设置已更新

### 快速批量运行

1. 右键点击 `用户个人中心 API` collection
2. 选择 **Run collection**
3. 选择要运行的请求（建议先跳过账号注销）
4. 点击 **Run** 按钮

---

## ❌ 常见错误

### 错误 1: "Could not validate credentials"

**原因：** Token 无效或过期

**解决方案：**
- 重新执行 `1. Login - Get Token`
- 检查环境变量中 `token` 是否有值

---

### 错误 2: "Connection refused"

**原因：** 服务未启动

**解决方案：**
- 确保应用正在运行：`python main.py`
- 检查 `base_url` 是否正确
- 检查端口是否被占用

---

### 错误 3: 头像上传失败

**原因：** OSS 配置问题或 Base64 数据无效

**解决方案：**
- 检查 `.env` 文件中的 OSS 配置
- 确认 Base64 数据格式正确
- 检查图片大小（不超过 5MB）
- 查看 Console 标签页中的错误信息

---

### 错误 4: "用户不存在"

**原因：** 用户 ID 无效或用户已被删除

**解决方案：**
- 确保已先执行登录
- 检查用户状态是否为 `normal`

---

## 📚 相关文档

- [API 完整文档](user-center-api.md)
- [数据库迁移脚本](../app/infra/sql/migration_user_center_20250119.sql)
- [服务层代码](../app/services/user/user_center_service.py)

---

## 💡 提示

1. **自动测试：** 每个请求都包含自动化测试脚本，会在 Tests 标签页中显示结果
2. **控制台日志：** 查看 Console 标签页可以看到详细的测试输出
3. **环境切换：** 可以创建多个环境（开发、测试、生产）快速切换
4. **Collection 分享：** 可以导出 Collection 分享给团队成员

---

## 🎯 下一步

完成测试后，您可以：
- 集成到前端应用
- 创建自动化测试脚本
- 监控 API 性能
- 编写 API 使用文档
