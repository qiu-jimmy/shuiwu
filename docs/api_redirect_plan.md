# API 重定向接入方案

## 1. 目标

在不立即重写原 FastAPI 后端的情况下，让原小程序请求逐步进入新的 LangChain Agent 服务。重定向应支持灰度、回滚和逐接口替换。

## 2. 推荐方式

### 方式 A：原后端内部转发

原后端保留 `/api/chat/*` 路由，但在路由内部根据开关转发到新服务。

优点：

- 小程序无需改接口地址
- 原鉴权、会员、日志可继续复用
- 灰度容易

缺点：

- 原后端仍需改少量路由代码

### 方式 B：网关/Nginx 路由

通过 Nginx 将部分路径转发到新服务。

优点：

- 原后端代码改动少
- 可以按路径快速切换

缺点：

- 用户级、套餐级灰度不如代码转发灵活
- SSE 代理配置需要仔细处理 buffering

### 方式 C：前端配置切换

小程序配置新的 API_BASE_URL 或部分页面调用新接口。

优点：

- 简单直接

缺点：

- 前端发版成本高
- 回滚和灰度复杂

## 3. 建议采用

第一阶段采用“原后端内部转发”，第二阶段再根据部署情况加 Nginx 路由。

## 4. 转发接口清单

| 原接口 | 新服务接口 | 切换优先级 |
|---|---|---|
| `/api/chat/chat` | `/api/chat/chat` | P1 |
| `/api/chat/full-feature` | `/api/chat/full-feature` | P0 |
| `/api/chat/supervisor` | `/api/chat/supervisor` | P1 |
| `/api/chat/rag` | `/api/chat/rag` | P0 |
| `/api/chat/contract-chat` | `/api/chat/contract-chat` | P1 |
| `/api/chat/sessions/*` | 暂保留旧服务 | P2 |

## 5. 转发伪代码

```python
@router.post("/full-feature")
async def full_feature_chat(request: Request, body: FullFeatureChatRequest):
    if should_route_to_new_agent(user_id=body.user_id, route="full-feature"):
        return await stream_proxy(
            target_url=f"{NEW_AGENT_BASE_URL}/api/chat/full-feature",
            request=request,
            json_body=body.model_dump(),
        )
    return await legacy_full_feature_chat(request, body)
```

## 6. SSE 注意事项

- 代理必须保持 `text/event-stream`
- 禁用响应缓冲
- 透传 `Authorization`
- 透传 trace id
- 客户端断开时要取消上游请求

## 7. 灰度规则

建议支持：

- 按用户 ID 白名单
- 按会员套餐
- 按接口路径
- 按百分比
- 按管理员开关

## 8. 回滚策略

任何接口发现异常时：

1. 关闭新 Agent 路由开关
2. 请求回到旧 Agno 实现
3. 保留新服务 trace 用于排查
4. 修复后重新小流量灰度
