# NL2SQL RAG 项目实现总结

## 项目概述

本项目实现了一个自然语言生成 SQL 的 RAG 系统，核心特点是：
- **表描述向量化存储**：用于语义检索匹配用户问题
- **字段信息文本存储**：完整保留字段定义和使用说明
- **双 Agent 协作**：Agent 1 提取字段，Agent 2 生成 SQL

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        NL2SQL RAG 系统                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  用户提问 ──▶ 向量检索 ──▶ 获取表信息 ──▶ Agent 1 ──▶ Agent 2  │
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │ 向量存储层   │    │ 文本存储层   │    │    Agent 协作层      │ │
│  │ (表描述向量) │    │ (字段+说明)  │    │ 提取 → 生成         │ │
│  └─────────────┘    └─────────────┘    └─────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 核心模块

### 1. 数据模型 (`src/models.py`)

```python
TableInfo          # 表信息
├── name           # 表名
├── description    # 表描述（用于向量化）
├── columns        # 字段列表
├── usage_guide    # 使用说明
└── relationships  # 表关系

ColumnInfo         # 字段信息
├── name           # 字段名
├── data_type      # 数据类型
├── comment        # 注释
├── is_primary_key # 是否主键
└── is_foreign_key # 是否外键
```

### 2. 向量存储 (`src/vector_store.py`)

- **当前实现**：关键词匹配（演示用）
- **生产建议**：替换为真实 Embedding 模型
  ```python
  # 推荐方案
  from sentence_transformers import SentenceTransformer
  model = SentenceTransformer('BAAI/bge-large-zh-v1.5')
  ```

### 3. 表信息存储 (`src/table_store.py`)

- JSON 文件存储
- 内存缓存
- 支持增删改查

### 4. Agent 1 - 字段提取 (`src/agent_extractor.py`)

**职责**：
- 分析用户意图
- 从多表信息中提取相关字段
- 识别表关系

**输入**：用户问题 + 多表完整信息
**输出**：相关字段列表 + 选择理由

### 5. Agent 2 - SQL 生成 (`src/agent_generator.py`)

**职责**：
- 构建查询逻辑
- 选择 JOIN 策略
- 生成 SQL 语句

**输入**：精简字段信息 + 原始问题
**输出**：完整 SQL + 解释说明

## 使用示例

### 基础使用

```python
from src import NL2SQLRAG, TableInfo, ColumnInfo

# 初始化
nl2sql = NL2SQLRAG()

# 添加表
users = TableInfo(
    name="users",
    description="用户表",
    columns=[
        ColumnInfo(name="id", data_type="INT", is_primary_key=True),
        ColumnInfo(name="name", data_type="VARCHAR(50)"),
    ]
)
nl2sql.add_table(users)

# 查询
result = nl2sql.query("查询所有用户")
print(result['sql'])
```

### 运行演示

```bash
# 自动演示
python demo.py

# 交互模式
python demo.py --interactive
```

## 项目结构

```
.
├── src/                    # 源代码
│   ├── __init__.py
│   ├── config.py          # 配置管理
│   ├── models.py          # 数据模型
│   ├── vector_store.py    # 向量存储
│   ├── table_store.py     # 表信息存储
│   ├── agent_extractor.py # Agent 1
│   ├── agent_generator.py # Agent 2
│   └── nl2sql.py          # 主入口
├── docs/                   # 文档
│   ├── requirements.md     # 需求分析
│   ├── architecture.md     # 架构设计
│   └── system_flow.mmd     # 流程图
├── data/                   # 数据存储
│   └── vector_db/          # 向量数据
├── demo.py                 # 演示脚本
├── requirements.txt        # 依赖
└── README.md              # 说明文档
```

## 关键设计决策

### 1. 为什么表描述向量化，字段信息不向量化？

| 方案 | 优点 | 缺点 |
|-----|------|------|
| **全部向量化** | 检索粒度细 | 丢失上下文、混入噪音 |
| **表描述向量化** | 保留完整上下文、可控性强 | 需要 Agent 提取字段 |

**选择**：表描述向量化 + Agent 提取

### 2. 为什么使用两个 Agent？

| 方案 | 优点 | 缺点 |
|-----|------|------|
| **单 Agent** | 简单直接 | 上下文过长、容易遗漏 |
| **双 Agent** | 关注点分离、可调试 | 增加一次 LLM 调用 |

**选择**：双 Agent，第一阶段压缩上下文，第二阶段专注生成

## 待完善项

### 高优先级
- [ ] 集成真实 LLM API（OpenAI / Kimi / Claude）
- [ ] 使用真实 Embedding 模型（sentence-transformers）
- [ ] SQL 语法校验增强

### 中优先级
- [ ] 支持多数据库方言
- [ ] SQL 执行和结果验证
- [ ] Web API 接口

### 低优先级
- [ ] 前端界面
- [ ] 用户反馈收集
- [ ] 查询历史缓存

## 生产环境建议

### 1. LLM 集成

```python
# 示例：集成 Kimi API
import openai

client = openai.OpenAI(
    api_key="your-api-key",
    base_url="https://api.moonshot.cn/v1"
)

def call_llm(system_prompt, user_prompt):
    response = client.chat.completions.create(
        model="kimi-coding/k2p5",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.1
    )
    return response.choices[0].message.content
```

### 2. Embedding 模型

```python
# 示例：使用 BGE 模型
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('BAAI/bge-large-zh-v1.5')

# 中文文本前添加指令
texts = ["为这个句子生成表示：" + desc for desc in descriptions]
embeddings = model.encode(texts, normalize_embeddings=True)
```

### 3. 向量数据库

推荐使用 ChromaDB 或 Milvus：
- **ChromaDB**：轻量、易部署
- **Milvus**：企业级、高性能

## 性能优化建议

1. **缓存**：缓存常见查询的 SQL 结果
2. **索引**：为表描述创建高效向量索引
3. **批处理**：批量处理相似查询
4. **预热**：系统启动时预热 Embedding 模型

## 总结

本项目提供了一个完整的 NL2SQL RAG 系统框架，核心创新点在于：

1. **分层存储**：向量存储用于检索，文本存储用于生成
2. **双 Agent 协作**：分离字段提取和 SQL 生成任务
3. **可扩展架构**：易于替换 Embedding 模型和 LLM

当前为演示版本，使用关键词匹配代替真实向量检索。生产环境建议：
- 替换为真实 Embedding 模型
- 集成 LLM API
- 添加 SQL 执行验证
