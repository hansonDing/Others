"""
向量数据库管理模块 (关键词匹配版)
使用关键词匹配进行表检索，确保演示可用
"""
import os
import re
from typing import List, Dict, Any, Optional
import json

from .config import get_config
from .models import TableInfo


class KeywordMatcher:
    """
    关键词匹配器
    用于演示阶段，基于关键词匹配检索相关表
    """
    
    def __init__(self):
        # 表名到关键词的映射
        self._table_keywords: Dict[str, List[str]] = {}
    
    def extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        # 简单的中文分词：提取2-4个字的词组
        words = []
        text = text.lower()
        
        # 提取表名相关的关键词
        # 用户、订单、商品、分类等
        keywords = [
            '用户', '订单', '商品', '产品', '分类', '明细',
            'user', 'order', 'product', 'category', 'item'
        ]
        
        for kw in keywords:
            if kw in text:
                words.append(kw)
        
        return words
    
    def calculate_similarity(self, query: str, table_info: TableInfo) -> float:
        """
        计算查询与表的相似度
        基于关键词匹配
        """
        query_lower = query.lower()
        
        # 表名精确匹配（最高权重）
        if table_info.name.lower() in query_lower:
            return 0.95
        
        # 描述匹配
        desc_lower = table_info.description.lower()
        score = 0.0
        
        # 关键词匹配 - 扩展关键词库
        keyword_mapping = {
            '用户': ['users', 'user'],
            '订单': ['orders', 'order'],
            '商品': ['products', 'product'],
            '产品': ['products', 'product'],
            '分类': ['categories', 'category'],
            '明细': ['order_items', 'item'],
            '金额': ['orders', 'amount', 'price'],
            '销售': ['orders', 'order_items', 'products'],
            '购买': ['orders', 'order_items'],
        }
        
        # 检查查询中的关键词
        for keyword, related_tables in keyword_mapping.items():
            if keyword in query:
                # 如果表名在相关表中，增加分数
                if table_info.name in related_tables:
                    score += 0.4
                # 检查描述中是否包含关键词
                if keyword in desc_lower:
                    score += 0.2
        
        # 字段名匹配
        for col in table_info.columns:
            col_name_lower = col.name.lower()
            col_comment_lower = col.comment.lower()
            
            # 提取查询中的关键字段名
            query_keywords = query_lower.replace('查询', '').replace('统计', '').split()
            for kw in query_keywords:
                if len(kw) >= 2:
                    if kw in col_name_lower or kw in col_comment_lower:
                        score += 0.15
        
        return min(score, 0.9)  # 最高 0.9，留给精确匹配


class VectorStore:
    """
    向量存储管理 (关键词匹配版)
    演示使用，基于关键词匹配检索相关表
    """
    
    def __init__(self):
        self.config = get_config().vector_db
        self.matcher = KeywordMatcher()
        
        # 内存存储
        self._data: Dict[str, TableInfo] = {}
        
        # 尝试从文件加载
        self._load_from_file()
    
    def _get_storage_path(self) -> str:
        """获取存储路径"""
        return os.path.join(self.config.persist_directory, "table_vectors.json")
    
    def _load_from_file(self):
        """从文件加载数据"""
        storage_path = self._get_storage_path()
        if os.path.exists(storage_path):
            try:
                with open(storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for table_id, table_dict in data.items():
                        self._data[table_id] = TableInfo.from_dict(table_dict)
            except Exception as e:
                print(f"加载向量数据失败: {e}")
                self._data = {}
    
    def _save_to_file(self):
        """保存数据到文件"""
        os.makedirs(self.config.persist_directory, exist_ok=True)
        storage_path = self._get_storage_path()
        try:
            data = {k: v.to_dict() for k, v in self._data.items()}
            with open(storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存向量数据失败: {e}")
    
    def add_table(self, table_info: TableInfo) -> str:
        """添加表到向量数据库"""
        table_id = table_info.name
        self._data[table_id] = table_info
        self._save_to_file()
        return table_id
    
    def add_tables(self, table_infos: List[TableInfo]) -> List[str]:
        """批量添加表"""
        ids = []
        for table_info in table_infos:
            table_id = self.add_table(table_info)
            ids.append(table_id)
        return ids
    
    def search(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        检索相关表
        基于关键词匹配
        """
        if top_k is None:
            top_k = self.config.top_k
        
        # 计算每个表的相似度
        results = []
        for table_id, table_info in self._data.items():
            similarity = self.matcher.calculate_similarity(query, table_info)
            
            # 过滤低相似度结果
            if similarity < self.config.similarity_threshold:
                continue
            
            results.append({
                "table_name": table_id,
                "description": table_info.description,
                "similarity": round(similarity, 4),
                "document": table_info.embedding_text
            })
        
        # 按相似度排序
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        # 返回 top_k
        return results[:top_k]
    
    def delete_table(self, table_name: str) -> bool:
        """删除表"""
        if table_name in self._data:
            del self._data[table_name]
            self._save_to_file()
            return True
        return False
    
    def get_all_tables(self) -> List[str]:
        """获取所有表名"""
        return list(self._data.keys())
    
    def clear(self):
        """清空所有数据"""
        self._data = {}
        self._save_to_file()
    
    def count(self) -> int:
        """获取表数量"""
        return len(self._data)
