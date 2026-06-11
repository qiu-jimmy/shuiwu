# 导入文件到知识库接口文档

## 接口概述

本文档描述了从文件系统导入文件到知识库的接口。

**Base URL**: `http://127.0.0.1:8000`

**认证方式**: Bearer Token

---

## 接口信息

- **接口地址**: `POST /api/knowledge-base/import-files`
- **接口说明**: 从文件系统选择已上传的文件，批量导入到指定知识库
- **权限要求**: 需要登录认证
- **Content-Type**: `application/json`

---

## 功能特性

1. **批量导入**: 支持一次导入多个文件
2. **自动处理**: 自动从 OSS 下载文件、分块、向量化
3. **重名检测**: 自动检测并拒绝同名文件
4. **权限验证**: 只能导入自己上传的文件
5. **部分失败**: 单个文件失败不影响其他文件导入
6. **自定义分块**: 支持自定义分块规则和参数

---

## 请求头

```json
{
  "Authorization": "Bearer <your_token>"
}
```

---

## 请求参数

### Body 参数（JSON格式）

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| kb_name | string | 是 | - | 目标知识库名称 |
| user_id | string | 是 | - | 用户ID |
| file_ids | array[string] | 是 | - | 文件ID列表（从文件系统选择） |
| chunking_rule | string | 否 | fixed_size | 分块规则 |
| chunk_size | integer | 否 | 5000 | 分块大小 |
| chunk_overlap | integer | 否 | 200 | 分块重叠 |
| metadata | object | 否 | null | 额外的元数据 |

### 分块规则说明

| chunking_rule | 说明 |
|---------------|------|
| fixed_size | 固定大小分块（默认） |
| semantic | 语义分块 |
| recursive | 递归分块 |

---

## 响应格式

### 成功响应（200 OK）

**全部成功**:
```json
{
  "code": 1,
  "message": "成功导入 3 个文件",
  "data": {
    "results": [
      {
        "status": "success",
        "message": "文档 增值税政策.pdf 已成功导入知识库",
        "filename": "增值税政策.pdf",
        "file_id": "file_1234567890abcdef",
        "user_id": "user_123"
      },
      {
        "status": "success",
        "message": "文档 企业所得税.docx 已成功导入知识库",
        "filename": "企业所得税.docx",
        "file_id": "file_2345678901bcdef",
        "user_id": "user_123"
      },
      {
        "status": "success",
        "message": "文档 个人所得税.txt 已成功导入知识库",
        "filename": "个人所得税.txt",
        "file_id": "file_3456789012cdefg",
        "user_id": "user_123"
      }
    ]
  }
}
```

**部分成功**:
```json
{
  "code": 1,
  "message": "导入完成，成功 2 个，失败 1 个",
  "data": {
    "results": [
      {
        "status": "success",
        "message": "文档 增值税政策.pdf 已成功导入知识库",
        "filename": "增值税政策.pdf",
        "file_id": "file_1234567890abcdef",
        "user_id": "user_123"
      },
      {
        "status": "error",
        "message": "文件不存在或无权访问",
        "file_id": "file_invalid_id",
        "user_id": "user_123"
      }
    ]
  }
}
```

### 失败响应

#### 请求错误（400）

**文件ID列表为空**:
```json
{
  "code": 0,
  "message": "file_ids 不能为空",
  "data": null
}
```

**文件已存在**:
```json
{
  "code": 1,
  "message": "导入完成，成功 0 个，失败 1 个",
  "data": {
    "results": [
      {
        "status": "error",
        "message": "文件名 '增值税政策.pdf' 已存在于知识库中，不能重名",
        "file_id": "file_abc123",
        "filename": "增值税政策.pdf",
        "user_id": "user_123"
      }
    ]
  }
}
```

#### 未授权（401）

```json
{
  "code": 0,
  "message": "未提供认证token",
  "data": null
}
```

---

## 使用示例

### 示例1：导入单个文件

```bash
curl -X POST "http://127.0.0.1:8000/api/knowledge-base/import-files" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "kb_name": "测试知识库",
    "user_id": "user_1234567890",
    "file_ids": ["file_abc123def456"]
  }'
```

### 示例2：批量导入多个文件

```bash
curl -X POST "http://127.0.0.1:8000/api/knowledge-base/import-files" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "kb_name": "测试知识库",
    "user_id": "user_1234567890",
    "file_ids": [
      "file_abc123def456",
      "file_789xyz012345",
      "file_678def456abc"
    ],
    "chunking_rule": "fixed_size",
    "chunk_size": 3000,
    "chunk_overlap": 200
  }'
```

### 示例3：自定义分块规则

```bash
curl -X POST "http://127.0.0.1:8000/api/knowledge-base/import-files" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "kb_name": "测试知识库",
    "user_id": "user_1234567890",
    "file_ids": ["file_abc123"],
    "chunking_rule": "semantic",
    "chunk_size": 1000,
    "chunk_overlap": 100,
    "metadata": {
      "source": "legal_docs",
      "category": "tax"
    }
  }'
```

---

## 导入流程

当调用此接口时，系统会执行以下操作：

### 1. 文件验证
- 检查文件是否存在
- 验证文件所有权（只能导入自己上传的文件）
- 检查文件名是否重复

### 2. 下载文件
- 从阿里云 OSS 下载文件内容
- 支持超时时间：30秒

### 3. 文档处理
- 根据文件扩展名选择读取器
- 支持的格式：PDF、DOCX、PPTX、CSV、Excel、TXT 等
- 自动进行文档分块
- 生成向量嵌入

### 4. 数据更新
- 将文档添加到知识库表
- 更新 `knowledge_base_registry` 的 `document_ids` 字段
- 更新 `business.files` 表的 `kb_name` 字段
- 更新知识库表的 `filters` 字段

### 5. 清理临时文件
- 删除下载的临时文件

---

## 支持的文件格式

| 文件类型 | 扩展名 | 说明 |
|---------|--------|------|
| PDF | .pdf | 支持 |
| Word | .docx | 支持 |
| PowerPoint | .pptx | 支持 |
| Excel | .xlsx, .xls | 支持 |
| CSV | .csv | 支持 |
| 文本 | .txt, .md | 支持 |

---

## 错误码说明

| code | message | 说明 |
|------|---------|------|
| 1 | 操作成功 | 请求处理成功 |
| 0 | 错误信息 | 请求处理失败，message包含具体错误原因 |

---

## 常见错误

### 错误1：file_ids 不能为空

```json
{
  "code": 0,
  "message": "file_ids 不能为空",
  "data": null
}
```

**解决方案**：请求体中必须提供 `file_ids` 参数

---

### 错误2：文件不存在或无权访问

```json
{
  "code": 1,
  "message": "导入完成，成功 0 个，失败 1 个",
  "data": {
    "results": [
      {
        "status": "error",
        "message": "文件不存在或无权访问",
        "file_id": "file_invalid_id",
        "user_id": "user_123"
      }
    ]
  }
}
```

**原因**：
1. 文件ID不存在
2. 文件不属于当前用户

**解决方案**：
1. 确认 file_id 正确
2. 确认文件是当前用户上传的

---

### 错误3：文件名已存在

```json
{
  "code": 1,
  "message": "导入完成，成功 0 个，失败 1 个",
  "data": {
    "results": [
      {
        "status": "error",
        "message": "文件名 '增值税政策.pdf' 已存在于知识库中，不能重名",
        "file_id": "file_abc123",
        "filename": "增值税政策.pdf",
        "user_id": "user_123"
      }
    ]
  }
}
```

**解决方案**：
1. 先删除知识库中的同名文件
2. 或重命名文件后再导入

---

### 错误4：从OSS下载文件失败

```json
{
  "code": 1,
  "message": "导入完成，成功 0 个，失败 1 个",
  "data": {
    "results": [
      {
        "status": "error",
        "message": "从OSS下载文件失败，状态码: 404",
        "file_id": "file_abc123",
        "filename": "test.pdf",
        "user_id": "user_123"
      }
    ]
  }
}
```

**原因**：OSS 上的文件不存在或无法访问

**解决方案**：
1. 确认文件已正确上传到 OSS
2. 检查 OSS 配置是否正确

---

## 注意事项

1. **权限要求**：
   - 只能导入自己上传的文件
   - 需要先通过文件管理接口上传文件

2. **文件名唯一性**：
   - 同一知识库中不能有同名文件
   - 包括扩展名的完整文件名

3. **处理时间**：
   - 大文件可能需要较长时间处理
   - 建议前端显示加载状态

4. **重名处理**：
   - 系统会拒绝同名文件的导入
   - 不会覆盖已有文件

5. **批量导入**：
   - 部分文件失败不影响其他文件
   - 返回结果中包含每个文件的状态

---

## 配套接口

### 上传文件到文件系统

```
POST /api/files/upload
```

先通过此接口上传文件到 OSS，获取 file_id，然后再调用导入接口。

### 查询文件列表

```
GET /api/files/list
```

查看文件系统中的所有文件，获取 file_id 和 file_name。

### 查询知识库文档

```
POST /api/knowledge-base/search
```

搜索知识库中的文档，验证导入是否成功。

---

## 前端对接示例

### JavaScript/TypeScript

```typescript
// 导入文件到知识库
async function importFilesToKnowledgeBase(
  kbName: string,
  userId: string,
  fileIds: string[],
  options?: {
    chunkingRule?: 'fixed_size' | 'semantic' | 'recursive';
    chunkSize?: number;
    chunkOverlap?: number;
    metadata?: Record<string, any>;
  }
) {
  const response = await fetch('http://127.0.0.1:8000/api/knowledge-base/import-files', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${userToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      kb_name: kbName,
      user_id: userId,
      file_ids: fileIds,
      chunking_rule: options?.chunkingRule || 'fixed_size',
      chunk_size: options?.chunkSize || 5000,
      chunk_overlap: options?.chunkOverlap || 200,
      metadata: options?.metadata
    })
  });

  const data = await response.json();
  return data;
}

// 使用示例
importFilesToKnowledgeBase('测试知识库', 'user_123', ['file_abc123', 'file_def456'])
  .then(result => {
    if (result.code === 1) {
      console.log('导入成功:', result.message);

      // 处理每个文件的结果
      result.data.results.forEach(r => {
        if (r.status === 'success') {
          console.log(`  ✓ ${r.filename} 导入成功`);
        } else {
          console.error(`  ✗ ${r.filename} 导入失败: ${r.message}`);
        }
      });
    }
  })
  .catch(error => {
    console.error('导入失败:', error);
  });
```

### Vue.js 示例

```vue
<template>
  <div>
    <el-button @click="handleImport" :loading="importing">
      导入到知识库
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { ElMessage } from 'element-plus';

const importing = ref(false);

const handleImport = async () => {
  importing.value = true;

  try {
    const result = await importFilesToKnowledgeBase(
      '测试知识库',
      'user_123',
      selectedFileIds.value
    );

    if (result.code === 1) {
      const successCount = result.data.results.filter(r => r.status === 'success').length;
      const failCount = result.data.results.filter(r => r.status === 'error').length;

      ElMessage.success(`导入完成：成功 ${successCount} 个，失败 ${failCount} 个`);

      // 显示详细结果
      result.data.results.forEach(r => {
        if (r.status === 'error') {
          ElMessage.error(`${r.filename}: ${r.message}`);
        }
      });
    } else {
      ElMessage.error(result.message);
    }
  } catch (error) {
    ElMessage.error('导入失败');
  } finally {
    importing.value = false;
  }
};
</script>
```

---

## 数据流向

```
┌─────────┐     上传      ┌──────────┐     导入      ┌─────────────┐
│ 前端/APP │ ──────────> │ 文件系统 │ ──────────> │  知识库(RAG) │
└─────────┘             └──────────┘             └─────────────┘
                           │                          │
                           v                          v
                      ┌──────────┐              ┌─────────────┐
                      │   OSS   │              │ PostgreSQL  │
                      └──────────┘              └─────────────┘
```

---

## 性能建议

1. **批量导入**：建议每次导入不超过 10 个文件
2. **文件大小**：单个文件建议不超过 50MB
3. **异步处理**：对于大文件，建议前端显示进度条
4. **重试机制**：网络超时时可以实现自动重试

---

## 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| v1.0 | 2026-01-22 | 初始版本 |
