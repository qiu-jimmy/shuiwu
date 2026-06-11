"""
企业体检报告生成器 - 使用 Agno AI 生成企业体检报告
"""
import asyncio
from pathlib import Path
from typing import Dict
from agno.agent import Agent
from agno.models.deepseek import DeepSeek
from agno.team import Team


class QuoteGenerator:
    """企业体检报告生成器"""
    
    def __init__(self, api_key: str):
        """初始化生成器"""
        self.api_key = api_key
        self.model = DeepSeek(id="deepseek-chat", api_key=api_key)
        
        # 创建各个专门的agent
        self._create_agents()
        
        # 创建Team来协调所有agent
        self.team = Team(
            model=self.model,
            members=[
                self.overview_agent,
                self.hardware_agent,
                self.functions_agent,
                self.performance_agent,
                self.indicators_agent,
                self.solution_agent,
                self.timeline_agent,
                self.deliverables_agent,
                self.payment_agent,
                self.conclusion_agent,
                self.cost_agent,
            ],
            name="企业体检报告生成团队"
        )
    
    def _create_agents(self):
        """创建各个专门的agent"""
        # 企业体检概览 agent
        self.overview_agent = Agent(
            name="企业体检概览生成器",
            model=self.model,
            markdown=True,
            instructions=(
                "你是一名资深企业管理咨询顾问，擅长从企业基础信息、业务数据和运营材料中，"
                "提炼出清晰的企业体检总体概述。"
            )
        )
        
        # 企业基本信息与业务概况 agent
        self.hardware_agent = Agent(
            name="企业信息分析生成器",
            model=self.model,
            markdown=True,
            instructions=(
                "你是一名企业管理与运营分析专家，擅长基于企业登记信息、股权结构、业务模式等，"
                "梳理企业基本情况和关键业务特征。"
            )
        )
        
        # 重点事项/风险点列表 agent
        self.functions_agent = Agent(
            name="重点事项与风险点生成器",
            model=self.model,
            markdown=True,
            instructions=(
                "你是一名企业风险识别专家，擅长从材料中抽取重点事项和潜在风险点，"
                "并用结构化方式进行归类和说明。"
            )
        )
        
        # 评估标准与规范要求 agent
        self.performance_agent = Agent(
            name="评估标准生成器",
            model=self.model,
            markdown=True,
            instructions=(
                "你是一名企业管理与评估标准专家，熟悉各类企业运营相关的评估要求、管理规范和最佳实践，"
                "能够将其整理为清晰的评估指标。"
            )
        )
        
        # 具体评估指标与核查要点 agent
        self.indicators_agent = Agent(
            name="评估指标生成器",
            model=self.model,
            markdown=True,
            instructions=(
                "你是一名企业内控与评估专家，擅长将抽象的评估要求细化为可检查的指标、"
                "核查要点和证据指引。"
            )
        )
        
        # 综合分析与改进建议 agent
        self.solution_agent = Agent(
            name="企业分析与建议生成器",
            model=self.model,
            markdown=True,
            instructions=(
                "你是一名资深企业管理咨询顾问，擅长撰写企业运营分析及改进建议，"
                "能够提出优化空间和管理提升建议。"
            )
        )
        
        # 改进计划与持续管理 agent
        self.timeline_agent = Agent(
            name="改进计划生成器",
            model=self.model,
            markdown=True,
            instructions=(
                "你是一名项目管理与企业改进推进专家，擅长将改进动作和持续管理工作，"
                "拆解为阶段性计划和时间安排。"
            )
        )
        
        # 报告附件与支撑材料清单 agent
        self.deliverables_agent = Agent(
            name="报告附件清单生成器",
            model=self.model,
            markdown=True,
            instructions=(
                "你是一名企业管理报告与文档专家，擅长整理企业体检或评估所需的附件清单、"
                "佐证材料和留存文档列表。"
            )
        )
        
        # 风险提示与合作条款 agent
        self.payment_agent = Agent(
            name="风险提示与合作条款生成器",
            model=self.model,
            markdown=True,
            instructions=(
                "你是一名企业管理服务条款设计专家，擅长用正式而清晰的语言，"
                "说明服务边界、责任划分与重要风险提示。"
            )
        )
        
        # 报告结论与总体评价 agent
        self.conclusion_agent = Agent(
            name="报告结论生成器",
            model=self.model,
            markdown=True,
            instructions=(
                "你是一名资深企业管理顾问，擅长撰写企业体检报告的总体结论和专业意见，"
                "语言正式、客观且易于企业管理层理解。"
            )
        )
        
        # 重要事项与改进优先级明细 agent
        self.cost_agent = Agent(
            name="重点事项清单生成器",
            model=self.model,
            markdown=True,
            instructions=(
                "你是一名企业项目管理专家，擅长把多个改进任务、核查事项和后续跟进工作，"
                "整理成结构化清单，并标注优先级与负责角色。"
            )
        )
    
    async def read_requirement_file(self, file_path: str) -> str:
        """读取需求文件内容"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 检查是否是.doc格式（旧格式，不支持）
        if path.suffix.lower() == '.doc':
            raise ValueError(f"不支持旧格式的.doc文件，请将文件转换为.docx格式。\n"
                           f"方法：在Word中打开文件，选择'另存为'，格式选择'Word文档(*.docx)'")
        
        # 支持多种文件格式
        if path.suffix.lower() == '.txt':
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
            except UnicodeDecodeError:
                # 尝试其他编码
                with open(path, 'r', encoding='gbk') as f:
                    return f.read()
        elif path.suffix.lower() == '.docx':
            try:
                from docx import Document
                import zipfile
                
                # 使用绝对路径，避免路径问题
                abs_path = str(path.resolve())
                
                # 先验证文件是否是有效的zip文件（docx本质上是zip）
                try:
                    with zipfile.ZipFile(abs_path, 'r') as zip_ref:
                        # 检查是否包含必要的docx文件结构
                        file_list = zip_ref.namelist()
                        if 'word/document.xml' not in file_list:
                            raise ValueError("文件不是有效的.docx格式（缺少word/document.xml）")
                except zipfile.BadZipFile:
                    raise ValueError(f"文件不是有效的.docx格式。\n"
                                   f"可能的原因：\n"
                                   f"1. 文件是旧格式的.doc文件（需要转换为.docx）\n"
                                   f"2. 文件已损坏\n"
                                   f"3. 文件不是Word文档")
                
                # 读取文档内容
                doc = Document(abs_path)
                text_content = '\n'.join([para.text for para in doc.paragraphs])
                if not text_content.strip():
                    raise ValueError("Word文档内容为空，请确认文档中有文字内容")
                return text_content
            except ImportError:
                raise ImportError("需要安装python-docx库来读取Word文档。请运行: pip install python-docx")
            except ValueError as e:
                # 重新抛出ValueError
                raise
            except Exception as e:
                error_msg = str(e)
                if "not a zip file" in error_msg.lower() or "bad zipfile" in error_msg.lower():
                    raise ValueError(f"Word文档格式错误或文件已损坏: {file_path}\n"
                                   f"可能的原因：\n"
                                   f"1. 文件是旧格式的.doc文件（需要转换为.docx）\n"
                                   f"2. 文件已损坏\n"
                                   f"3. 文件不是Word文档\n"
                                   f"错误详情: {error_msg}")
                else:
                    raise ValueError(f"读取Word文档失败: {error_msg}")
        elif path.suffix.lower() == '.pdf':
            try:
                import PyPDF2
                with open(path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text_content = '\n'.join([page.extract_text() for page in reader.pages])
                    if not text_content.strip():
                        raise ValueError("PDF文档内容为空或无法读取")
                    return text_content
            except ImportError:
                raise ImportError("需要安装PyPDF2库来读取PDF文档。请运行: pip install PyPDF2")
            except Exception as e:
                raise ValueError(f"读取PDF文档失败: {str(e)}")
        else:
            # 尝试作为文本文件读取
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
            except UnicodeDecodeError:
                try:
                    with open(path, 'r', encoding='gbk') as f:
                        return f.read()
                except Exception as e:
                    raise ValueError(f"无法读取文件，请确认文件格式正确。错误: {str(e)}")
            except Exception as e:
                raise ValueError(f"读取文件失败: {str(e)}")
    
    async def generate_implementation_timeline(self, requirement: str) -> list:
        """生成改进计划与持续管理"""
        prompt = f"""请根据以下材料以及潜在改进工作，生成"改进计划与持续管理"表格。

要求：
1. 按时间顺序给出若干阶段，例如：现状梳理与问题确认、改进方案设计与内部培训、系统与流程调整、效果复盘与持续监控等；
2. 预估每一阶段的持续时间（按“X周”或“X个月”表述），最后给出总预估时长；
3. 请以JSON格式返回，字段名保持不变以便程序使用，格式如下：
[
    {{"stage": "阶段名称", "content": "主要工作内容", "duration": "X周或X个月"}},
    ...
]

材料内容：
{requirement}"""
        
        response = await self.timeline_agent.arun(input=prompt)
        content = response.content.strip()
        
        import json
        import re
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        
        return []
    
    async def generate_all_content_with_titles(self, requirement: str, project_name: str, 
                                               timeline: list, total_amount: float) -> str:
        """使用 Team 生成包含完整标题和内容的 Markdown 文档（用于 Pandoc 模式）
        
        Args:
            requirement: 用户上传的材料文本
            project_name: 企业/项目名称
            timeline: 改进计划与持续管理列表
            total_amount: 保留参数（兼容旧接口）
            
        Returns:
            完整的 Markdown 文档字符串，包含所有标题和内容
        """
        # 准备各个agent的输入（要求生成包含标题的完整 Markdown）
        timeline_str = '\n'.join([f"- {t.get('stage', '')}: {t.get('content', '')} ({t.get('duration', '')})" for t in timeline])
        
        # 定义所有任务，要求每个 Agent 生成包含标题的完整 Markdown
        tasks = {
            'overview': {
                'agent': self.overview_agent,
                'input': f"""请根据以下材料，生成"一、企业体检总体概述"章节的完整内容。

要求：
1. 必须包含一级标题：使用 Markdown 格式 "# 一、企业体检总体概述"
2. 标题下方是正文内容，用专业但易理解的语言说明企业的基本情况、主要业务模式和核心特征；
3. 概括当前整体企业运营状况，包括：组织架构、业务模式、管理水平、运营效率等维度；
4. 简要提及本次体检评估聚焦的重点方向（如：管理体系、业务流程、组织效能、资源配置等）；
5. 字数约300字左右，采用 3 个自然段撰写，每个自然段之间使用一个空行分隔；
6. 正文可以使用 Markdown 格式（如段落、列表等），但保持简洁专业。

材料内容：
{requirement}

请直接输出完整的章节内容，包括标题和正文。"""
            },
            'core_functions': {
                'agent': self.functions_agent,
                'input': f"""请根据以下材料，生成"二、重点事项与评估标准"章节的完整内容。

要求：
1. 必须包含一级标题：使用 Markdown 格式 "# 二、重点事项与评估标准"
2. 包含二级标题 "## 2.1 重点事项与风险点列表"
3. 从材料中识别企业运营中的重点事项或场景（如：战略规划、组织管理、流程优化、人力资源、财务管理、信息化建设等）；
4. 对每一项给出简要描述，并指出该事项下可能出现的主要风险或问题；
5. 使用 Markdown 列表格式输出，不超过8项；
6. 格式示例：
   - **事项名称**：事项背景或业务模式简述。主要风险或需关注的管理要求：...

材料内容：
{requirement}

请直接输出完整的章节内容，包括标题和列表。"""
            },
            'performance_requirements': {
                'agent': self.performance_agent,
                'input': f"""请根据以下材料，生成"2.2 评估标准与管理指标"部分的完整内容。

要求：
1. 必须包含二级标题：使用 Markdown 格式 "## 2.2 评估标准与管理指标"
2. 结合企业管理最佳实践和行业标准，列出关键评估标准；
3. 使用 Markdown 列表格式，每项包含：评估标准名称、目标状态或标准说明、备注或适用范围；
4. 格式示例：
   - **评估标准名称**：目标状态或标准说明。备注或适用范围：...

材料内容：
{requirement}

请直接输出完整的内容，包括标题和列表。"""
            },
            'technical_indicators': {
                'agent': self.indicators_agent,
                'input': f"""请根据以下材料，生成"2.3 具体评估指标与核查要点"部分的完整内容。

要求：
1. 必须包含二级标题：使用 Markdown 格式 "## 2.3 具体评估指标与核查要点"
2. 针对重点事项，列出需要检查的具体项目和核查要点；
3. 可以使用 Markdown 表格或列表格式；
4. 每项包含：检查类别、主要检查内容、关注级别或风险评级、核查要点与建议做法；

材料内容：
{requirement}

请直接输出完整的内容，包括标题和详细说明。"""
            },
            'technical_solution': {
                'agent': self.solution_agent,
                'input': f"""请根据以下材料，生成"三、企业运营分析与改进建议"章节的完整内容。

要求：
1. 必须包含一级标题：使用 Markdown 格式 "# 三、企业运营分析与改进建议"
2. 语言正式、专业，适合作为对管理层的企业体检报告正文部分；
3. 对不同业务领域或管理场景下的问题进行分条分析，结合管理最佳实践进行评估；
4. 每类问题给出具体可执行的改进建议或管理优化建议；
5. 使用分级标题（如 ##、### 等），便于后续生成 Word 报告目录结构；
6. 可以使用 Markdown 格式（标题、段落、列表等）。

材料内容：
{requirement}

请直接输出完整的章节内容，包括标题和详细分析。"""
            },
            'timeline': {
                'agent': self.timeline_agent,
                'input': f"""请根据以下材料，生成"四、改进计划与持续管理"章节的完整内容。

要求：
1. 必须包含一级标题：使用 Markdown 格式 "# 四、改进计划与持续管理"
2. 按时间顺序给出若干阶段，例如：现状梳理与问题确认、改进方案设计与内部培训、系统与流程调整、效果复盘与持续监控等；
3. 预估每一阶段的持续时间（按"X周"或"X个月"表述），最后给出总预估时长；
4. 使用 Markdown 列表或表格格式展示；

材料内容：
{requirement}

请直接输出完整的章节内容，包括标题和计划。"""
            },
            'deliverables': {
                'agent': self.deliverables_agent,
                'input': f"""请根据以下材料，生成"五、报告附件与支撑材料"章节的完整内容。

要求：
1. 必须包含一级标题：使用 Markdown 格式 "# 五、报告附件与支撑材料"
2. 列出建议准备或留存的材料类型（如：企业证照、财务报表、制度文件、业务流程文档、组织架构图、人力资源资料等）；
3. 使用 Markdown 列表格式，每项包含材料类别和具体内容说明；

材料内容：
{requirement}

请直接输出完整的章节内容，包括标题和清单。"""
            },
            'cost_details': {
                'agent': self.cost_agent,
                'input': f"""请根据以下材料，生成"六、重点事项与改进任务清单"章节的完整内容。

要求：
1. 必须包含一级标题：使用 Markdown 格式 "# 六、重点事项与改进任务清单"
2. 将后续工作拆分为 5-8 个板块（如：资料补充与整理、重点领域自查、流程与制度优化、组织架构调整、系统配置与权限梳理、培训与宣导、持续监控与复盘等）；
3. 在每个板块下列出具体任务或核查事项；
4. 使用 Markdown 格式，包含板块标题（二级标题）和任务列表；
5. 每项任务包含：责任角色/部门、建议完成时间、优先级、具体工作内容；

材料内容：
{requirement}

改进计划与持续管理：
{timeline_str}

请直接输出完整的章节内容，包括标题和任务清单。"""
            },
            'payment_terms': {
                'agent': self.payment_agent,
                'input': f"""请根据以下材料，生成"七、重要风险提示与合作边界说明"章节的完整内容。

要求：
1. 必须包含一级标题：使用 Markdown 格式 "# 七、重要风险提示与合作边界说明"
2. 包含二级标题 "## 7.1 重要风险提示" 和 "## 7.2 合作边界与责任划分"
3. 明确本报告及相关服务的定位：为企业提供管理咨询参考意见，不构成对任何第三方的保证；
4. 说明信息来源及企业自行披露材料的局限性，提示可能存在的遗漏或偏差风险；
5. 可以简要说明服务方与企业在管理工作中的责任边界；
6. 使用 Markdown 格式（标题、段落、列表等）；

材料内容：
{requirement}

请直接输出完整的章节内容，包括标题和说明。"""
            },
            'conclusion': {
                'agent': self.conclusion_agent,
                'input': f"""请根据以下材料，生成"八、备注"章节的完整内容。

要求：
1. 必须包含一级标题：使用 Markdown 格式 "# 八、备注"
2. 用正式、稳健的语气对企业当前运营状态做总体评价（如：整体运营状况良好/存在一定改进空间/存在较高风险等）；
3. 概括最重要的若干改进方向或优先事项；
4. 可以适度表达后续持续服务与沟通的意愿；
5. 可以包含默认的备注条款（如：报告基于指定时间点前的资料、仅供内部使用、不构成鉴证结论等）；
6. 使用 Markdown 格式（标题、段落、列表等）；

材料内容：
{requirement}
企业/项目名称：{project_name}

请直接输出完整的章节内容，包括标题和备注。"""
            }
        }
        
        # 使用Team协调，通过asyncio.gather并行执行所有任务
        async def run_task(task_name):
            task_info = tasks[task_name]
            response = await task_info['agent'].arun(input=task_info['input'])
            return task_name, response.content.strip()
        
        # 并行执行所有任务
        all_tasks = ['overview', 'core_functions', 'performance_requirements', 'technical_indicators',
                     'technical_solution', 'timeline', 'deliverables', 'cost_details', 'payment_terms', 'conclusion']
        results = await asyncio.gather(*[run_task(task) for task in all_tasks])
        
        # 按顺序拼接所有章节
        content_dict = {task_name: content for task_name, content in results}
        
        # 构建完整的 Markdown 文档
        markdown_parts = []
        
        # 添加文档标题
        markdown_parts.append(f"# {project_name}企业体检报告\n")
        
        # 按顺序添加各个章节
        markdown_parts.append(content_dict.get('overview', ''))
        markdown_parts.append('\n\n')
        markdown_parts.append(content_dict.get('core_functions', ''))
        markdown_parts.append('\n\n')
        markdown_parts.append(content_dict.get('performance_requirements', ''))
        markdown_parts.append('\n\n')
        markdown_parts.append(content_dict.get('technical_indicators', ''))
        markdown_parts.append('\n\n')
        markdown_parts.append(content_dict.get('technical_solution', ''))
        markdown_parts.append('\n\n')
        markdown_parts.append(content_dict.get('timeline', ''))
        markdown_parts.append('\n\n')
        markdown_parts.append(content_dict.get('deliverables', ''))
        markdown_parts.append('\n\n')
        markdown_parts.append(content_dict.get('cost_details', ''))
        markdown_parts.append('\n\n')
        markdown_parts.append(content_dict.get('payment_terms', ''))
        markdown_parts.append('\n\n')
        markdown_parts.append(content_dict.get('conclusion', ''))
        
        # 添加公司署名
        markdown_parts.append('\n\n---\n\n')
        markdown_parts.append('<div align="right">杭州烛龙智元科技有限公司</div>')
        
        return '\n'.join(markdown_parts)
    

