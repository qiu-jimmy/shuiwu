from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkingPolicy:
    name: str
    target_size: int
    overlap: int
    strategy: str


POLICIES = {
    "tax_policy": ChunkingPolicy("tax_policy", target_size=1200, overlap=120, strategy="article"),
    "guide": ChunkingPolicy("guide", target_size=1600, overlap=160, strategy="steps"),
    "case": ChunkingPolicy("case", target_size=1800, overlap=180, strategy="case_sections"),
    "contract": ChunkingPolicy("contract", target_size=1000, overlap=100, strategy="clauses"),
    "spreadsheet": ChunkingPolicy("spreadsheet", target_size=2000, overlap=0, strategy="table_blocks"),
}


def choose_policy(file_name: str, document_type: str | None = None) -> ChunkingPolicy:
    if document_type and document_type in POLICIES:
        return POLICIES[document_type]
    lowered = file_name.lower()
    if "合同" in file_name:
        return POLICIES["contract"]
    if lowered.endswith((".xlsx", ".xls", ".csv")):
        return POLICIES["spreadsheet"]
    return POLICIES["tax_policy"]
