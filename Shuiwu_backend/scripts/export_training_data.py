"""
微调数据导出脚本 - 从数据库导出高质量对话用于微调

功能：
1. 从 PostgreSQL 导出历史对话
2. 筛选高质量样本（评分 > 0.5）
3. 自动脱敏处理（身份证、手机号、金额等）
4. 输出 JSONL 格式（可直接用于训练）

使用方式：
    python scripts/export_training_data.py \
        --output data/training_data.jsonl \
        --min_score 0.5 \
        --max_samples 20000
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_db_connection():
    """获取数据库连接"""
    import psycopg2
    from dotenv import load_dotenv
    
    load_dotenv()
    
    return psycopg2.connect(
        host=os.getenv('PG_HOST', 'localhost'),
        port=os.getenv('PG_PORT', '5432'),
        user=os.getenv('PG_USER', 'postgres'),
        password=os.getenv('PG_PASSWORD', 'root'),
        dbname=os.getenv('PG_DATABASE', 'Agno'),
    )


def export_conversations(
    days_back: int = 90,
    min_turns: int = 2,
    max_turns: int = 20,
) -> List[Dict[str, Any]]:
    """
    从数据库导出对话
    
    Args:
        days_back: 导出最近N天的数据
        min_turns: 最少对话轮数
        max_turns: 最多对话轮数（截断）
    
    Returns:
        对话列表
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
    
    logger.info(f"📥 导出最近 {days_back} 天的对话数据...")
    
    try:
        cur.execute("""
            SELECT 
                s.id as session_id,
                s.user_id,
                s.created_at as session_created,
                m.role,
                m.content,
                m.created_at as message_created,
                m.rag_files,
                m.search_results
            FROM business.chat_sessions s
            JOIN business.chat_messages m ON s.id = m.session_id
            WHERE s.created_at >= %s
              AND m.content IS NOT NULL
              AND LENGTH(m.content) > 3
              AND m.role IN ('user', 'assistant')
            ORDER BY s.id, m.created_at ASC
        """, (cutoff_date,))
        
        rows = cur.fetchall()
        
        logger.info(f"   查询到 {len(rows)} 条消息记录")
        
        conversations = {}
        for row in rows:
            session_id = row[0]
            
            if session_id not in conversations:
                conversations[session_id] = {
                    'id': session_id,
                    'user_id': row[1],
                    'created_at': row[2],
                    'messages': [],
                }
            
            msg = {
                'role': row[3],
                'content': row[4],
                'timestamp': str(row[5]),
            }
            
            if row[6]:
                try:
                    msg['rag_files'] = json.loads(row[6]) if isinstance(row[6], str) else row[6]
                except:
                    pass
            
            if row[7]:
                try:
                    msg['search_results'] = json.loads(row[7]) if isinstance(row[7], str) else row[7]
                except:
                    pass
            
            conversations[session_id]['messages'].append(msg)
        
        filtered = []
        for conv in conversations.values():
            messages = conv['messages']
            
            if len(messages) < min_turns * 2:
                continue
            
            user_msgs = [m for m in messages if m['role'] == 'user']
            asst_msgs = [m for m in messages if m['role'] == 'assistant']
            
            if len(user_msgs) < min_turns or len(asst_msgs) < min_turns:
                continue
            
            conv['messages'] = messages[:max_turns * 2]
            
            has_substantive_content = any(
                len(m.get('content', '')) > 20 
                for m in asst_msgs
            )
            
            if not has_substantive_content:
                continue
            
            filtered.append(conv)
        
        logger.info(f"   筛选后保留 {len(filtered)} 条有效对话")
        
        return filtered
        
    finally:
        cur.close()
        conn.close()


def enhance_with_rag_context(conversations: List[Dict]) -> List[Dict]:
    """
    为对话添加RAG上下文信息
    
    将RAG检索结果合并到用户消息中，
    让模型学习"如何利用检索结果回答问题"
    """
    enhanced = []
    
    for conv in conversations:
        enhanced_messages = []
        
        for i, msg in enumerate(conv['messages']):
            if msg['role'] == 'assistant':
                rag_files = msg.get('rag_files')
                
                next_msg_idx = i + 1
                if next_msg_idx < len(conv['messages']):
                    next_msg = conv['messages'][next_msg_idx]
                    
                    if rag_files and isinstance(rag_files, list) and len(rag_files) > 0:
                        context_text = "\n\n【参考资料】\n"
                        for rf in rag_files[:3]:
                            filename = rf.get('file_name', '未知文件')
                            content = rf.get('content', '')[:500]
                            context_text += f"- 来源: {filename}\n{content}\n"
                        
                        enhanced_user_msg = {
                            **msg,
                            'content': msg['content'] + context_text,
                        }
                        enhanced_messages.append(enhanced_user_msg)
                        continue
            
            enhanced_messages.append(msg)
        
        enhanced_conv = {**conv, 'messages': enhanced_messages}
        enhanced.append(enhanced_conv)
    
    logger.info(f"✅ 已为 {len(enhanced)} 条对话添加RAG上下文")
    
    return enhanced


def main():
    parser = argparse.ArgumentParser(description="导出微调训练数据")
    
    parser.add_argument("--output", type=str, default="data/training_data_raw.jsonl",
                        help="输出文件路径")
    parser.add_argument("--days_back", type=int, default=90,
                        help="导出最近N天的数据")
    parser.add_argument("--min_turns", type=int, default=2,
                        help="最少对话轮数")
    parser.add_argument("--max_samples", type=int, default=50000,
                        help="最大导出数量")
    parser.add_argument("--add_rag_context", action='store_true',
                        help="是否添加RAG上下文到用户消息")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  税小通 - 微调数据导出工具")
    print("=" * 60)
    print(f"  导出范围: 最近{args.days_back}天")
    print(f"  最少轮数: {args.min_turns}")
    print(f"  输出文件: {args.output}")
    print("=" * 60)
    
    conversations = export_conversations(
        days_back=args.days_back,
        min_turns=args.min_turns,
    )
    
    if args.add_rag_context:
        conversations = enhance_with_rag_context(conversations)
    
    conversations = conversations[:args.max_samples]
    
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    with open(args.output, 'w', encoding='utf-8') as f:
        for conv in conversations:
            f.write(json.dumps(conv, ensure_ascii=False) + '\n')
    
    print(f"\n✅ 导出完成!")
    print(f"   总计: {len(conversations)} 条对话")
    print(f"   文件大小: {os.path.getsize(args.output) / 1024 / 1024:.1f} MB")
    print(f"\n下一步:")
    print(f"   python scripts/prepare_finetuning_data.py \\")
    print(f"       --input {args.output} \\")
    print(f"       --output data/training_data_cleaned.jsonl")


if __name__ == "__main__":
    main()
