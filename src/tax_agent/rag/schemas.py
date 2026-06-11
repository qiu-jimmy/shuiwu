from pydantic import BaseModel, Field


class KnowledgeBaseCandidate(BaseModel):
    kb_name: str
    kb_type: str = "system"
    score: float = 0.0
    reason: str = ""


class EvidenceChunk(BaseModel):
    content: str
    kb_name: str
    file_name: str | None = None
    chunk_id: str | None = None
    section_path: str | None = None
    page_number: int | None = None
    policy_doc_no: str | None = None
    effective_date: str | None = None
    expiry_date: str | None = None
    score: float = 0.0
    metadata: dict = Field(default_factory=dict)


class EvidencePack(BaseModel):
    query: str
    evidences: list[EvidenceChunk] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
