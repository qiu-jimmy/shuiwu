# 智税引擎 LangChain Agent 架构规划

## 1. 背景

当前项目 Agent 部分基于 Agno 实现，已经具备普通对话、Full Feature 对话、Supervisor、RAG、联网搜索、合同审查、MCP 工具和会话存储等能力。后续计划使用 LangChain 重写 Agent 核心，并通过 API 重定向逐步替换原有 Agent 服务。

重写时不建议一次性推翻全部业务逻辑。更稳妥的方式是先搭建独立 Agent 服务，复刻原接口契约，再逐步把旧路由转发到新服务。

## 2. 总体目标

1. 接口兼容：小程序前端无需第一时间改造。
2. 能力增强：RAG 从“单库选择 + 大段上下文”升级为“多库路由 + 精确证据”。
3. 编排清晰：将 Agent、工具、RAG、权限、会话和 API 适配拆开。
4. 可灰度：按接口、用户、会员套餐、功能开关逐步切流。
5. 可观测：记录工具调用、检索命中、模型输出、耗时、错误和配额消耗。

## 3. 推荐架构

```text
小程序/旧后端
    |
    | 原 API 路由或网关重定向
    v
New Agent API Service (FastAPI)
    |
    +-- API Adapter: 兼容旧请求/响应/SSE
    +-- Permission Gateway: 调用旧会员与配额体系
    +-- Session Gateway: 兼容旧会话与新会话存储
    +-- Agent Orchestrator
          |
          +-- Normal Tax Agent
          +-- Full Feature Tax Agent
          +-- RAG Agent
          +-- Contract Review Agent
          +-- Supervisor Router
          +-- Future LangGraph Workflows
    |
    +-- Tools Registry
          +-- RAG Search Tool
          +-- Web Search Tool
          +-- Time Tool
          +-- Contract Analysis Tool
          +-- MCP Tool Bridge
    |
    +-- RAG Engine
          +-- Query Rewrite
          +-- Knowledge Router
          +-- Hybrid Retriever
          +-- Reranker
          +-- Evidence Pack Builder
```

## 4. Agent 分层

### 4.1 Normal Tax Agent

用于基础税务问答，不默认挂载重工具。

能力：

- 税务基本概念解释
- 常见流程说明
- 简单政策适用说明
- 会话历史续问

约束：

- 涉及具体税率、日期、文号、扣除标准时，应升级到 Full Feature 或触发搜索/RAG。

### 4.2 Full Feature Tax Agent

用于会员高级模式，挂载 RAG、联网搜索、时间、MCP 等工具。

能力：

- 最新政策核验
- 法规与案例检索
- 多模态文件理解
- 个性化税务资料问答
- 工具自主决策

### 4.3 RAG Agent

用于指定知识库或用户文件问答。

能力：

- 指定知识库检索
- 系统知识库 + 用户知识库双路召回
- 引用证据返回
- 证据不足时拒绝确定性结论

### 4.4 Contract Review Agent

用于合同审查。

能力：

- 识别税费承担条款
- 识别发票开具条款风险
- 识别付款、验收、违约责任风险
- 输出风险等级、原因、影响和修改建议

### 4.5 Supervisor Router

第一阶段可先用规则 + LLM 分类实现，后续可升级 LangGraph。

分类维度：

- 是否税务相关
- 是否需要最新政策
- 是否需要用户文件
- 是否需要合同审查
- 是否需要企业风险报告
- 是否需要 MCP 工具
- 是否需要人工/税务师服务

## 5. RAG 新架构

当前项目 RAG 的核心问题是只选一个知识库、chunk 偏大、命中文件后全文召回、引用不够精确。新架构建议如下：

```text
User Query
  -> Query Rewrite
  -> Knowledge Router: 选 Top 2-3 知识库
  -> Hybrid Retriever: 每库召回 Top K
  -> Metadata Filter: 有效期、税种、地区、用户权限
  -> Reranker: 二次排序
  -> Evidence Pack: 精确证据包
  -> Agent Answer: 基于证据回答
```

### 5.1 知识库路由

不要只选 1 个知识库。建议维护 `kb_router_index`：

- 知识库名称
- 描述
- 适用税种
- 适用对象
- 典型问题
- 关键词
- 是否系统知识库
- 是否用户私有知识库

路由返回 Top-N 知识库。

### 5.2 分块策略

按文档类型切分：

- 法规政策：按章、条、款切分
- 办事指南：按步骤切分
- 案例：按案情、争议焦点、处理结果、依据切分
- 合同：按条款切分
- 表格：按 sheet、表块、行范围切分

### 5.3 证据模型

每条证据至少包含：

- `content`
- `source_title`
- `file_name`
- `kb_name`
- `chunk_id`
- `section_path`
- `page_number`
- `policy_doc_no`
- `effective_date`
- `expiry_date`
- `score`

### 5.4 回答约束

税务回答必须具备：

- 结论
- 政策依据
- 适用条件
- 操作建议
- 风险提示
- 不确定性说明

如果证据不足，不允许编造精确数字、日期、文号。

## 6. 工具体系

工具统一由 `ToolRegistry` 管理，根据请求上下文动态启用。

工具启用依据：

- 会员权益
- 接口类型
- 用户显式开关
- 问题分类结果
- 管理后台开关

第一阶段工具：

- `rag_search`
- `web_search`
- `get_current_time`
- `contract_review`
- `mcp_call`

## 7. API 兼容策略

新服务应直接兼容旧接口请求体：

- `user_id`
- `session_id`
- `message`
- `model_id`
- `temperature`
- `enable_search`
- `enable_rag`
- `knowledge_base`
- `images`
- `files`

输出保持 SSE：

```json
{"type": "content", "content": "..."}
{"type": "completed"}
{"type": "error", "message": "..."}
```

后续可扩展：

```json
{"type": "references", "data": [...]}
{"type": "tool_event", "tool": "rag_search", "status": "started"}
```

## 8. 第一阶段交付物

- 新 Agent 服务脚手架
- API 契约兼容层
- Mock Agent 流式响应
- Tool Registry
- RAG 模块接口定义
- 权限网关接口定义
- 会话网关接口定义
- 迁移路线文档

## 9. 第二阶段交付物

- 接入真实 OpenAI-compatible/Qwen 模型
- 接入旧 PostgreSQL 知识库 registry
- 接入 PgVector 检索
- 接入旧会员权益接口
- 原 `/api/chat/full-feature` 灰度转发

## 10. 第三阶段交付物

- LangGraph Supervisor
- 多 Agent 企业报告编排
- 合同审查专用证据库
- Rerank 与评估集
- LangSmith 或自建 trace 平台
