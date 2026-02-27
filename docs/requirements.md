# NL2SQL RAG 项目需求分析

## 1. 项目概述

**目标**: 构建一个自然语言生成 SQL 的 RAG 系统，通过向量检索表描述信息，再经过多 Agent 协作生成精准 SQL。

## 2. 核心需求拆解

### 2.1 数据存储层
| 数据类型 | 存储方式 | 用途 |
|---------|---------|------|
| 表描述信息 | 向量数据库 (向量化存储) | 用于语义检索，匹配用户问题与相关表 |
| 表字段信息 | 文本存储 (非向量化) | 详细字段定义、类型、约束等 |
| 表使用说明 | 文本存储 (非向量化) | 业务场景、使用示例、注意事项 |

### 2.2 查询流程
```
用户提问 → 向量检索表描述 → 获取相关表的全量信息 → Agent 1 提取相关字段 → Agent 2 生成 SQL
```

### 2.3 多 Agent 协作设计

**Agent 1: 字段提取专家**
- 输入: 用户问题 + 检索到的表完整信息（字段+使用说明）
- 输出: 与问题相关的字段子集 + 表关系
- 职责: 从大量字段中筛选出查询所需的关键字段

**Agent 2: SQL 生成专家**
- 输入: Agent 1 提取的精简字段信息 + 原始用户问题
- 输出: 完整的可执行 SQL 语句
- 职责: 根据精简后的信息生成准确的 SQL

## 3. 系统边界

### 3.1 支持范围
- ✅ 单表查询
- ✅ 多表 JOIN 查询
- ✅ 聚合查询 (GROUP BY, COUNT, SUM, AVG 等)
- ✅ 条件过滤 (WHERE, HAVING)
- ✅ 排序和分页 (ORDER BY, LIMIT)

### 3.2 暂不支持
- ❌ DDL 操作 (CREATE, ALTER, DROP)
- ❌ DML 操作 (INSERT, UPDATE, DELETE)
- ❌ 复杂子查询嵌套（可扩展）

## 4. 技术选型建议

| 组件 | 推荐方案 | 备选方案 |
|-----|---------|---------|
| 向量数据库 | ChromaDB (轻量) / Milvus (企业) | Pinecone, Weaviate |
| Embedding 模型 | BGE-large-zh / text-embedding-3 | m3e, GTE |
| LLM | Kimi / GPT-4 | Claude, Qwen |
| 框架 | LangChain / 原生实现 | LlamaIndex |

## 5. 数据结构设计

### 5.1 表元数据结构
```json
{
  "table_name": "orders",
  "table_description": "订单表，存储所有用户订单信息",
  "embedding_text": "订单表，存储所有用户订单信息，包含订单状态、金额、时间等",
  "columns": [
    {"name": "order_id", "type": "INT", "comment": "订单ID，主键"},
    {"name": "user_id", "type": "INT", "comment": "用户ID，外键关联users表"},
    {"name": "amount", "type": "DECIMAL", "comment": "订单金额"}
  ],
  "usage_guide": "查询订单时需要关联users表获取用户信息，金额字段单位为分"
}
```

### 5.2 向量存储结构
```
Collection: table_descriptions
- id: table_name
- embedding: vector(768)
- metadata: {table_name, description}
```

## 6. 关键设计决策

### 6.1 为什么字段信息不向量化？
1. **精度问题**: 字段级别的语义检索容易丢失上下文
2. **完整性问题**: 用户问题可能涉及多个字段的组合关系
3. **成本控制**: 减少向量存储和检索的复杂度
4. **可控性**: 通过 Agent 提取比纯向量匹配更可靠

### 6.2 为什么用两个 Agent？
1. **关注点分离**: 提取和生成是不同的认知任务
2. **上下文压缩**: Agent 1 将大量信息压缩为精简上下文
3. **可调试性**: 可以分别优化每个 Agent 的 prompt
4. **可扩展性**: 未来可插入更多 Agent（如 SQL 优化器）

## 7. 质量保障机制

- **检索召回率**: Top-K 表检索，确保不遗漏相关表
- **字段覆盖率**: Agent 1 需说明每个选中字段的理由
- **SQL 可执行性**: Agent 2 生成的 SQL 需通过语法检查
- **结果可解释性**: 输出 SQL 的同时说明查询逻辑

## 8. 扩展性考虑

- 支持多数据库方言 (MySQL, PostgreSQL, ClickHouse)
- 支持 SQL 执行和结果反馈（验证生成质量）
- 支持用户反馈收集（RLHF 优化）
- 支持历史查询缓存和相似问题推荐
