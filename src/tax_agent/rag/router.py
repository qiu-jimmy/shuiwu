from tax_agent.rag.schemas import KnowledgeBaseCandidate


class KnowledgeRouter:
    """Selects candidate knowledge bases. Current implementation is a scaffold."""

    def route(self, query: str, user_id: str, preferred_kb: str | None = None) -> list[KnowledgeBaseCandidate]:
        if preferred_kb:
            return [
                KnowledgeBaseCandidate(
                    kb_name=preferred_kb,
                    kb_type="user_or_system",
                    score=1.0,
                    reason="user preferred knowledge base",
                )
            ]

        candidates: list[KnowledgeBaseCandidate] = []
        if any(k in query for k in ["发票", "专票", "普票", "抵扣", "红字"]):
            candidates.append(KnowledgeBaseCandidate(kb_name="发票管理知识库", score=0.92))
        if any(k in query for k in ["增值税", "小规模", "一般纳税人", "销项", "进项"]):
            candidates.append(KnowledgeBaseCandidate(kb_name="增值税知识库", score=0.9))
        if any(k in query for k in ["个税", "个人所得税", "专项附加", "年终奖"]):
            candidates.append(KnowledgeBaseCandidate(kb_name="个人所得税知识库", score=0.9))
        if any(k in query for k in ["企业所得税", "税前扣除", "汇算清缴", "研发费用"]):
            candidates.append(KnowledgeBaseCandidate(kb_name="企业所得税知识库", score=0.9))
        if any(k in query for k in ["风险", "稽查", "异常", "公转私", "私户"]):
            candidates.append(KnowledgeBaseCandidate(kb_name="税务风险规则库", score=0.88))

        if not candidates:
            candidates.append(KnowledgeBaseCandidate(kb_name="政策税务法规", score=0.6))

        return sorted(candidates, key=lambda item: item.score, reverse=True)[:3]
