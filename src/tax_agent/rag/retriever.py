from tax_agent.config import get_settings
from tax_agent.rag.router import KnowledgeRouter
from tax_agent.rag.schemas import EvidenceChunk, EvidencePack


class HybridRetriever:
    """Scaffold retriever. Replace mock retrieval with PgVector + rerank in P2/P3."""

    def __init__(self, router: KnowledgeRouter | None = None) -> None:
        self.settings = get_settings()
        self.router = router or KnowledgeRouter()

    async def retrieve(
        self,
        query: str,
        user_id: str,
        preferred_kb: str | None = None,
        top_k: int = 6,
    ) -> EvidencePack:
        candidates = self.router.route(query=query, user_id=user_id, preferred_kb=preferred_kb)
        if not self.settings.enable_real_rag:
            evidences = [
                EvidenceChunk(
                    content=f"Mock evidence for query '{query}' from {candidate.kb_name}.",
                    kb_name=candidate.kb_name,
                    file_name="mock_policy.md",
                    chunk_id=f"mock-{idx}",
                    section_path="示例章节",
                    score=candidate.score,
                )
                for idx, candidate in enumerate(candidates[:top_k], start=1)
            ]
            return EvidencePack(query=query, evidences=evidences, warnings=["当前为 mock RAG。"])

        raise NotImplementedError("Real PgVector retrieval will be implemented in migration phase P2.")
