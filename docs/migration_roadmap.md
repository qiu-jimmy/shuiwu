# LangChain Agent 迁移路线图

## P0：脚手架与接口契约

- 建立独立目录和 Python 包结构
- 实现 FastAPI 新 Agent 服务
- 兼容旧聊天接口请求体
- 兼容 SSE 输出
- 增加 mock Agent，便于前后端联调
- 输出 Agent 架构与 API 重定向文档

## P1：真实模型与工具

- 接入 OpenAI-compatible/Qwen 模型
- 使用 `langchain.agents.create_agent`
- 建立工具注册中心
- 接入时间工具
- 接入 mock RAG 工具
- 接入 mock 搜索工具

## P2：接入旧项目资源

- 读取旧 PostgreSQL 配置
- 兼容 `knowledge.knowledge_base_registry`
- 兼容已有 PgVector 表
- 接入旧会员权益与配额
- 接入旧会话或建立会话映射表

## P3：RAG 质量升级

- 多知识库 Top-N 路由
- Query rewrite
- Hybrid retrieval
- Rerank
- 精确引用
- 政策有效期过滤
- RAG 评估集

## P4：Supervisor 与复杂编排

- 用 LangGraph 重写 Supervisor
- 合同审查子图
- 企业报告多 Agent 子图
- MCP 工具桥
- 人工审核/税务师协作节点

## P5：生产化

- 灰度开关
- trace 与监控
- 错误告警
- 成本统计
- Prompt 版本管理
- 回归评测流水线
