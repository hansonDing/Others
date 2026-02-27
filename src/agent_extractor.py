"""
Agent 1: 字段提取专家
从大量表字段信息中提取与用户问题相关的字段
"""
import json
from typing import List, Dict, Any

from .models import TableInfo, ExtractedFields
from .config import get_config


class FieldExtractorAgent:
    """
    字段提取 Agent
    
    职责：
    1. 分析用户问题的意图
    2. 从检索到的多表完整信息中提取相关字段
    3. 识别表之间的关系
    4. 提供字段选择理由
    """
    
    def __init__(self):
        self.config = get_config()
    
    def _build_system_prompt(self) -> str:
        """构建系统 Prompt"""
        return """你是一个专业的数据库字段提取专家。你的任务是从大量的表字段信息中，精准提取与用户问题相关的字段。

## 核心职责
1. 深入理解用户问题的真实意图
2. 从提供的表信息中筛选出查询所需的关键字段
3. 识别表之间的关联关系（JOIN 条件）
4. 提供清晰的字段选择理由

## 输出格式
你必须以 JSON 格式输出，结构如下：
{
  "tables": [
    {
      "table_name": "表名",
      "selected_columns": ["字段1", "字段2"],
      "reason": "选择这些字段的具体理由",
      "join_hints": ["与其他表的 JOIN 建议"],
      "filter_hints": ["可能的过滤条件建议"]
    }
  ],
  "overall_analysis": "对用户问题的整体分析"
}

## 字段选择原则
1. **必要性原则**：只选择回答问题所必需的字段
2. **完整性原则**：确保查询所需的字段不遗漏
3. **关联性原则**：如果涉及多表，必须包含关联字段
4. **展示字段**：包含用于展示给用户看的字段（如名称、描述等）

## 示例
用户问题："查询最近一周下单金额超过1000的用户"
表信息：orders(订单表), users(用户表)

输出：
{
  "tables": [
    {
      "table_name": "orders",
      "selected_columns": ["order_id", "user_id", "amount", "created_at"],
      "reason": "需要 user_id 关联用户，amount 判断金额，created_at 判断时间",
      "join_hints": ["orders.user_id = users.user_id"],
      "filter_hints": ["created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)", "amount > 1000"]
    },
    {
      "table_name": "users",
      "selected_columns": ["user_id", "username", "email"],
      "reason": "需要用户信息展示，user_id 用于关联",
      "join_hints": [],
      "filter_hints": []
    }
  ],
  "overall_analysis": "用户想查询最近一周的高价值订单用户，需要关联 orders 和 users 表"
}

## 重要提示
- 只输出 JSON，不要输出其他内容
- 确保 JSON 格式正确，可以被解析
- 字段名必须与提供的表信息中的字段名完全一致
"""
    
    def _build_user_prompt(self, user_question: str, tables_info_text: str) -> str:
        """构建用户 Prompt"""
        return f"""用户问题：{user_question}

以下是检索到的相关表的完整信息：

{tables_info_text}

请分析用户问题，提取相关字段，并以 JSON 格式输出结果。
"""
    
    def extract_fields(
        self,
        user_question: str,
        table_infos: List[TableInfo]
    ) -> List[ExtractedFields]:
        """
        提取相关字段
        
        Args:
            user_question: 用户问题
            table_infos: 检索到的表信息列表
            
        Returns:
            提取的字段信息列表
        """
        # 构建表信息文本
        tables_info_text = "\n\n".join([
            f"【表 {i+1}】\n{table.full_info_text}"
            for i, table in enumerate(table_infos)
        ])
        
        # 构建 Prompt
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(user_question, tables_info_text)
        
        # 调用 LLM
        # 这里使用简单的模拟实现，实际使用时替换为真实的 LLM 调用
        response = self._call_llm(system_prompt, user_prompt, table_infos)
        
        # 解析结果
        try:
            result = json.loads(response)
            extracted_fields = []
            
            for table_data in result.get("tables", []):
                extracted = ExtractedFields(
                    table_name=table_data["table_name"],
                    selected_columns=table_data["selected_columns"],
                    reason=table_data["reason"],
                    join_hints=table_data.get("join_hints", []),
                    filter_hints=table_data.get("filter_hints", [])
                )
                extracted_fields.append(extracted)
            
            return extracted_fields
            
        except json.JSONDecodeError as e:
            print(f"解析 Agent 1 输出失败: {e}")
            print(f"原始输出: {response}")
            # 返回空列表或基于启发式的默认提取
            return self._fallback_extraction(user_question, table_infos)
    
    def _call_llm(self, system_prompt: str, user_prompt: str, table_infos: List[TableInfo]) -> str:
        """
        调用大模型
        
        实际使用时，这里应该调用真实的 LLM API
        如 OpenAI, Kimi, Claude 等
        """
        # TODO: 实现真实的 LLM 调用
        # 这里返回一个模拟的响应用于测试
        
        # 模拟响应示例
        mock_response = {
            "tables": [
                {
                    "table_name": table.name,
                    "selected_columns": [col.name for col in table.columns[:5]],  # 简化：取前5个字段
                    "reason": f"根据问题选择了相关字段",
                    "join_hints": [],
                    "filter_hints": []
                }
                for table in table_infos[:2]  # 简化：最多处理2个表
            ],
            "overall_analysis": f"用户查询意图分析..."
        }
        
        return json.dumps(mock_response, ensure_ascii=False)
    
    def _fallback_extraction(
        self,
        user_question: str,
        table_infos: List[TableInfo]
    ) -> List[ExtractedFields]:
        """
        备用提取策略（当 LLM 调用失败时使用）
        
        基于关键词匹配的简单启发式方法
        """
        extracted_fields = []
        
        # 简单的关键词匹配
        keywords = user_question.lower().split()
        
        for table in table_infos:
            selected_columns = []
            
            for col in table.columns:
                col_name_lower = col.name.lower()
                col_comment_lower = col.comment.lower()
                
                # 如果字段名或注释包含问题中的关键词
                for keyword in keywords:
                    if len(keyword) > 2 and (keyword in col_name_lower or keyword in col_comment_lower):
                        selected_columns.append(col.name)
                        break
            
            # 如果没有匹配到，选择主键和少量字段
            if not selected_columns:
                selected_columns = [col.name for col in table.columns if col.is_primary_key]
                if not selected_columns:
                    selected_columns = [table.columns[0].name] if table.columns else []
            
            # 去重并保持顺序
            seen = set()
            unique_columns = []
            for col in selected_columns:
                if col not in seen:
                    seen.add(col)
                    unique_columns.append(col)
            
            extracted = ExtractedFields(
                table_name=table.name,
                selected_columns=unique_columns[:10],  # 限制字段数量
                reason="基于关键词匹配的备用提取策略",
                join_hints=[],
                filter_hints=[]
            )
            extracted_fields.append(extracted)
        
        return extracted_fields
    
    def format_extracted_info(self, extracted_fields: List[ExtractedFields]) -> str:
        """
        将提取的字段信息格式化为文本（用于传递给 Agent 2）
        
        Args:
            extracted_fields: 提取的字段信息列表
            
        Returns:
            格式化后的文本
        """
        lines = []
        
        for ef in extracted_fields:
            lines.append(f"表名: {ef.table_name}")
            lines.append(f"相关字段: {', '.join(ef.selected_columns)}")
            lines.append(f"选择理由: {ef.reason}")
            
            if ef.join_hints:
                lines.append(f"JOIN 建议: {'; '.join(ef.join_hints)}")
            
            if ef.filter_hints:
                lines.append(f"过滤建议: {'; '.join(ef.filter_hints)}")
            
            lines.append("")
        
        return "\n".join(lines)


# 导入 table_infos 用于类型提示
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass
