import os
import sys

# 将 src 目录加入环境变量，以便于导入
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from langchain_core.messages import HumanMessage
from tax_agent.workflow.state import TaxAgentState
from tax_agent.workflow.nodes.query_rewriter import rewrite_query_node

def test_rewriter():
    queries = [
        "公司没赚钱还要不要报税？",
        "个体户的个人所得税怎么计算？",
        "2026年小规模几个点？",
        "我想退税要怎么弄",
        "研发费用加计扣除是不是分行业",
        "发票不小心撕了怎么办"
    ]
    
    print("==================================================")
    print("开始测试查询重写器 (Query Rewriter)")
    print("==================================================\n")
    
    for query in queries:
        print(f"👤 用户原始提问: {query}")
        
        # 组装 State
        state = {"messages": [HumanMessage(content=query)]}
        
        try:
            # 执行节点
            result = rewrite_query_node(state)
            search_query = result.get("search_query")
            print(f"🔎 提炼改写结果: \033[96m{search_query}\033[0m")
        except Exception as e:
            print(f"❌ 发生异常: {e}")
            
        print("-" * 50)

if __name__ == "__main__":
    test_rewriter()
