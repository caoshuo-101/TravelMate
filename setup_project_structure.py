#!/usr/bin/env python3
"""
项目结构搭建脚本 (setup_project_structure.py)
功能：根据开发文档创建完整的项目目录和空文件
"""

import os
import sys
from pathlib import Path

# 定义项目根目录（脚本所在目录）
PROJECT_ROOT = Path(__file__).parent

# 定义所有需要创建的目录（相对于项目根目录）
DIRECTORIES = [
    "agent",
    "config",
    "data/北京",
    "data/上海",
    "data/杭州",
    "logs",
    "model",
    "rag",
    "scripts",
    "tools",
    "utils",
]

# 定义所有需要创建的空文件（相对于项目根目录）
FILES = [
    "agent/__init__.py",
    "agent/graph.py",
    "agent/state.py",
    "agent/nodes.py",
    "agent/middleware.py",
    "config/__init__.py",
    "config/settings.py",
    "config/prompts.py",
    "config/apis.yml",
    "model/__init__.py",
    "model/factory.py",
    "model/chat_model.py",
    "model/embedding_model.py",
    "rag/__init__.py",
    "rag/vector_store.py",
    "rag/retriever.py",
    "rag/knowledge_base.py",
    "rag/background_learner.py",
    "scripts/setup_data.py",
    "scripts/init_chroma.py",
    "tools/__init__.py",
    "tools/weather.py",
    "tools/traffic.py",
    "tools/attraction.py",
    "tools/preference.py",
    "tools/itinerary.py",
    "utils/__init__.py",
    "utils/config_loader.py",
    "utils/logger.py",
    "utils/file_utils.py",
    "utils/validators.py",
    "app.py",
]


def create_directories():
    """创建所有必需的目录"""
    print("\n📁 创建项目目录...")
    for dir_path in DIRECTORIES:
        full_path = PROJECT_ROOT / dir_path
        try:
            full_path.mkdir(parents=True, exist_ok=True)
            print(f"  ✅ 创建目录: {dir_path}")
        except Exception as e:
            print(f"  ❌ 创建目录失败 {dir_path}: {e}")
            sys.exit(1)


def create_files():
    """创建所有必需的空文件"""
    print("\n📄 创建项目文件...")
    for file_path in FILES:
        full_path = PROJECT_ROOT / file_path
        try:
            # 确保文件所在目录存在
            full_path.parent.mkdir(parents=True, exist_ok=True)
            # 创建空文件
            full_path.touch(exist_ok=True)
            print(f"  ✅ 创建文件: {file_path}")
        except Exception as e:
            print(f"  ❌ 创建文件失败 {file_path}: {e}")
            sys.exit(1)


def create_gitkeep():
    """为可能的空目录创建 .gitkeep 文件（可选）"""
    print("\n🔧 处理空目录占位符...")
    for dir_path in DIRECTORIES:
        gitkeep_path = PROJECT_ROOT / dir_path / ".gitkeep"
        if not any((PROJECT_ROOT / dir_path).iterdir()):
            try:
                gitkeep_path.touch(exist_ok=True)
                print(f"  ✅ 创建占位文件: {dir_path}/.gitkeep")
            except Exception as e:
                print(f"  ❌ 创建占位文件失败 {dir_path}: {e}")


def print_summary():
    """打印项目结构总结"""
    print("\n" + "=" * 50)
    print("🎉 项目结构搭建完成！")
    print("=" * 50)
    print(f"项目根目录: {PROJECT_ROOT}")
    print(f"目录数量: {len(DIRECTORIES)}")
    print(f"文件数量: {len(FILES)}")
    print("\n下一步操作:")
    print("1. 编辑 config/apis.yml 填入你的 API 密钥")
    print("2. 运行 python scripts/setup_data.py 初始化数据")
    print("3. 运行 streamlit run app.py 启动应用")
    print("=" * 50)


def main():
    """主函数"""
    print("🚀 开始搭建旅途智伴（TravelMate）项目结构...")

    # 确认是否在正确的目录执行
    response = input(f"\n将在当前目录创建项目结构: {PROJECT_ROOT}\n是否继续？(y/n): ")
    if response.lower() != 'y':
        print("❌ 操作已取消")
        sys.exit(0)

    create_directories()
    create_files()
    create_gitkeep()
    print_summary()


if __name__ == "__main__":
    main()