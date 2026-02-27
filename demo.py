#!/usr/bin/env python3
"""
NL2SQL RAG 系统演示脚本
展示如何使用系统实现自然语言到 SQL 的转换
"""
import json
import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent))

from src import NL2SQLRAG, TableInfo, ColumnInfo


def create_sample_tables():
    """创建示例表数据"""
    
    # 用户表
    users_table = TableInfo(
        name="users",
        description="用户表，存储所有注册用户的基本信息",
        columns=[
            ColumnInfo(name="user_id", data_type="INT", comment="用户ID，主键", is_primary_key=True),
            ColumnInfo(name="username", data_type="VARCHAR(50)", comment="用户名"),
            ColumnInfo(name="email", data_type="VARCHAR(100)", comment="邮箱地址"),
            ColumnInfo(name="phone", data_type="VARCHAR(20)", comment="手机号"),
            ColumnInfo(name="created_at", data_type="DATETIME", comment="注册时间"),
            ColumnInfo(name="status", data_type="TINYINT", comment="用户状态：0-禁用 1-正常"),
        ],
        usage_guide="查询用户信息时使用，user_id 是主键，与 orders 表一对多关联",
        common_queries=[
            "查询最近注册的用户",
            "统计各状态用户数量"
        ],
        relationships=[
            {"description": "users.user_id = orders.user_id (一对多)"}
        ]
    )
    
    # 订单表
    orders_table = TableInfo(
        name="orders",
        description="订单表，存储所有用户订单信息",
        columns=[
            ColumnInfo(name="order_id", data_type="INT", comment="订单ID，主键", is_primary_key=True),
            ColumnInfo(name="user_id", data_type="INT", comment="用户ID，外键关联 users 表", is_foreign_key=True, foreign_key_table="users", foreign_key_column="user_id"),
            ColumnInfo(name="amount", data_type="DECIMAL(10,2)", comment="订单金额，单位：元"),
            ColumnInfo(name="status", data_type="TINYINT", comment="订单状态：0-待支付 1-已支付 2-已发货 3-已完成 4-已取消"),
            ColumnInfo(name="created_at", data_type="DATETIME", comment="订单创建时间"),
            ColumnInfo(name="paid_at", data_type="DATETIME", comment="支付时间，未支付为 NULL"),
        ],
        usage_guide="查询订单时需要关联 users 表获取用户信息，金额字段单位为元，注意区分订单状态",
        common_queries=[
            "查询某用户的所有订单",
            "统计最近一周的订单金额",
            "查询待支付的订单"
        ],
        relationships=[
            {"description": "orders.user_id = users.user_id (多对一)"},
            {"description": "orders.order_id = order_items.order_id (一对多)"}
        ]
    )
    
    # 订单明细表
    order_items_table = TableInfo(
        name="order_items",
        description="订单明细表，存储订单中的商品信息",
        columns=[
            ColumnInfo(name="item_id", data_type="INT", comment="明细ID，主键", is_primary_key=True),
            ColumnInfo(name="order_id", data_type="INT", comment="订单ID，外键关联 orders 表", is_foreign_key=True, foreign_key_table="orders", foreign_key_column="order_id"),
            ColumnInfo(name="product_id", data_type="INT", comment="商品ID，外键关联 products 表", is_foreign_key=True, foreign_key_table="products", foreign_key_column="product_id"),
            ColumnInfo(name="quantity", data_type="INT", comment="购买数量"),
            ColumnInfo(name="unit_price", data_type="DECIMAL(10,2)", comment="单价，单位：元"),
            ColumnInfo(name="subtotal", data_type="DECIMAL(10,2)", comment="小计金额 = 数量 * 单价"),
        ],
        usage_guide="查询订单明细时使用，需要关联 orders 表和 products 表",
        common_queries=[
            "查询某订单包含的商品",
            "统计各商品的销售数量"
        ],
        relationships=[
            {"description": "order_items.order_id = orders.order_id (多对一)"},
            {"description": "order_items.product_id = products.product_id (多对一)"}
        ]
    )
    
    # 商品表
    products_table = TableInfo(
        name="products",
        description="商品表，存储所有商品信息",
        columns=[
            ColumnInfo(name="product_id", data_type="INT", comment="商品ID，主键", is_primary_key=True),
            ColumnInfo(name="product_name", data_type="VARCHAR(200)", comment="商品名称"),
            ColumnInfo(name="category_id", data_type="INT", comment="分类ID，外键关联 categories 表"),
            ColumnInfo(name="price", data_type="DECIMAL(10,2)", comment="商品价格，单位：元"),
            ColumnInfo(name="stock", data_type="INT", comment="库存数量"),
            ColumnInfo(name="created_at", data_type="DATETIME", comment="上架时间"),
        ],
        usage_guide="查询商品信息时使用，product_id 是主键",
        common_queries=[
            "查询某分类下的商品",
            "查询库存不足的商品"
        ],
        relationships=[
            {"description": "products.category_id = categories.category_id (多对一)"}
        ]
    )
    
    # 商品分类表
    categories_table = TableInfo(
        name="categories",
        description="商品分类表，存储商品分类信息",
        columns=[
            ColumnInfo(name="category_id", data_type="INT", comment="分类ID，主键", is_primary_key=True),
            ColumnInfo(name="category_name", data_type="VARCHAR(50)", comment="分类名称"),
            ColumnInfo(name="parent_id", data_type="INT", comment="父分类ID，0表示顶级分类"),
            ColumnInfo(name="description", data_type="TEXT", comment="分类描述"),
        ],
        usage_guide="查询商品分类时使用，支持多级分类",
        common_queries=[
            "查询所有分类",
            "查询某分类下的子分类"
        ],
        relationships=[]
    )
    
    return [users_table, orders_table, order_items_table, products_table, categories_table]


def demo():
    """演示 NL2SQL RAG 系统"""
    
    print("=" * 70)
    print("NL2SQL RAG 系统演示")
    print("=" * 70)
    
    # 初始化系统
    print("\n[1] 初始化 NL2SQL RAG 系统...")
    nl2sql = NL2SQLRAG()
    print("    系统初始化完成")
    
    # 添加示例表
    print("\n[2] 添加示例表数据...")
    tables = create_sample_tables()
    for table in tables:
        nl2sql.add_table(table)
        print(f"    ✓ 添加表: {table.name}")
    
    # 显示系统统计
    print("\n[3] 系统统计信息:")
    stats = nl2sql.get_stats()
    print(f"    向量数据库表数量: {stats['vector_db']['table_count']}")
    print(f"    表信息存储数量: {stats['table_store']['table_count']}")
    print(f"    Embedding 模型: {stats['config']['embedding_model']}")
    print(f"    SQL 方言: {stats['config']['sql_dialect']}")
    
    # 测试查询
    test_questions = [
        "查询最近一周下单的用户",
        "统计每个用户的订单总金额",
        "查询订单金额超过1000的用户信息",
        "查询购买了电子产品的用户",
        "统计最近一个月各分类的商品销售数量",
    ]
    
    print("\n[4] 执行测试查询...")
    print("-" * 70)
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n测试 {i}/{len(test_questions)}: {question}")
        print("-" * 70)
        
        result = nl2sql.query(question)
        
        if result['success']:
            print(f"\n✓ 查询成功 (置信度: {result['confidence']:.2f})")
            print(f"\n生成的 SQL:")
            print(f"```sql")
            print(result['sql'])
            print(f"```")
            print(f"\n查询解释:")
            print(result['explanation'])
        else:
            print(f"\n✗ 查询失败: {result.get('error', '未知错误')}")
        
        print(f"\n涉及的表:")
        for table in result['retrieved_tables']:
            print(f"  - {table['name']} (相似度: {table['similarity']})")
        
        print("\n" + "=" * 70)
    
    print("\n演示完成！")


def interactive_demo():
    """交互式演示"""
    print("=" * 70)
    print("NL2SQL RAG 交互式演示")
    print("输入自然语言查询，输入 'quit' 退出")
    print("=" * 70)
    
    # 初始化系统
    nl2sql = NL2SQLRAG()
    
    # 添加示例表
    tables = create_sample_tables()
    for table in tables:
        nl2sql.add_table(table)
    
    print(f"\n已加载 {len(tables)} 个示例表")
    print("可用表: users, orders, order_items, products, categories\n")
    
    while True:
        try:
            question = input("\n请输入查询: ").strip()
            
            if question.lower() in ['quit', 'exit', 'q']:
                print("再见！")
                break
            
            if not question:
                continue
            
            result = nl2sql.query(question)
            
            print(f"\n{'='*60}")
            if result['success']:
                print(f"✓ 生成成功 (置信度: {result['confidence']:.2f})")
                print(f"\nSQL:")
                print(result['sql'])
                print(f"\n解释: {result['explanation']}")
            else:
                print(f"✗ 失败: {result.get('error', '未知错误')}")
            print(f"{'='*60}")
            
        except KeyboardInterrupt:
            print("\n再见！")
            break
        except Exception as e:
            print(f"错误: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='NL2SQL RAG 演示')
    parser.add_argument('--interactive', '-i', action='store_true', help='交互模式')
    args = parser.parse_args()
    
    if args.interactive:
        interactive_demo()
    else:
        demo()
