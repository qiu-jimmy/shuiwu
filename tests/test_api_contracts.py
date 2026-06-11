from tax_agent.schemas import ChatRequest, ContractReviewRequest


def test_chat_request_legacy_fields():
    request = ChatRequest(
        user_id="user_1",
        session_id="session_1",
        message="小规模纳税人现在有什么优惠？",
        enable_rag=True,
        enable_search=True,
    )
    assert request.user_id == "user_1"
    assert request.enable_rag is True
    assert request.model_id == "qwen-flash"


def test_contract_request_defaults():
    request = ContractReviewRequest(user_id="user_1")
    assert request.model_id == "qwen-plus"
    assert "审查" in (request.message or "")
