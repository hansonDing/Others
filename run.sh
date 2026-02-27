#!/bin/bash
# NL2SQL RAG 项目启动脚本

echo "=========================================="
echo "NL2SQL RAG 系统启动"
echo "=========================================="

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 检查依赖
echo "检查依赖..."
pip install -q numpy pydantic sqlparse 2>/dev/null

# 清理旧数据（可选）
read -p "是否清理旧数据? (y/N): " clean_data
if [ "$clean_data" = "y" ] || [ "$clean_data" = "Y" ]; then
    echo "清理旧数据..."
    rm -rf data/vector_db
fi

echo ""
echo "选择运行模式:"
echo "1. 自动演示模式"
echo "2. 交互式模式"
echo "3. 退出"
read -p "请选择 (1-3): " mode

case $mode in
    1)
        echo ""
        echo "运行自动演示..."
        python3 demo.py
        ;;
    2)
        echo ""
        echo "启动交互式模式..."
        python3 demo.py --interactive
        ;;
    3)
        echo "退出"
        exit 0
        ;;
    *)
        echo "无效选择，运行自动演示..."
        python3 demo.py
        ;;
esac
