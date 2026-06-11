# LangChain Agent Rewrite

本目录用于承接“智税引擎”项目 Agent 部分的重写工作。目标是在不大规模改动原小程序前端和既有业务接口的前提下，先建设一套新的 LangChain Agent 架构，再通过 API 重定向/网关转发逐步替换原 Agno Agent 实现。

## 建设目标

- 保持原接口兼容：优先兼容 `/api/chat/chat`、`/api/chat/full-feature`、`/api/chat/supervisor`、`/api/chat/rag`、`/api/chat/contract-chat` 等接口形态。
- 重写 Agent 核心：使用 LangChain `create_agent` 作为第一阶段高层 Agent 循环，复杂 Supervisor 和多 Agent 编排预留 LangGraph 接口。
- 重写 RAG 方案：将“只选 1 个知识库 + 全文召回”升级为“多知识库路由 + chunk 级召回 + rerank + 证据约束”。
- 独立部署：新 Agent 服务可作为独立 FastAPI 服务运行，原后端通过反向代理、路由转发或内部 HTTP 调用接入。
- 可观测与可回滚：所有请求保留 trace_id，支持逐接口、逐用户、逐套餐灰度。

## 当前脚手架内容

```text
langchain_agent_rewrite/
  docs/
    agent_architecture_plan.md
    api_redirect_plan.md
    migration_roadmap.md
  src/tax_agent/
    api/                # 新 Agent 服务的 FastAPI 入口
    agents/             # Agent 工厂、提示词、Supervisor 编排
    rag/                # RAG 路由、检索、重排、证据模型
    services/           # 对话服务、会话、权限网关
    tools/              # LangChain 工具注册
  tests/
  scripts/
```

## 快速启动

```powershell
cd D:\zhulong_code\Shuiwu\修改前\langchain_agent_rewrite
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
uvicorn tax_agent.api.main:app --reload --port 8011
```

当前代码是脚手架，默认使用 mock LLM/retriever，便于先联调接口契约。接入真实模型、向量库、会员系统和旧后端数据库时，按 `docs/migration_roadmap.md` 分阶段推进。

## 参考方向

LangChain 官方文档当前推荐使用 `langchain.agents.create_agent` 创建工具调用 Agent；对于复杂状态、持久化、流式和多 Agent 编排，LangGraph 是更底层的编排框架。本脚手架先保留两层抽象：简单 Agent 先用 LangChain，高复杂流程后续升级到 LangGraph。
