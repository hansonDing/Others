"""
Agent 2: SQL 生成专家
根据提取的字段信息生成 SQL 语句
"""
import json
import re
from typing import List, Dict, Any, Optional

try:
    import sqlparse
    SQLPARSE_AVAILABLE = True
except ImportError:
    SQLPARSE_AVAILABLE = False

from .models import ExtractedFields, SQLGenerationResult
from .config import get_config


class SQLGeneratorAgent:
    """
    SQL 生成 Agent
    
    职责：
    1. 根据 Agent 1 提取的精简字段信息构建查询逻辑
    2. 选择合适的 JOIN 策略
    3. 生成符合语法的 SQL 语句
    4. 提供查询解释和执行计划说明
    """
    
    # 支持的 SQL 方言
    SUPPORTED_DIALECTS = ["mysql", "postgresql", "sqlite", "oracle", "sqlserver"]
    
    def __init__(self, dialect: str = "mysql"):
        self.config = get_config()
        self.dialect = dialect if dialect in self.SUPPORTED_DIALECTS else "mysql"
    
    def _build_system_prompt(self) -> str:
        """构建系统 Prompt"""
        dialect_specific = {
            "mysql": "使用 MySQL 语法，注意日期函数使用 DATE_SUB, DATE_ADD, NOW() 等",
            "postgresql": "使用 PostgreSQL 语法，注意日期函数使用 NOW(), INTERVAL 等",
            "sqlite": "使用 SQLite 语法，注意日期函数使用 datetime(), date() 等",
            "oracle": "使用 Oracle 语法，注意日期函数使用 SYSDATE, ADD_MONTHS 等",
            "sqlserver": "使用 SQL Server 语法，注意日期函数使用 GETDATE(), DATEADD 等"
        }
        
        return f"""你是一个专业的 SQL 生成专家。你的任务是根据提取的字段信息，生成准确、高效的 SQL 查询语句。

## 核心职责
1. 理解用户查询意图
2. 根据提供的字段信息构建查询逻辑
3. 选择合适的 JOIN 类型和条件
4. 生成符合 {self.dialect} 语法的 SQL
5. 提供清晰的查询解释

## SQL 方言说明
{dialect_specific.get(self.dialect, "使用标准 SQL 语法")}

## 输出格式
你必须以 JSON 格式输出，结构如下：
{{
  "sql": "生成的 SQL 语句（单行或多行）",
  "explanation": "查询逻辑的详细解释",
  "involved_tables": ["涉及的表名列表"],
  "confidence": 0.95  // 置信度 0-1
}}

## SQL 生成原则
1. **准确性**：SQL 语法必须正确，字段名必须使用提供的字段
2. **完整性**：包含所有必要的字段，不遗漏用户要求的信息
3. **性能**：优先使用 INNER JOIN，必要时使用 LEFT JOIN
4. **可读性**：适当使用别名（如 o 代表 orders, u 代表 users）
5. **安全性**：不要生成 DELETE, UPDATE, INSERT, DROP 等修改语句

## 常见查询模式

### 单表查询
```sql
SELECT column1, column2
FROM table_name
WHERE condition
ORDER BY column DESC
LIMIT 10;
```

### 多表 JOIN
```sql
SELECT t1.column1, t2.column2
FROM table1 t1
INNER JOIN table2 t2 ON t1.id = t2.id
WHERE condition
GROUP BY column
HAVING condition
ORDER BY column;
```

### 聚合查询
```sql
SELECT 
    category,
    COUNT(*) as count,
    SUM(amount) as total,
    AVG(price) as avg_price
FROM table_name
WHERE condition
GROUP BY category
HAVING count > 5
ORDER BY total DESC;
```

## 日期处理（{self.dialect}）
- 最近 N 天：根据方言选择正确的日期函数
- 特定时间段：使用 BETWEEN 或 >= AND <=
- 按时间分组：使用 DATE_FORMAT 或类似函数

## 重要提示
- 只输出 JSON，不要输出其他内容
- 确保 SQL 语法正确，可以被解析
- 表名和字段名必须与提供的信息完全一致
- 如果无法生成有效 SQL，confidence 设为 0 并说明原因
"""
    
    def _build_user_prompt(
        self,
        user_question: str,
        extracted_info_text: str
    ) -> str:
        """构建用户 Prompt"""
        return f"""用户问题：{user_question}

Agent 1 提取的字段信息：
{extracted_info_text}

请根据以上信息生成 SQL 查询语句，并以 JSON 格式输出结果。
"""
    
    def generate_sql(
        self,
        user_question: str,
        extracted_fields: List[ExtractedFields]
    ) -> SQLGenerationResult:
        """
        生成 SQL
        
        Args:
            user_question: 用户问题
            extracted_fields: Agent 1 提取的字段信息
            
        Returns:
            SQL 生成结果
        """
        # 格式化提取的信息
        extracted_info_text = self._format_extracted_fields(extracted_fields)
        
        # 构建 Prompt
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(user_question, extracted_info_text)
        
        # 调用 LLM
        response = self._call_llm(system_prompt, user_prompt, extracted_fields)
        
        # 解析结果
        try:
            result = json.loads(response)
            
            sql = result.get("sql", "")
            explanation = result.get("explanation", "")
            involved_tables = result.get("involved_tables", [])
            confidence = result.get("confidence", 0.0)
            
            # 格式化 SQL
            sql = self._format_sql(sql)
            
            # 验证 SQL
            is_valid, error_msg = self._validate_sql(sql)
            if not is_valid:
                confidence = 0.0
                explanation += f"\n\n[验证警告] {error_msg}"
            
            return SQLGenerationResult(
                sql=sql,
                explanation=explanation,
                involved_tables=involved_tables,
                confidence=confidence
            )
            
        except json.JSONDecodeError as e:
            print(f"解析 Agent 2 输出失败: {e}")
            print(f"原始输出: {response}")
            
            # 尝试从文本中提取 SQL
            sql = self._extract_sql_from_text(response)
            
            return SQLGenerationResult(
                sql=sql,
                explanation="从非标准输出中提取的 SQL，请人工检查",
                involved_tables=[ef.table_name for ef in extracted_fields],
                confidence=0.3
            )
    
    def _format_extracted_fields(self, extracted_fields: List[ExtractedFields]) -> str:
        """格式化提取的字段信息"""
        lines = []
        
        for ef in extracted_fields:
            lines.append(f"表: {ef.table_name}")
            lines.append(f"  字段: {', '.join(ef.selected_columns)}")
            lines.append(f"  理由: {ef.reason}")
            
            if ef.join_hints:
                lines.append(f"  JOIN: {'; '.join(ef.join_hints)}")
            
            if ef.filter_hints:
                lines.append(f"  过滤: {'; '.join(ef.filter_hints)}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _call_llm(self, system_prompt: str, user_prompt: str, extracted_fields: List[ExtractedFields]) -> str:
        """
        调用大模型
        
        实际使用时，这里应该调用真实的 LLM API
        """
        # TODO: 实现真实的 LLM 调用
        # 这里返回一个模拟的响应用于测试
        
        # 从提取的字段中构建一个简单的 SQL
        if extracted_fields:
            main_table = extracted_fields[0]
            columns = main_table.selected_columns[:5]  # 取前5个字段
            
            # 构建简单的 SELECT 语句
            sql = f"SELECT {', '.join(columns)}\nFROM {main_table.table_name}"
            
            # 如果有 JOIN 提示
            if len(extracted_fields) > 1 and main_table.join_hints:
                second_table = extracted_fields[1]
                sql += f"\nINNER JOIN {second_table.table_name} ON {main_table.join_hints[0]}"
            
            sql += ";"
            
            mock_response = {
                "sql": sql,
                "explanation": f"根据用户问题生成的查询，从 {main_table.table_name} 表中获取数据",
                "involved_tables": [ef.table_name for ef in extracted_fields],
                "confidence": 0.85
            }
        else:
            mock_response = {
                "sql": "SELECT 1;",
                "explanation": "未能提取到有效字段信息",
                "involved_tables": [],
                "confidence": 0.0
            }
        
        return json.dumps(mock_response, ensure_ascii=False)
    
    def _format_sql(self, sql: str) -> str:
        """格式化 SQL 语句"""
        if not sql:
            return sql
        
        # 基本清理
        sql = sql.strip()
        
        # 使用 sqlparse 格式化（如果可用）
        if SQLPARSE_AVAILABLE:
            try:
                formatted = sqlparse.format(
                    sql,
                    keyword_case='upper',
                    identifier_case='lower',
                    reindent=True,
                    wrap_after=80
                )
                return formatted.strip()
            except Exception:
                pass
        
        return sql
    
    def _validate_sql(self, sql: str) -> tuple[bool, str]:
        """
        验证 SQL 语法
        
        Returns:
            (是否有效, 错误信息)
        """
        if not sql:
            return False, "SQL 为空"
        
        # 检查是否为 SELECT 语句（安全限制）
        sql_upper = sql.upper().strip()
        
        # 禁止危险操作
        dangerous_keywords = ['DELETE', 'DROP', 'TRUNCATE', 'UPDATE', 'INSERT', 'ALTER']
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return False, f"检测到危险操作: {keyword}"
        
        # 使用 sqlparse 验证
        if SQLPARSE_AVAILABLE:
            try:
                parsed = sqlparse.parse(sql)
                if not parsed:
                    return False, "无法解析 SQL"
                
                # 检查第一个 token 是否为 SELECT
                first_token = None
                for token in parsed[0].tokens:
                    if not token.is_whitespace:
                        first_token = str(token).upper()
                        break
                
                if first_token != 'SELECT':
                    return False, f"SQL 必须以 SELECT 开头，当前为: {first_token}"
                
                return True, ""
                
            except Exception as e:
                return False, f"解析错误: {str(e)}"
        
        # 简单检查
        if not sql_upper.startswith('SELECT'):
            return False, "SQL 必须以 SELECT 开头"
        
        return True, ""
    
    def _extract_sql_from_text(self, text: str) -> str:
        """从文本中提取 SQL 语句"""
        # 尝试匹配代码块
        code_block_pattern = r'```sql\s*(.*?)```'
        match = re.search(code_block_pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # 尝试匹配 ``` 代码块
        code_block_pattern2 = r'```\s*(SELECT.*?)```'
        match = re.search(code_block_pattern2, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # 尝试匹配 SELECT 开头的语句
        select_pattern = r'(SELECT\s+.*?;?)'
        match = re.search(select_pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            sql = match.group(1).strip()
            # 确保以分号结尾
            if not sql.endswith(';'):
                sql += ';'
            return sql
        
        return ""
