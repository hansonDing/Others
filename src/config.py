"""
NL2SQL RAG 系统配置
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class VectorDBConfig:
    """向量数据库配置"""
    persist_directory: str = "./data/vector_db"
    collection_name: str = "table_descriptions"
    embedding_model: str = "BAAI/bge-large-zh-v1.5"  # 中文 Embedding 模型
    embedding_dim: int = 1024
    top_k: int = 5  # 检索返回的表数量
    similarity_threshold: float = 0.5  # 相似度阈值


@dataclass
class LLMConfig:
    """大模型配置"""
    model: str = "kimi-coding/k2p5"
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    temperature: float = 0.1  # 低温度确保 SQL 生成稳定
    max_tokens: int = 4096


@dataclass
class StorageConfig:
    """存储配置"""
    # 表详细信息存储路径
    table_info_path: str = "./data/table_info.json"
    # SQLite 数据库路径（可选）
    sqlite_path: str = "./data/metadata.db"
    # 是否使用 SQLite
    use_sqlite: bool = False


@dataclass
class NL2SQLConfig:
    """NL2SQL 系统整体配置"""
    vector_db: VectorDBConfig = None
    llm: LLMConfig = None
    storage: StorageConfig = None
    
    # Agent 配置
    agent1_max_tables: int = 5  # Agent 1 最多处理的表数量
    agent2_dialect: str = "mysql"  # SQL 方言
    
    def __post_init__(self):
        if self.vector_db is None:
            self.vector_db = VectorDBConfig()
        if self.llm is None:
            self.llm = LLMConfig()
        if self.storage is None:
            self.storage = StorageConfig()


# 全局配置实例
_config: Optional[NL2SQLConfig] = None


def get_config() -> NL2SQLConfig:
    """获取全局配置"""
    global _config
    if _config is None:
        _config = NL2SQLConfig()
    return _config


def set_config(config: NL2SQLConfig):
    """设置全局配置"""
    global _config
    _config = config
