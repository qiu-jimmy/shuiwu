# 管理员删除知识库文档接口文档

## 接口概述

本文档描述了管理员删除知识库文档的接口，供管理员使用。

**Base URL**: `http://127.0.0.1:8000`

**认证方式**: Bearer Token（管理员权限）

---

## 接口信息

- **接口地址**: `POST /api/knowledge-base/admin/remove-documents`
- **接口说明**: 管理员从指定用户的知识库中删除文档
- **权限要求**: 管理员权限（is_admin = true）
- **Content-Type**: `application/json`

---

## 请求头

```json
{
  "Authorization": "Bearer <your_admin_token>"
}
```

---

## 请求参数

### Body 参数（JSON格式）

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| kb_name | string | 是 | - | 知识库名称 |
| user_id | string | 是 | - | 知识库所属用户ID |
| file_ids | array[string] | 否* | - | 要删除的文件ID列表（与filenames二选一） |
| filenames | array[string] | 否* | - | 要删除的文件名列表（与file_ids二选一） |
| delete_from_file_system | boolean | 否 | false | 是否同时从文件系统删除（business.files表） |

**注意**：`file_ids` 和 `filenames` 必须提供其中一个，不能同时提供。

---

## 响应格式

### 成功响应（200 OK）

```json
{
  "code": 1,
  "message": "成功删除 2 个文件",
  "data": {
    "results": [
      {
        "status": "success",
        "message": "文件 增值税政策.docx 已从知识库删除",
        "file_id": "file_abc123",
        "filename": "增值税政策.docx"
      },
      {
        "status": "success",
        "message": "文件 企业所得税.docx 已从知识库删除",
        "file_id": "file_def456",
        "filename": "企业所得税.docx"
      }
    ]
  }
}
```

### 部分成功响应

```json
{
  "code": 1,
  "message": "删除完成，成功 1 个，失败 1 个",
  "data": {
    "results": [
      {
        "status": "success",
        "message": "文件 增值税政策.docx 已从知识库删除",
        "file_id": "file_abc123",
        "filename": "增值税政策.docx"
      },
      {
        "status": "error",
        "message": "文件 file_wrong_id 不存在",
        "file_id": "file_wrong_id"
      }
    ]
  }
}
```

### 失败响应

#### 未授权（401）

```json
{
  "code": 0,
  "message": "未提供认证token",
  "data": null
}
```

#### 权限不足（403）

```json
{
  "code": 0,
  "message": "需要管理员权限",
  "data": null
}
```

#### 参数错误（400）

```json
{
  "code": 0,
  "message": "file_ids 和 filenames 必须提供其中一个",
  "data": {
    "results": [
      {
        "status": "error",
        "message": "file_ids 和 filenames 必须提供其中一个"
      }
    ]
  }
}
```

---

## 使用示例

### 示例1：按 file_id 删除文档

```bash
curl -X POST "http://127.0.0.1:8000/api/knowledge-base/admin/remove-documents" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "kb_name": "测试知识库3",
    "user_id": "user_1234567890abcdef",
    "file_ids": ["file_abc123", "file_def456"],
    "delete_from_file_system": false
  }'
```

### 示例2：按 filename 删除文档

```bash
curl -X POST "http://127.0.0.1:8000/api/knowledge-base/admin/remove-documents" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "kb_name": "测试知识库3",
    "user_id": "user_1234567890abcdef",
    "filenames": ["增值税政策.docx", "企业所得税.docx"],
    "delete_from_file_system": false
  }'
```

### 示例3：删除并从文件系统移除

```bash
curl -X POST "http://127.0.0.1:8000/api/knowledge-base/admin/remove-documents" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "kb_name": "测试知识库3",
    "user_id": "user_1234567890abcdef",
    "file_ids": ["file_abc123"],
    "delete_from_file_system": true
  }'
```

---

## 删除操作说明

### 执行流程

当调用此接口时，系统会执行以下操作：

1. **权限验证**：验证当前用户是否具有管理员权限（is_admin = true）

2. **文件查询**：根据提供的 file_id 或 filename 查询对应的文件信息

3. **从知识库表删除**：
   - 从 `knowledge.kb_{user_id}_{kb_name}` 表中删除所有匹配的文档记录
   - 匹配条件：`meta_data->>'filename'` 或 `filters->>'filename'`

4. **更新注册表**：
   - 从 `knowledge.knowledge_base_registry` 表的 `document_ids` 数组中移除对应的 file_id

5. **处理文件系统**（可选）：
   - 如果 `delete_from_file_system = false`：只更新 `business.files` 表的 `kb_name` 字段为 `null`
   - 如果 `delete_from_file_system = true`：永久删除 `business.files` 表中的记录

### 影响范围

| 操作 | 影响范围 |
|------|---------|
| 删除知识库文档 | `knowledge.kb_{user_id}_{kb_name}` 表中的记录 |
| 更新注册表 | `knowledge.knowledge_base_registry.document_ids` 数组 |
| 取消文件关联 | `business.files.kb_name` 设置为 `null` |
| 永久删除文件 | `business.files` 表记录被删除（需要 delete_from_file_system=true） |

---

## 错误码说明

| code | message | 说明 |
|------|---------|------|
| 1 | 操作成功 | 请求处理成功 |
| 0 | 错误信息 | 请求处理失败，message包含具体错误原因 |

---

## 常见错误

### 错误1：未提供 file_ids 或 filenames

```json
{
  "code": 0,
  "message": "file_ids 和 filenames 必须提供其中一个",
  "data": {
    "results": [
      {
        "status": "error",
        "message": "file_ids 和 filenames 必须提供其中一个"
      }
    ]
  }
}
```

**解决方案**：提供 `file_ids` 或 `filenames` 参数

---

### 错误2：同时提供了 file_ids 和 filenames

```json
{
  "code": 0,
  "message": "file_ids 和 filenames 只能提供其中一个",
  "data": {
    "results": [
      {
        "status": "error",
        "message": "file_ids 和 filenames 只能提供其中一个"
      }
    ]
  }
}
```

**解决方案**：只提供其中一个参数

---

### 错误3：文件不属于指定用户

```json
{
  "code": 1,
  "message": "删除完成，成功 0 个，失败 1 个",
  "data": {
    "results": [
      {
        "status": "error",
        "message": "文件 file_abc123 不属于用户 user_xyz",
        "file_id": "file_abc123"
      }
    ]
  }
}
```

**解决方案**：确认 `user_id` 参数正确

---

### 错误4：权限不足

```json
{
  "code": 0,
  "message": "需要管理员权限",
  "data": null
}
```

**解决方案**：确保当前登录用户具有管理员角色（admin 或 super_admin）

---

## 注意事项

1. **权限要求**：此接口只对管理员开放，普通用户无法访问

2. **数据安全**：
   - 删除操作不可逆，请谨慎操作
   - 建议在删除前先查询确认文件信息

3. **文件名匹配**：
   - 按 `filename` 删除时，会删除所有匹配的文档（包括多个分块）
   - 一个文件可能有多个分块，删除时会全部删除

4. **文件系统删除**：
   - `delete_from_file_system=false`：只取消知识库关联，文件保留在文件系统
   - `delete_from_file_system=true`：永久删除，不可恢复

5. **批量操作**：
   - 支持批量删除，一次可删除多个文件
   - 部分成功时，会返回详细的成功/失败信息

---

## 配套接口

### 查询知识库文档列表

```
GET /api/knowledge-base/documents/{kb_name}?user_id={user_id}
```

返回知识库中的所有文档，可用于查看可删除的文件。

### 查询文件系统列表

```
GET /api/files/list
```

返回文件系统中的所有文件，可查看文件的 file_id 和 file_name。

---

## 前端对接示例

### JavaScript/TypeScript

```typescript
// 按文件ID删除
async function removeDocumentsByFileIds(
  kbName: string,
  userId: string,
  fileIds: string[],
  deleteFromFileSystem: boolean = false
) {
  const response = await fetch('http://127.0.0.1:8000/api/knowledge-base/admin/remove-documents', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${adminToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      kb_name: kbName,
      user_id: userId,
      file_ids: fileIds,
      delete_from_file_system: deleteFromFileSystem
    })
  });

  const data = await response.json();
  return data;
}

// 按文件名删除
async function removeDocumentsByFilenames(
  kbName: string,
  userId: string,
  filenames: string[],
  deleteFromFileSystem: boolean = false
) {
  const response = await fetch('http://127.0.0.1:8000/api/knowledge-base/admin/remove-documents', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${adminToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      kb_name: kbName,
      user_id: userId,
      filenames: filenames,
      delete_from_file_system: deleteFromFileSystem
    })
  });

  const data = await response.json();
  return data;
}

// 使用示例
removeDocumentsByFileIds('测试知识库3', 'user_123', ['file_abc'], false)
  .then(result => {
    if (result.code === 1) {
      console.log('删除成功:', result.message);
      result.data.results.forEach(r => {
        if (r.status === 'success') {
          console.log('  -', r.message);
        }
      });
    }
  });
```

---

## 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| v1.0 | 2025-01-22 | 初始版本，支持管理员删除知识库文档 |
