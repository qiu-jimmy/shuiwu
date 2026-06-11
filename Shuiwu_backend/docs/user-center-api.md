# 用户个人中心 API 文档

## 基础信息

- **基础路径**: `/api/user/center`
- **认证方式**: JWT Bearer Token
- **Content-Type**: `application/json`

## 接口列表

### 1. 获取个人信息

```
GET /api/user/center
Authorization: Bearer <token>
```

**响应示例：**
```json
{
  "code": 1,
  "message": "success",
  "data": {
    "user_id": "user_1234567890",
    "nickname": "测试用户",
    "avatar_url": "https://...",
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

### 2. 更新昵称

```
PUT /api/user/center/nickname
Authorization: Bearer <token>
Content-Type: application/json

{
  "nickname": "新昵称"
}
```

**参数：**
- `nickname`: string (1-50字符)

---

### 3. 更新头像

```
PUT /api/user/center/avatar
Authorization: Bearer <token>
Content-Type: application/json

{
  "avatar_data": "iVBORw0KGgoAAAANSUhEUg...",
  "file_name": "avatar.jpg"
}
```

**参数：**
- `avatar_data`: Base64 编码的图片数据
- `file_name`: 文件名（包含扩展名）

**限制：**
- 最大 5MB
- 支持 JPG、PNG、GIF

**响应：**
```json
{
  "code": 1,
  "message": "头像更新成功",
  "data": {
    "avatar_url": "https://bucket.oss-cn-hangzhou.aliyuncs.com/avatars/..."
  }
}
```

---

### 4. 绑定/更换手机号

```
PUT /api/user/center/phone
Authorization: Bearer <token>
Content-Type: application/json

{
  "phone": "13900139000",
  "sms_code": "123456"
}
```

**参数：**
- `phone`: string (11位数字)
- `sms_code`: string (6位数字)

---

### 5. 修改密码

```
PUT /api/user/center/password
Authorization: Bearer <token>
Content-Type: application/json

{
  "old_password": "password123",
  "new_password": "newpassword456"
}
```

**参数：**
- `old_password`: string (旧密码)
- `new_password`: string (新密码，6-50字符)

---

### 6. 账号注销

```
DELETE /api/user/center
Authorization: Bearer <token>
Content-Type: application/json

{
  "password": "password123",
  "reason": "不再使用"
}
```

**参数：**
- `password`: string (密码，用于验证身份)
- `reason`: string (可选，注销原因)

**说明：** 软删除，用户状态变为 `disabled`

---

### 7. 获取隐私设置

```
GET /api/user/center/privacy
Authorization: Bearer <token>
```

**响应示例：**
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

```
PUT /api/user/center/privacy
Authorization: Bearer <token>
Content-Type: application/json

{
  "show_phone": true,
  "show_member_info": true,
  "allow_search": true
}
```

**参数：**
- `show_phone`: boolean
- `show_member_info`: boolean
- `allow_search`: boolean

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| `USER_NOT_FOUND` | 用户不存在 |
| `INVALID_OLD_PASSWORD` | 旧密码错误 |
| `INVALID_PASSWORD` | 密码错误 |
| `PHONE_ALREADY_BOUND` | 手机号已被占用 |
| `INVALID_BASE64` | 无效的 Base64 数据 |
| `FILE_TOO_LARGE` | 文件过大（>5MB） |
| `OSS_NOT_INITIALIZED` | OSS 服务未初始化 |
| `UPDATE_FAILED` | 更新失败 |

---

## 数据库迁移

```bash
psql -U postgres -d Agno -f app/infra/sql/migration_user_center_20250119.sql
```

---

## 前端示例

### JavaScript (Fetch)

```javascript
// 获取个人信息
const response = await fetch('http://127.0.0.1:8000/api/user/center', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
const data = await response.json();
console.log(data.data);

// 更新头像
const fileInput = document.querySelector('#avatar');
const file = fileInput.files[0];
const reader = new FileReader();

reader.onload = async (e) => {
  const base64Data = e.target.result;

  const response = await fetch('http://127.0.0.1:8000/api/user/center/avatar', {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      avatar_data: base64Data,
      file_name: file.name
    })
  });

  const result = await response.json();
  console.log(result.data.avatar_url);
};

reader.readAsDataURL(file);
```

---

## Postman 测试

详见：[user-center-postman-guide.md](user-center-postman-guide.md)
