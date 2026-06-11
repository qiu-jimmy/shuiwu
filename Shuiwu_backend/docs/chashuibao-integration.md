# 查税宝经营风险报告对接文档

## 概述

查税宝经营风险报告第三方服务对接，提供企业税务风险评估报告生成功能。

## 功能特性

- **自动生成授权链接**：用户通过 H5 链接进行税局账号授权，自动生成报告
- **手动上传报表**：支持手动上传税务报表文件生成报告
- **获取报告数据**：获取已生成的经营风险报告详细数据
- **回调通知**：支持报告生成完成后的回调通知

## 安装依赖

```bash
pip install -r requirements.txt
```

新增依赖：
- `gmssl>=3.2.1` - 国密 SM2 签名算法库

## 环境变量配置

在 `.env` 文件中添加以下配置：

```env
# 查税宝配置
CHASHUIBAO_BASE_URL=https://testcsbplus.dianzuanmao.com  # 测试环境
# CHASHUIBAO_BASE_URL=https://csb.dianzuanmao.com  # 正式环境
CHASHUIBAO_THIRD_PARTY_ID=your_third_party_id  # 第三方令牌
CHASHUIBAO_PRIVATE_KEY=your_sm2_private_key  # SM2 私钥（十六进制字符串）
CHASHUIBAO_PUBLIC_KEY=your_sm2_public_key  # SM2 公钥（可选，用于验签）
```

## SM2 签名说明

### 签名规则

所有参数（剔除 `sign` 字段）按照第一个字符的键值 ASCII 码递增排序，如果遇到相同字符则按照第二个字符的键值 ASCII 码递增排序，以此类推。将排序后的参数与其对应值组合成 `参数=参数值` 的格式，并用 `&` 字符连接起来，生成待签名字符串。然后使用 SM2 进行签名。

### 签名工具使用

```python
from app.services.chashuibao.sm2_signature import ChashuibaoSignature

# 设置私钥
ChashuibaoSignature.set_private_key(private_key)

# 生成签名
params = {
    'thirdPartyId': 'your_token',
    'taxpayerId': 'encrypted_taxpayer_id',
    'companyName': 'encrypted_company_name',
}
sign = ChashuibaoSignature.sign(params)
```

### 字段加密

纳税人识别号和企业名称需要使用 SM2 公钥加密：

```python
# 加密字段
encrypted_taxpayer_id = ChashuibaoSignature.encrypt_field(
    plaintext='91330100MA2XXX00XX',
    public_key=chashuibao_public_key
)
```

## API 接口

### 1. 获取授权链接

**接口**: `POST /api/chashuibao/authorization`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| thirdPartyId | String | 是 | 令牌（加密） |
| sign | String | 是 | 签名 |
| taxpayerId | String | 是 | 纳税人识别号（加密） |
| companyName | String | 是 | 企业名称（加密） |
| reportType | String | 否 | 报告类型，默认 2（经营风险报告） |
| cburl | String | 是 | 授权完成回调页面 |
| year | String | 否 | 年度（经营风险报告传参） |
| quarter | String | 否 | 季度（经营风险报告传参） |
| reportLogo | String | 否 | 封面logo(网络地址url) |
| watermark | String | 否 | 水印(网络地址url) |
| coverUrl | String | 否 | 封面(网络地址url) |
| isAnonymity | Integer | 否 | 是否匿名（0-否，1-是） |

**响应示例**:

```json
{
  "code": 1,
  "message": "获取授权链接成功",
  "data": {
    "orderNo": "unique_order_no",
    "initialUrl": "https://example.com/authorize?..."
  }
}
```

### 2. 手动上传报表

**接口**: `POST /api/chashuibao/upload_report`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| firmName | String | 是 | 企业名称 |
| year | String | 是 | 年度 |
| quarter | String | 是 | 季度 |
| phone | String | 是 | 用户手机号 |
| taxpayerNo | String | 是 | 纳税人识别号 |
| reportNo | String | 是 | 报告编号（唯一，长度32） |
| accountingCriterionId | String | 是 | 会计准则编码 |
| taxpayerType | String | 是 | 纳税人类型编码 |
| taxpayerName | String | 是 | 企业名称 |
| zzsFileBs | String | 是 | 增值税文件标识(1单文件0多文件) |
| zzs | String | 否 | 增值税文件URL（完整，单文件） |
| zzsZb | String | 否 | 增值税文件URL-主表(多文件） |
| ... | ... | ... | 其他文件 URL |

**注意**：参与签名字段包括 `firmName`、`taxpayerNo`、`thirdPartyId`

### 3. 获取指标报告数据

**接口**: `GET /api/chashuibao/report_data`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| report_no | String | 是 | 报告编号 |

**响应数据结构**:

```json
{
  "code": 1,
  "message": "获取报告数据成功",
  "data": {
    "firmInfo": {
      "taxpayerName": "企业名称",
      "taxpayerNo": "91330100MA2XXX00XX",
      "industry": "行业",
      ...
    },
    "fxList": [...],
    "taxInfo": {...},
    "cwzkfx": [...],
    "lrbfx": [...],
    "reportUrl": "https://example.com/report.pdf"
  }
}
```

### 4. 报告生成完成通知回调

**接口**: `POST /api/chashuibao/notify/callback`

**回调参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orderNo | String | 否 | 订单号 |
| state | String | 是 | 成功状态（0-失败，1-成功） |
| reportType | String | 是 | 报告类型（2-经营报告） |

**注意**：此接口需要公网可访问，建议在查税宝后台配置回调地址。

## 测试

运行测试脚本：

```bash
python test/test_chashuibao_e2e.py
```

## 代码结构

```
app/
├── api/
│   └── chashuibao.py          # API 路由
├── services/
│   └── chashuibao/
│       ├── __init__.py
│       ├── sm2_signature.py    # SM2 签名工具
│       └── chashuibao_service.py  # 服务层
└── schemas/
    └── chashuibao.py          # Pydantic 模型
```

## 常见问题

### 1. SM2 私钥格式

SM2 私钥应该是 64 位十六进制字符串。

### 2. 字段加密

纳税人识别号和企业名称需要使用查税宝提供的 SM2 公钥加密后传输。

### 3. 报告编号生成

报告编号需要保证唯一，建议使用 UUID 或其他唯一标识生成。

### 4. 回调地址配置

需要在查税宝后台配置报告生成完成通知的回调地址。

## 参考资料

- [查税宝第三方服务文档](../经营风险报告文档-对外文档.docx)
- [GMSSL 文档](https://github.com/duanhongyi/gmssl)
