"""
NL2SQL RAG 系统
自然语言生成 SQL 的 RAG 项目
"""

__version__ = "0.1.0"

from .config import NL2SQLConfig, VectorDBConfig, LLMConfig, StorageConfig, get_config, set_config
from .models import TableInfo, ColumnInfo, ExtractedFields, SQLGenerationResult
from .nl2sql import NL2SQLRAG, create_nl2sql
from .vector_store import VectorStore
from .table_store import TableInfoStore
from .agent_extractor import FieldExtractorAgent
from .agent_generator import SQLGeneratorAgent

__all__ = [
    # 主类
    'NL2SQLRAG',
    'create_nl2sql',
    
    # 配置
    'NL2SQLConfig',
    'VectorDBConfig',
    'LLMConfig',
    'StorageConfig',
    'get_config',
    'set_config',
    
    # 模型
    'TableInfo',
    'ColumnInfo',
    'ExtractedFields',
    'SQLGenerationResult',
    
    # 组件
    'VectorStore',
    'TableInfoStore',
    'FieldExtractorAgent',
    'SQLGeneratorAgent',
]
