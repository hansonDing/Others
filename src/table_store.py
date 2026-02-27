"""
表详细信息存储模块
负责表字段信息和使用说明的文本存储
"""
import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

from .models import TableInfo
from .config import get_config


class TableInfoStore:
    """表信息存储管理"""
    
    def __init__(self):
        self.config = get_config().storage
        self._ensure_storage_exists()
        self._cache: Dict[str, TableInfo] = {}  # 内存缓存
    
    def _ensure_storage_exists(self):
        """确保存储目录和文件存在"""
        storage_path = Path(self.config.table_info_path)
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not storage_path.exists():
            with open(storage_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
    
    def _load_all(self) -> Dict[str, Any]:
        """加载所有表信息"""
        try:
            with open(self.config.table_info_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    def _save_all(self, data: Dict[str, Any]):
        """保存所有表信息"""
        with open(self.config.table_info_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_table(self, table_info: TableInfo) -> str:
        """
        添加或更新表信息
        
        Args:
            table_info: 表信息
            
        Returns:
            表名
        """
        data = self._load_all()
        data[table_info.name] = table_info.to_dict()
        self._save_all(data)
        
        # 更新缓存
        self._cache[table_info.name] = table_info
        
        return table_info.name
    
    def add_tables(self, table_infos: List[TableInfo]) -> List[str]:
        """批量添加表信息"""
        data = self._load_all()
        names = []
        
        for table_info in table_infos:
            data[table_info.name] = table_info.to_dict()
            names.append(table_info.name)
            self._cache[table_info.name] = table_info
        
        self._save_all(data)
        return names
    
    def get_table(self, table_name: str) -> Optional[TableInfo]:
        """
        获取单个表信息
        
        Args:
            table_name: 表名
            
        Returns:
            表信息，不存在返回 None
        """
        # 先查缓存
        if table_name in self._cache:
            return self._cache[table_name]
        
        # 从文件加载
        data = self._load_all()
        if table_name in data:
            table_info = TableInfo.from_dict(data[table_name])
            self._cache[table_name] = table_info
            return table_info
        
        return None
    
    def get_tables(self, table_names: List[str]) -> List[TableInfo]:
        """
        批量获取表信息
        
        Args:
            table_names: 表名列表
            
        Returns:
            表信息列表
        """
        return [table for table in (self.get_table(name) for name in table_names) if table]
    
    def get_all_tables(self) -> List[TableInfo]:
        """获取所有表信息"""
        data = self._load_all()
        return [TableInfo.from_dict(t) for t in data.values()]
    
    def delete_table(self, table_name: str) -> bool:
        """
        删除表信息
        
        Args:
            table_name: 表名
            
        Returns:
            是否成功
        """
        data = self._load_all()
        if table_name in data:
            del data[table_name]
            self._save_all(data)
            
            # 清除缓存
            if table_name in self._cache:
                del self._cache[table_name]
            
            return True
        return False
    
    def get_table_full_info_text(self, table_name: str) -> str:
        """
        获取表的完整信息文本（用于发送给 Agent）
        
        Args:
            table_name: 表名
            
        Returns:
            完整信息文本
        """
        table_info = self.get_table(table_name)
        if table_info:
            return table_info.full_info_text
        return f"表 {table_name} 不存在"
    
    def get_tables_full_info_text(self, table_names: List[str]) -> str:
        """
        获取多个表的完整信息文本
        
        Args:
            table_names: 表名列表
            
        Returns:
            拼接后的完整信息文本
        """
        parts = []
        for name in table_names:
            text = self.get_table_full_info_text(name)
            parts.append(text)
            parts.append("\n" + "="*50 + "\n")
        
        return "\n".join(parts)
    
    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        if table_name in self._cache:
            return True
        
        data = self._load_all()
        return table_name in data
    
    def clear_cache(self):
        """清除内存缓存"""
        self._cache.clear()
    
    def reload(self):
        """重新加载数据"""
        self._cache.clear()
