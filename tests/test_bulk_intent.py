import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# 将 src 目录加入环境变量，以便于导入
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from langchain_core.messages import HumanMessage
from tax_agent.workflow.nodes.intent_router import analyze_intent_node

def process_question(item):
    question = item["question"]
    expected = item["expected"]
    index = item["index"]
    total = item["total"]
    
    state = {"messages": [HumanMessage(content=question)]}
    try:
        # LLM 调用默认应该有超时机制，不过为了保险，这里只捕获异常
        result = analyze_intent_node(state)
        actual = result.get("intent")
        
        if actual == expected:
            return True, index, question, expected, actual, ""
        else:
            return False, index, question, expected, actual, f"❌ 失败 | 问题: {question} | 预期: {expected} | 实际: {actual}"
    except Exception as e:
        return False, index, question, expected, "ERROR", f"⚠️ 异常 | 问题: {question} | 预期: {expected} | 错误: {e}"

def run_evaluation():
    file_path = os.path.join(os.path.dirname(__file__), "test_data_v2.md")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Parse markdown table
    questions = []
    idx = 1
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("|") and not line.startswith("| 序号") and not line.startswith("|---"):
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4:
                question = parts[2]
                expected_intent = parts[3].replace("`", "")
                if question and expected_intent:
                    questions.append({"question": question, "expected": expected_intent, "index": idx})
                    idx += 1

    total = len(questions)
    for q in questions:
        q["total"] = total

    print(f"总计加载测试问题数: {total}")
    
    correct_count = 0
    print("开始多线程并发测试...")
    
    # 限制并发数以避免触发限流
    max_workers = 10
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_question, q): q for q in questions}
        
        completed = 0
        for future in as_completed(futures):
            success, index, question, expected, actual, msg = future.result()
            completed += 1
            if success:
                correct_count += 1
            else:
                print(f"[{completed}/{total}] {msg}")
            
            if completed % 20 == 0:
                print(f"进度: {completed}/{total} 已完成...")

    print("="*50)
    print("评估完成!")
    print(f"总测试数: {total}")
    print(f"正确识别: {correct_count}")
    accuracy = (correct_count / total) * 100 if total > 0 else 0
    print(f"准确率: {accuracy:.2f}%")

if __name__ == "__main__":
    run_evaluation()
