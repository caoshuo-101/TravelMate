# scripts/manage_learning.py - 修复显示已学习城市

# !/usr/bin/env python3
"""
后台学习管理脚本
查看学习状态、手动触发学习等
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rag.background_learner import get_background_learner
from rag.vector_store import VectorStoreManager
from utils.logger import setup_logger
from config.settings import settings

logger = setup_logger("manage_learning")


def get_learned_cities_from_files() -> list:
    """从文件系统中读取已学习的城市"""
    data_dir = Path(settings.DATA_DIR)
    if not data_dir.exists():
        return []

    cities = []
    for city_dir in data_dir.iterdir():
        if city_dir.is_dir():
            # 检查是否有自动生成的文件
            auto_files = list(city_dir.glob("auto_generated_*.md"))
            if auto_files:
                cities.append(city_dir.name)

    return cities


def show_status():
    """显示学习状态"""
    print("\n" + "=" * 50)
    print("后台学习状态")
    print("=" * 50)

    # 从文件系统读取已学习的城市
    learned = get_learned_cities_from_files()

    print(f"\n已学习的城市: {learned if learned else '无'}")

    # 查看向量库中的文档
    vs = VectorStoreManager()
    print(f"\n向量库文档总数: {vs.collection.count()}")

    # 显示每个城市的文档数
    if learned:
        print("\n各城市文档统计:")
        for city in learned:
            results = vs.collection.get(where={"city": city})
            count = len(results['ids']) if results['ids'] else 0
            print(f"  - {city}: {count} 个文档块")

    print("=" * 50)


def trigger_learning(city: str):
    """手动触发学习"""
    print(f"\n手动触发学习: {city}")

    learner = get_background_learner()
    learner.submit_learning_task(city)

    print(f"已提交学习任务，将在后台处理")
    print("使用 --status 查看学习状态")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="后台学习管理")
    parser.add_argument("--status", action="store_true", help="显示学习状态")
    parser.add_argument("--learn", type=str, help="手动学习指定城市")

    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.learn:
        trigger_learning(args.learn)
    else:
        print("用法:")
        print("  python manage_learning.py --status")
        print("  python manage_learning.py --learn 成都")


if __name__ == "__main__":
    main()