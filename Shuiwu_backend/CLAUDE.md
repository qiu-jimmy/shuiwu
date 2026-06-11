# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **"税小通" (Tax Helper)** - a tax advisory platform built as a FastAPI-based Backend Agent System with native MCP (Model Context Protocol) integration, built on the Agno AI framework. The system provides AI-powered tax consulting, document processing, knowledge management, and membership subscriptions for individual and business tax services in China.

**Technology Stack:**
- **Framework:** FastAPI 0.124.0 with async/await
- **AI Framework:** agno 2.3.23 (agent orchestration)
- **Database:** PostgreSQL with SQLAlchemy 2.0.36 (async + sync engines)
- **Document Processing:** PDF, DOCX, PPTX, CSV/Excel support via agno-ai
- **Search:** baidusearch, duckduckgo-search
- **Authentication:** python-jose (JWT), passlib with bcrypt
- **AI/ML:** sentence-transformers, PyTorch, Transformers, OpenAI API

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Start the development server (auto-reload disabled by default)
python main.py

# For development with auto-reload, use uvicorn directly:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Entry Points:**
- **[main.py](main.py)** (root) - uvicorn server configuration with single worker, connection limits (100 max concurrent), and custom logging
- **[app/main.py](app/main.py)** - FastAPI application initialization with lifespan management, middleware, and route registration

The application runs on `http://127.0.0.1:8000` by default. FastAPI auto-docs are available at `/docs`.

## Testing

Comprehensive end-to-end test scripts are available in the `test/` directory:

```bash
# Authentication & User Management
python test/test_auth_e2e.py           # Register, login, password change, token validation

# Knowledge Base Operations
python test/test_knowledge_e2e.py      # Create, upload, search, delete knowledge bases

# Member & Subscription
python test/test_member_e2e.py         # Membership subscription flows
python test/test_member_permission_e2e.py  # Permission-based access control

# Payment & Distribution
python test/test_payment_e2e.py        # WeChat Pay integration
python test/test_distribution_e2e.py   # Referral/affiliate system
python test/test_bind_invite_code.py   # Invite code binding

# Tax Services
python test/test_tax_declaration_e2e.py      # Individual tax declaration
python test/test_business_declaration_e2e.py # Business registration/tax filing

# Administration
python test/test_admin_e2e.py         # Admin operations
python test/test_admin_remove_documents.py  # Document moderation
python test/test_admin_import_files.py      # Batch file imports

# File Management
python test/test_files_e2e.py         # File upload/download
python test/test_import_files_e2e.py  # Import operations

# Feedback System
python test/test_feedback_e2e.py      # User feedback submissions

# WeChat Integration
python test/test_wechat_pay.py        # WeChat Pay specific tests
```

Tests use `httpx` for HTTP requests and include Windows console encoding fixes.

### Environment Configuration

Create a `.env` file with database credentials and API keys:

```env
# Database
PG_HOST=localhost
PG_PORT=5432
PG_USER=postgres
PG_PASSWORD=root
PG_DATABASE=Agno

# OpenAI Configuration
OPENAI_API_KEY=your_openai_key
OPENAI_BASE_URL=https://api.openai.com/v1

# Embeddings
EMBEDDER_DIMENSIONS=384  # or 1536 for larger models

# Optional Services
GPTZERO_API_KEY=          # AI content detection
LANGFUSE_HOST=            # Observability platform
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
OSS_ACCESS_KEY_ID=        # Alibaba OSS for file storage
OSS_ACCESS_KEY_SECRET=
OSS_BUCKET_NAME=
OSS_ENDPOINT=

# Logging
LOG_LEVEL=INFO
LOG_DIR=logs
```

## Architecture

The codebase follows **clean architecture** with clear separation of concerns:

### Layer Structure

```
app/
├── api/           # Presentation layer - FastAPI route handlers
├── services/      # Application layer - Business logic
├── agno/          # Domain layer - Agent orchestration
├── infra/         # Infrastructure layer - DB, HTTP, logging
└── schemas/       # Pydantic models for API validation
```

### Key Components

#### 1. **MCP Integration** (`app/agno/mcp/`, `app/services/mcp/`)
- **Service Registry Pattern:** `mcp_service_manager` maintains MCP service instances in memory
- **Repository Pattern:** `mcp_repository` handles database operations for MCP configurations
- **Dynamic Tool Loading:** MCP services expose tools that agents can use at runtime
- **Schema Isolation:** MCP uses a dedicated PostgreSQL schema (`mcp`)

Key files:
- [mcp_service.py](app/services/mcp/mcp_service.py) - Service lifecycle management
- [mcp_repository.py](app/services/mcp/mcp_repository.py) - Database operations
- [mcp_client.py](app/agno/mcp/mcp_client.py) - Agno PostgresDb factory

#### 2. **Agent System** (`app/agno/agents/`, `app/agno/runners/`, `app/agno/workflows/`)
- **Factory Pattern:** `agent_factory.py` creates different agent types:
  - **Normal Agent** - Basic tax consulting Q&A
  - **RAG Agent** - Knowledge base-enhanced conversations
  - **Search Agent** - Web search-enhanced responses
  - **Full Agent** - Combines all capabilities
  - **Contract Review Agent** - Legal document analysis
  - **Knowledge Selector Agent** - Routes to appropriate knowledge bases
- **Supervisor-Agent Workflow:** `workflows/supervisor_agent_workflow.py` implements a leader-expert pattern:
  - Supervisor Agent analyzes user input and outputs structured JSON decisions
  - Routes to specialist agents based on intelligent analysis (not just keyword matching)
  - Manages conversation context with history-aware query optimization
  - Uses custom `role_map` to store supervisor reasoning as `system` role for compatibility
- **Runner Pattern:** `runners/` execute agent workflows
- **Team Pattern:** `teams/` coordinate multi-agent collaboration

Agents use **Agno's PostgresDb** for session persistence, which is separate from the application database.

#### 3. **Database Architecture** ([db.py](app/infra/db.py))
- **Dual Engines:** Async engine (`asyncpg`) for API operations, sync engine (`psycopg`) for compatibility
- **Dependency Injection:** `get_db()` for async sessions, `get_sync_db()` for sync sessions
- **Schema Separation:** Business data in `business` schema, MCP data in `mcp` schema
- **Agno Integration:** `create_postgres_db()` creates Agno PostgresDb instances

**Schema Files:** Database schemas are defined in SQL files:
- [business_schema.sql](app/infra/sql/business_schema.sql) - Core business tables
- [knowledge_types_schema.sql](app/infra/sql/knowledge_types_schema.sql) - Knowledge base types
- [knowledge_base_registry_schema.sql](app/infra/sql/knowledge_base_registry_schema.sql) - Knowledge base registry

#### 4. **API Structure** (`app/api/`)
- **Router Pattern:** Each domain has its own router (mcp, models, chat, rag, etc.)
- **Schema Validation:** All request/response models use Pydantic schemas
- **Separation of Concerns:** Routes only handle HTTP; business logic is in services

### Active Routes

Currently **active** (registered in [app/main.py](app/main.py:298-389)):
- `/health` - Health check endpoint
- `/api/test` - Test endpoint
- `/api/mcp/*` - MCP service management
- `/api/auth/*` - Authentication (register, login, password management)
- `/api/models/*` - Model management
- `/api/chat/*` - Chat functionality with agent orchestration
- `/api/knowledge/*` - Knowledge base operations
- `/api/knowledge_type/*` - Knowledge base type management
- `/api/dashboard/*` - Dashboard/data visualization
- `/api/files/*` - File management with cloud storage
- `/api/member/*` - Membership subscriptions and VIP tiers
- `/api/distribution/*` - Referral/affiliate distribution system
- `/api/config/*` - System configuration management
- `/api/user_center/*` - User profile and settings
- `/api/payment/*` - WeChat Pay integration
- `/api/tax_declaration/*` - Individual tax declaration services
- `/api/business_declaration/*` - Business registration and tax filing
- `/api/admin/*` - Administrative operations
- `/api/enterprise_report/*` - Enterprise health analytics reports
- `/api/feedback/*` - User feedback system
- `/api/admin_feedback/*` - Admin feedback management (moderation)
- `/api/examples/*` - Permission system examples
- `/api/package-config/*` - Membership package configuration (CRUD for packages)

**Middleware:** JWT authentication middleware is applied globally with CORS enabled for all origins (development mode).

## Important Patterns

### Async-First Design
All operations use async/await. Database sessions use `AsyncSessionLocal` with FastAPI dependency injection:

```python
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

### MCP Service Lifecycle
1. Service configuration stored in PostgreSQL `mcp` schema
2. `mcp_service_manager` caches active `MCPTools` instances in memory
3. Services are lazy-loaded on first access
4. On app shutdown, all MCP connections are closed

### Agno PostgresDb vs App Database
- **App Database:** SQLAlchemy ORM for business data (MCP configs, user data, etc.)
- **Agno PostgresDb:** Agno's native PostgreSQL storage for agent sessions
  - Created via `create_postgres_db()` or `create_mcp_postgres_db()`
  - Uses schema-qualified table names (e.g., `mcp.agent_sessions`)

### Custom Role Mapping Pattern (Supervisor Workflow)
The supervisor-agent workflow uses a custom `role_map` to ensure OpenAI API compatibility:
```python
supervisor_role_map = {
    "system": "system",
    "user": "user",
    "assistant": "system",  # Supervisor reasoning stored as system
    "tool": "tool",
    "model": "system",      # Model responses also stored as system
}
```
This maps assistant/model outputs to `system` role when storing to PostgresDb, since the `assistant` role was only added in later OpenAI API versions. This ensures compatibility with all OpenAI API versions when loading conversation history.

### Document Processing
Document readers are provided by agno-ai dependencies:
- PDF: `PyPDF2` (via agno.knowledge.reader.pdf_reader.PDFReader)
- DOCX: `python-docx`
- PPTX: `python-pptx` (via agno.knowledge.reader.pptx_reader.PPTXReader)
- CSV/Excel: `pandas` + `openpyxl` (via agno.knowledge.reader.csv_reader.CSVReader)

**Semantic Chunking:** Uses `chonkie>=1.5.0` for advanced knowledge base chunking (agno.knowledge.chunking.semantic.SemanticChunking)

### Embeddings & Search
- **Embeddings:** `sentence-transformers` (used by agno-ai)
- **Search Tools:** Custom implementations in [search_tools.py](app/agno/tools/search_tools.py)

### Permission System (`app/middleware/permission/`, `app/middleware/member_permission.py`)
- **Declarative Permission Decorators:**
  - `@require_privilege(privilege_type)` - Checks if user has a specific feature privilege
  - `@require_quota(quota_type, consume=n)` - Checks if user has sufficient quota
- **Admin Bypass:** All permission decorators automatically skip checks for admin users (`user_type="admin"` or `role="admin"/"super_admin"`)
- **Dynamic Permissions:** Uses `business.member_packages.custom_config` JSON field for extensible permissions without code changes
- **Supported Privileges:** `rag`, `web_search`, `mcp_tools`, and any `enable_xxx` field from packages table
- **Supported Quotas:** `daily_chats`, `kb_count`, `kb_documents`, `file_storage_mb`, `file_count`

### Scheduled Tasks (`scripts/run_tasks.py`)
Distribution system scheduled tasks run hourly (configurable via crontab):
```bash
# Manual execution
python scripts/run_tasks.py settle    # Settle pending commissions
python scripts/run_tasks.py upgrade   # Upgrade distributor levels
python scripts/run_tasks.py all       # Run all tasks

# Crontab configuration (hourly)
0 * * * * cd /path/to/Shuiwu_backend && python scripts/run_tasks.py all >> logs/tasks.log 2>&1
```

## Startup Sequence

On application startup ([app/main.py](app/main.py:5-236)):

**Synchronous (blocking):**
1. TensorFlow optimizations disabled via environment variables
2. sentence-transformers modules blocked to prevent 60+ second startup delays
3. MCP database initialization

**Asynchronous (non-blocking background tasks):**
1. Business database initialization ([business_db](app/infra/business_db.py))
2. MCP services loading ([mcp_service_manager](app/services/mcp/mcp_service.py))
3. Model configuration caching ([model_cache](app/services/models/model_cache.py))
4. WeChat Pay configuration loading
5. System knowledge base cache loading
6. **Scheduled tasks** (runs hourly):
   - Settlement of pending commissions
   - Distributor level upgrades

On shutdown:
1. All MCP service connections are closed

**Environment Variables Set at Startup:**
- `TF_ENABLE_ONEDNN_OPTS=0` - Disables TensorFlow oneDNN optimizations
- `TRANSFORMERS_NO_TF=1` - Forces PyTorch backend for sentence-transformers
- `USE_TF=0` - Disables TensorFlow usage
- `PYDANTIC_DISABLE_WARNINGS=1` - Suppresses Pydantic warnings

**Module Blocking for Performance:**
The following modules are blocked via `sys.modules` to avoid startup delays:
- `sentence_transformers`
- `sentence_transformers.cross_encoder`
- `sentence_transformers.losses`

## Code Conventions

- **Chinese Comments:** Codebase uses Chinese comments extensively
- **Environment Variables:** Database config via `os.getenv()` with defaults
- **Error Handling:** HTTP exceptions with detailed error messages
- **Placeholder Files:** Many files are 0-byte placeholders indicating ongoing development

## Development Notes

- No formal test suite or CI/CD configuration exists
- No linting/formatting tools configured (no ruff, black, flake8, etc.)
- The codebase is under active development (branch: `feature/ycc`)
- MCP integration is the most mature component

### Utility Scripts (`scripts/`)
- **`run_tasks.py`** - Scheduled tasks for distribution system (commission settlement, level upgrades)
- **`setup_admin_role.py`** - Initialize admin roles in the database
- **`batch_upload_tax_documents.py`** - Batch upload tax documents to knowledge base
- **`import_tax_qa_to_kb.py`** - Import tax Q&A data to knowledge base
- **`import_guardrails_to_kb.py`** - Import guardrails/rail fence content
- **`batch_upload_policy_docs.py`** - Batch upload policy documents
- **`cleanup_kb_indexes.py`** - Clean up knowledge base indexes

### Database Migrations (`app/infra/sql/migrations/`)
Schema migrations are versioned SQL files:
- `001_add_password_hash.sql` - Add password hashing support
- `002_add_is_system_to_knowledge_base_registry.sql` - Flag system knowledge bases
- `003_create_file_manager_schema.sql` - File management tables
- `004_create_tax_declaration_system.sql` - Tax declaration tables
- `005_create_business_declaration_system.sql` - Business declaration tables
- `006_add_member_packages_extensions.sql` - Membership package extensions

### Key Documentation (`docs/`)
- **[permission-decorators-guide.md](docs/permission-decorators-guide.md)** - Permission decorator usage
- **[member-permission-system.md](docs/member-permission-system.md)** - Member permission system
- **[tax_scope_guardrails.md](docs/tax_scope_guardrails.md)** - Product scope boundaries (100+ Q&A pairs)
- **[DISTRIBUTION_README.md](docs/DISTRIBUTION_README.md)** - Distribution/affiliate system
- **[admin-system.md](docs/admin-system.md)** - Admin system documentation
- **[wechat-miniprogram-integration.md](docs/wechat-miniprogram-integration.md)** - WeChat integration guide
- **[wechat-pay-integration-summary.md](docs/wechat-pay-integration-summary.md)** - WeChat Pay integration
- **[order-system-design.md](docs/order-system-design.md)** - Order system architecture

### Key Features

1. **AI Agent System**: Multiple agent types (normal chat, RAG, search, full, contract review, knowledge selector) + Supervisor-Agent workflow
2. **Knowledge Base**: Document upload, processing, and semantic search with pgvector
3. **MCP Integration**: Extensible tool system for AI agents with service registry pattern
4. **WeChat Integration**: Mini-program integration with WeChat Pay support
5. **Multi-format Document Support**: PDF, DOCX, PPTX, CSV/Excel with semantic chunking
6. **Authentication System**: JWT-based auth with registration/login via WeChat OAuth
7. **Member Subscriptions**: Multi-tier VIP system (Free, VIP, Premium, Enterprise) with dynamic permissions
8. **Distribution System**: Referral/affiliate program with commission tracking and scheduled settlements
9. **Tax Services**: Individual tax declaration and business registration/filing
10. **Enterprise Analytics**: Business health reports and risk assessment
11. **Observability**: Langfuse integration for monitoring and tracing
12. **File Management**: Cloud storage (Alibaba OSS) support
13. **Feedback System**: User feedback submission with admin moderation workflows
14. **Permission System**: Declarative permission decorators with admin bypass and dynamic configuration
15. **Product Scope Guardrails**: Tax-focused boundary enforcement with 100+ predefined refusal responses

## Additional Services

- **GPTZero:** AI content detection API integration
- **Langfuse:** Observability and tracing platform
- **SSE Support:** Streaming responses via `sse-starlette`
- **WeChat Pay:** Native payment integration with order management
- **Baidu/DuckDuckGo Search:** Web search capabilities for agents
- **Enterprise Services:** Business risk queries, company information lookup
- **Alibaba Cloud OSS:** File storage for documents and user uploads
