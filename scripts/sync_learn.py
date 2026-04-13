#!/usr/bin/env python3
"""同步学习指定城市（用于测试）"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rag.background_learner import BackgroundLearner
from utils.logger import setup_logger

logger = setup_logger("sync_learn")


def sync_learn(city: str):
    """同步学习城市"""
    print(f"\n开始同步学习: {city}")

    # 创建学习器实例
    learner = BackgroundLearner()

    # 直接调用处理方法
    task = {"city": city, "user_query": "", "timestamp": ""}

    try:
        learner._process_learning_task(task)
        print(f"✅ 学习完成: {city}")
        print(f"已学习城市: {learner.get_learned_cities()}")
    except Exception as e:
        print(f"❌ 学习失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    city = sys.argv[1] if len(sys.argv) > 1 else "成都"
    sync_learn(city)