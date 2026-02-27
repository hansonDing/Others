# NL2SQL RAG 项目

自然语言生成 SQL 的 RAG 系统，通过向量检索表描述信息，再经过多 Agent 协作生成精准 SQL。

## 系统架构

```
用户提问 → 向量检索表描述 → 获取完整表信息 → Agent 1 提取字段 → Agent 2 生成 SQL
```

### 核心组件

1. **向量存储层**: 表描述信息向量化存储，用于语义检索
2. **文本存储层**: 表字段信息和使用说明以文本形式存储
3. **Agent 1 - 字段提取专家**: 从大量字段信息中提取相关字段
4. **Agent 2 - SQL 生成专家**: 根据提取的字段生成 SQL

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行演示

```bash
# 自动演示模式
python demo.py

# 交互式模式
python demo.py --interactive
```

### 基础使用

```python
from src import NL2SQLRAG, TableInfo, ColumnInfo

# 初始化系统
nl2sql = NL2SQLRAG()

# 添加表信息
table = TableInfo(
    name="users",
    description="用户表",
    columns=[
        ColumnInfo(name="id", data_type="INT", comment="主键", is_primary_key=True),
        ColumnInfo(name="name", data_type="VARCHAR(50)", comment="用户名"),
    ]
)
nl2sql.add_table(table)

# 执行查询
result = nl2sql.query("查询所有用户")
print(result['sql'])
```

## 项目结构

```
.
├── src/                    # 源代码
│   ├── __init__.py        # 包入口
│   ├── config.py          # 配置管理
│   ├── models.py          # 数据模型
│   ├── vector_store.py    # 向量数据库存储
│   ├── table_store.py     # 表信息文本存储
│   ├── agent_extractor.py # Agent 1: 字段提取
│   ├── agent_generator.py # Agent 2: SQL 生成
│   └── nl2sql.py          # 主入口
├── docs/                   # 文档
│   ├── requirements.md     # 需求分析
│   ├── architecture.md     # 架构设计
│   └── system_flow.mmd     # 流程图
├── data/                   # 数据存储（自动创建）
│   ├── vector_db/          # 向量数据库
│   └── table_info.json     # 表信息存储
├── demo.py                 # 演示脚本
├── requirements.txt        # 依赖列表
└── README.md              # 本文件
```

## 配置说明

### 向量数据库配置

```python
from src import NL2SQLConfig, VectorDBConfig

config = NL2SQLConfig(
    vector_db=VectorDBConfig(
        embedding_model="BAAI/bge-large-zh-v1.5",  # Embedding 模型
        top_k=5,  # 检索返回的表数量
        similarity_threshold=0.5  # 相似度阈值
    )
)

nl2sql = NL2SQLRAG(config)
```

### SQL 方言配置

```python
from src import NL2SQLConfig

config = NL2SQLConfig()
config.agent2_dialect = "postgresql"  # 支持 mysql, postgresql, sqlite, oracle, sqlserver

nl2sql = NL2SQLRAG(config)
```

## 核心概念

### 为什么表描述向量化，字段信息不向量化？

1. **精度问题**: 字段级别的语义检索容易丢失上下文
2. **完整性问题**: 用户问题可能涉及多个字段的组合关系
3. **可控性**: 通过 Agent 提取比纯向量匹配更可靠
4. **成本**: 减少向量存储和检索的复杂度

### 为什么使用两个 Agent？

1. **关注点分离**: 提取和生成是不同的认知任务
2. **上下文压缩**: Agent 1 将大量信息压缩为精简上下文
3. **可调试性**: 可以分别优化每个 Agent 的 prompt
4. **可扩展性**: 未来可插入更多 Agent（如 SQL 优化器）

## API 文档

### NL2SQLRAG 类

#### 初始化

```python
nl2sql = NL2SQLRAG(config=None)
```

#### 添加表

```python
nl2sql.add_table(table_info: TableInfo) -> str
nl2sql.add_tables(table_infos: List[TableInfo]) -> List[str]
```

#### 执行查询

```python
result = nl2sql.query(user_question: str, top_k: int = None)
# 返回: {
#     "success": bool,
#     "sql": str,
#     "explanation": str,
#     "confidence": float,
#     "retrieved_tables": List[Dict],
#     "extracted_fields": List[Dict],
#     "involved_tables": List[str]
# }
```

#### 其他方法

```python
nl2sql.get_table_info(table_name: str) -> Optional[TableInfo]
nl2sql.list_tables() -> List[str]
nl2sql.delete_table(table_name: str) -> bool
nl2sql.get_stats() -> Dict[str, Any]
```

## 开发计划

- [x] 需求分析
- [x] 系统架构设计
- [x] 核心功能实现
- [ ] 集成真实 LLM API
- [ ] SQL 执行和结果验证
- [ ] 用户反馈收集
- [ ] Web API 接口
- [ ] 前端界面

## 许可证

MIT
