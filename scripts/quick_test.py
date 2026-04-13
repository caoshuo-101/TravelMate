#!/usr/bin/env python3
"""快速测试旅途智伴功能"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent.graph import travel_graph
from agent.state import create_initial_state

test_cases = [
    ("基础问候", "你好"),
    ("天气查询", "北京天气怎么样"),
    ("景点推荐", "北京有什么好玩的"),
    ("行程规划", "帮我规划一个北京三日游"),
    ("偏好设置", "我喜欢安静的地方"),
]

print("=" * 60)
print("旅途智伴快速测试")
print("=" * 60)

for name, query in test_cases:
    print(f"\n📝 测试: {name}")
    print(f"用户: {query}")

    state = create_initial_state(query)
    try:
        result = travel_graph.invoke(state)
        response = result.get("response", "无响应")
        print(f"助手: {response[:200]}...")
        print("✅ 通过")
    except Exception as e:
        print(f"❌ 失败: {e}")

    print("-" * 40)