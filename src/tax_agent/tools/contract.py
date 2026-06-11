from tax_agent.tools.decorators import compatible_tool


@compatible_tool
def contract_clause_check(text: str) -> str:
    """Check contract clauses for tax, invoice, payment, acceptance, and liability risks."""
    return f"Mock contract clause risk analysis: {text[:200]}"
