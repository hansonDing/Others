"""
表元数据模型定义
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
import json


@dataclass
class ColumnInfo:
    """字段信息"""
    name: str
    data_type: str
    comment: str = ""
    is_nullable: bool = True
    is_primary_key: bool = False
    is_foreign_key: bool = False
    foreign_key_table: Optional[str] = None
    foreign_key_column: Optional[str] = None
    default_value: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ColumnInfo":
        return cls(**data)
    
    def __str__(self) -> str:
        pk_mark = " [PK]" if self.is_primary_key else ""
        fk_mark = f" [FK->{self.foreign_key_table}.{self.foreign_key_column}]" if self.is_foreign_key else ""
        return f"  - {self.name}: {self.data_type}{pk_mark}{fk_mark} // {self.comment}"


@dataclass
class TableInfo:
    """表信息"""
    name: str
    description: str
    columns: List[ColumnInfo] = field(default_factory=list)
    usage_guide: str = ""  # 使用说明
    common_queries: List[str] = field(default_factory=list)  # 常见查询示例
    relationships: List[Dict[str, str]] = field(default_factory=list)  # 表关系
    
    @property
    def embedding_text(self) -> str:
        """
        用于向量化的文本
        组合表名、描述、使用说明生成 embedding 文本
        """
        text_parts = [
            f"表名: {self.name}",
            f"描述: {self.description}",
        ]
        if self.usage_guide:
            text_parts.append(f"使用说明: {self.usage_guide}")
        return "\n".join(text_parts)
    
    @property
    def full_info_text(self) -> str:
        """
        完整的表信息文本（用于发送给 Agent）
        """
        lines = [
            f"表名: {self.name}",
            f"描述: {self.description}",
            "",
            "字段信息:",
        ]
        for col in self.columns:
            lines.append(str(col))
        
        if self.usage_guide:
            lines.extend(["", "使用说明:", self.usage_guide])
        
        if self.relationships:
            lines.extend(["", "表关系:"])
            for rel in self.relationships:
                lines.append(f"  - {rel.get('description', '')}")
        
        if self.common_queries:
            lines.extend(["", "常见查询示例:"])
            for query in self.common_queries:
                lines.append(f"  - {query}")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "columns": [col.to_dict() for col in self.columns],
            "usage_guide": self.usage_guide,
            "common_queries": self.common_queries,
            "relationships": self.relationships,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TableInfo":
        """从字典创建"""
        columns = [ColumnInfo.from_dict(col) for col in data.get("columns", [])]
        return cls(
            name=data["name"],
            description=data["description"],
            columns=columns,
            usage_guide=data.get("usage_guide", ""),
            common_queries=data.get("common_queries", []),
            relationships=data.get("relationships", []),
        )
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "TableInfo":
        """从 JSON 字符串创建"""
        return cls.from_dict(json.loads(json_str))


@dataclass
class ExtractedFields:
    """Agent 1 提取的字段信息"""
    table_name: str
    selected_columns: List[str]
    reason: str  # 选择这些字段的理由
    join_hints: List[str] = field(default_factory=list)  # JOIN 建议
    filter_hints: List[str] = field(default_factory=list)  # 过滤条件建议
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractedFields":
        return cls(**data)


@dataclass
class SQLGenerationResult:
    """SQL 生成结果"""
    sql: str
    explanation: str
    involved_tables: List[str]
    confidence: float = 0.0  # 置信度
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SQLGenerationResult":
        return cls(**data)
