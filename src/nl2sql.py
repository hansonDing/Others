"""
NL2SQL RAG 系统主入口
整合向量检索和多 Agent 协作
"""
from typing import List, Dict, Any, Optional
import json

from .config import get_config, NL2SQLConfig
from .models import TableInfo, SQLGenerationResult, ExtractedFields
from .vector_store import VectorStore
from .table_store import TableInfoStore
from .agent_extractor import FieldExtractorAgent
from .agent_generator import SQLGeneratorAgent


class NL2SQLRAG:
    """
    NL2SQL RAG 系统
    
    完整流程：
    1. 向量检索相关表
    2. 获取表完整信息
    3. Agent 1 提取相关字段
    4. Agent 2 生成 SQL
    """
    
    def __init__(self, config: Optional[NL2SQLConfig] = None):
        """
        初始化系统
        
        Args:
            config: 配置对象，None 使用默认配置
        """
        if config:
            set_config(config)
        
        self.config = get_config()
        
        # 初始化各组件
        self.vector_store = VectorStore()
        self.table_store = TableInfoStore()
        self.extractor_agent = FieldExtractorAgent()
        self.generator_agent = SQLGeneratorAgent(
            dialect=self.config.agent2_dialect
        )
    
    def add_table(self, table_info: TableInfo) -> str:
        """
        添加表到系统
        
        Args:
            table_info: 表信息
            
        Returns:
            表名
        """
        # 添加到向量数据库（表描述向量化）
        self.vector_store.add_table(table_info)
        
        # 添加到表信息存储（字段信息文本存储）
        self.table_store.add_table(table_info)
        
        return table_info.name
    
    def add_tables(self, table_infos: List[TableInfo]) -> List[str]:
        """批量添加表"""
        # 添加到向量数据库
        self.vector_store.add_tables(table_infos)
        
        # 添加到表信息存储
        self.table_store.add_tables(table_infos)
        
        return [t.name for t in table_infos]
    
    def query(self, user_question: str, top_k: Optional[int] = None) -> Dict[str, Any]:
        """
        处理用户查询
        
        Args:
            user_question: 用户自然语言问题
            top_k: 检索表数量，None 使用配置默认值
            
        Returns:
            包含 SQL 和详细信息的字典
        """
        print(f"\n{'='*60}")
        print(f"用户问题: {user_question}")
        print(f"{'='*60}\n")
        
        # Step 1: 向量检索相关表
        print("Step 1: 向量检索相关表...")
        search_results = self.vector_store.search(user_question, top_k=top_k)
        
        if not search_results:
            return {
                "success": False,
                "error": "未找到相关表",
                "sql": None,
                "explanation": None,
                "retrieved_tables": [],
                "extracted_fields": None,
                "generation_result": None
            }
        
        print(f"  检索到 {len(search_results)} 个相关表:")
        for result in search_results:
            print(f"    - {result['table_name']} (相似度: {result['similarity']})")
        
        # Step 2: 获取表完整信息
        print("\nStep 2: 获取表完整信息...")
        table_names = [r['table_name'] for r in search_results]
        table_infos = self.table_store.get_tables(table_names)
        
        print(f"  获取到 {len(table_infos)} 个表的详细信息")
        
        # Step 3: Agent 1 提取相关字段
        print("\nStep 3: Agent 1 提取相关字段...")
        extracted_fields = self.extractor_agent.extract_fields(
            user_question=user_question,
            table_infos=table_infos
        )
        
        print(f"  从 {len(extracted_fields)} 个表中提取了字段:")
        for ef in extracted_fields:
            print(f"    - {ef.table_name}: {', '.join(ef.selected_columns)}")
        
        # Step 4: Agent 2 生成 SQL
        print("\nStep 4: Agent 2 生成 SQL...")
        generation_result = self.generator_agent.generate_sql(
            user_question=user_question,
            extracted_fields=extracted_fields
        )
        
        print(f"  生成完成 (置信度: {generation_result.confidence})")
        
        # 构建返回结果
        result = {
            "success": generation_result.confidence > 0.5,
            "sql": generation_result.sql,
            "explanation": generation_result.explanation,
            "confidence": generation_result.confidence,
            "retrieved_tables": [
                {
                    "name": r['table_name'],
                    "description": r['description'],
                    "similarity": r['similarity']
                }
                for r in search_results
            ],
            "extracted_fields": [
                ef.to_dict() for ef in extracted_fields
            ],
            "involved_tables": generation_result.involved_tables
        }
        
        return result
    
    def query_with_details(self, user_question: str, top_k: Optional[int] = None) -> Dict[str, Any]:
        """
        查询并返回详细信息（用于调试）
        
        与 query 方法相同，但包含更多中间信息
        """
        result = self.query(user_question, top_k)
        
        # 添加中间过程的详细信息
        table_names = [r['name'] for r in result['retrieved_tables']]
        table_infos = self.table_store.get_tables(table_names)
        
        result['detailed_table_info'] = [
            {
                "name": ti.name,
                "full_info": ti.full_info_text
            }
            for ti in table_infos
        ]
        
        return result
    
    def get_table_info(self, table_name: str) -> Optional[TableInfo]:
        """获取表信息"""
        return self.table_store.get_table(table_name)
    
    def list_tables(self) -> List[str]:
        """列出所有表"""
        return self.table_store._load_all().keys()
    
    def delete_table(self, table_name: str) -> bool:
        """
        删除表
        
        Args:
            table_name: 表名
            
        Returns:
            是否成功
        """
        # 从向量数据库删除
        vector_deleted = self.vector_store.delete_table(table_name)
        
        # 从表信息存储删除
        info_deleted = self.table_store.delete_table(table_name)
        
        return vector_deleted and info_deleted
    
    def get_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        return {
            "vector_db": {
                "table_count": self.vector_store.count(),
                "collection_name": self.config.vector_db.collection_name
            },
            "table_store": {
                "table_count": len(self.table_store.get_all_tables()),
                "storage_path": self.config.storage.table_info_path
            },
            "config": {
                "embedding_model": self.config.vector_db.embedding_model,
                "sql_dialect": self.config.agent2_dialect,
                "top_k": self.config.vector_db.top_k
            }
        }


# 重新导入 set_config
from .config import set_config


# 便捷函数
def create_nl2sql(config: Optional[NL2SQLConfig] = None) -> NL2SQLRAG:
    """创建 NL2SQL RAG 实例"""
    return NL2SQLRAG(config)
