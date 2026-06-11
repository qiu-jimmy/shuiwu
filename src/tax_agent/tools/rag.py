import asyncio

from tax_agent.rag.retriever import HybridRetriever
from tax_agent.schemas import AgentContext
from tax_agent.tools.decorators import compatible_tool


def make_rag_tool(context: AgentContext):
    retriever = HybridRetriever()

    @compatible_tool
    def rag_search(query: str, kb_name: str | None = None) -> str:
        """Search tax knowledge bases and return evidence snippets."""
        pack = asyncio.run(
            retriever.retrieve(
                query=query,
                user_id=context.user_id,
                preferred_kb=kb_name or context.knowledge_base,
            )
        )
        lines = []
        for idx, evidence in enumerate(pack.evidences, start=1):
            lines.append(
                f"{idx}. 来源：{evidence.kb_name}/{evidence.file_name or '未知文件'}\n"
                f"位置：{evidence.section_path or evidence.chunk_id or '未知位置'}\n"
                f"内容：{evidence.content}"
            )
        if pack.warnings:
            lines.append("提示：" + "；".join(pack.warnings))
        return "\n\n".join(lines) if lines else "未检索到相关证据。"

    return rag_search
