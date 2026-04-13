#!/usr/bin/env python3
# scripts/setup_data.py
"""
数据初始化脚本
功能：
1. 创建目录结构
2. 生成示例文档
3. 检查环境
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.logger import setup_logger

logger = setup_logger("setup")


def create_directory_structure():
    """创建项目目录结构"""
    dirs = [
        "data/北京",
        "data/上海",
        "data/杭州",
        "logs",
        "chroma_db",
        "saved_itineraries",
        "config"
    ]

    for dir_path in dirs:
        full_path = PROJECT_ROOT / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ 创建目录: {dir_path}")

    return True


def generate_sample_documents():
    """生成示例文档"""
    samples = {
        "北京/attractions.md": """# 北京景点推荐

## 故宫
- 开放时间：8:30-17:00（旺季），8:30-16:30（淡季）
- 门票：旺季60元，淡季40元
- 建议游玩时间：3-4小时
- 特色：明清皇家宫殿，世界文化遗产
- 小贴士：周一闭馆，需提前7天预约

## 长城（八达岭）
- 开放时间：7:30-16:00
- 门票：40元
- 建议游玩时间：4-5小时
- 特色：世界七大奇迹之一
- 交通：S2线火车或公交专线

## 颐和园
- 开放时间：6:30-18:00
- 门票：旺季30元，淡季20元
- 建议游玩时间：2-3小时
- 特色：皇家园林，昆明湖
""",
        "北京/restaurants.md": """# 北京美食推荐

## 北京烤鸭
- 全聚德：百年老店，挂炉烤鸭
- 便宜坊：焖炉烤鸭，历史更悠久
- 大董：创意烤鸭，环境优雅

## 老北京小吃
- 豆汁配焦圈：地道北京早餐
- 炸酱面：家常味道
- 卤煮火烧：特色小吃
- 爆肚：清真美食

## 推荐餐厅
- 四季民福烤鸭店
- 护国寺小吃
- 牛街美食街
""",
        "北京/guide.txt": """北京旅行攻略

最佳旅行季节：春季（4-5月）和秋季（9-10月）

建议行程：
- 3日游：故宫-长城-颐和园-天坛
- 5日游：增加胡同游、798艺术区

交通建议：
- 地铁：覆盖主要景点
- 公交：可使用一卡通

注意事项：
- 提前预约热门景点
- 注意防晒和补水
"""
    }

    for file_path, content in samples.items():
        full_path = PROJECT_ROOT / "data" / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"✅ 生成示例文档: data/{file_path}")

    return True


def check_apis_config():
    """检查API配置文件"""
    apis_file = PROJECT_ROOT / "config" / "apis.yml"

    if not apis_file.exists():
        # 创建模板文件
        template = """# config/apis.yml
# 高德地图API配置
amap:
  weather_api_key: "your_amap_weather_key"
  map_api_key: "your_amap_map_key"

# 千问大模型API配置
qwen:
  api_key: "your_qwen_api_key"
  model_name: "qwen-turbo"
  embedding_model: "text-embedding-v1"
"""
        with open(apis_file, 'w', encoding='utf-8') as f:
            f.write(template)
        logger.warning("⚠️ 已创建 config/apis.yml 模板，请填入真实的API密钥")
        return False
    else:
        logger.info("✅ config/apis.yml 已存在")
        return True


def check_dependencies():
    """检查必要的依赖包"""
    required_packages = [
        "streamlit",
        "langchain",
        "langgraph",
        "chromadb",
        "pyyaml"
    ]

    missing = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            logger.info(f"✅ {package} 已安装")
        except ImportError:
            missing.append(package)
            logger.warning(f"❌ {package} 未安装")

    if missing:
        print("\n请安装缺失的依赖：")
        print(f"pip install {' '.join(missing)}")
        return False

    return True


def init_chroma_placeholder():
    """
    初始化Chroma向量库（占位符）
    完整实现在阶段二
    """
    logger.info("📝 Chroma向量库初始化将在阶段二实现")
    # 创建chroma_db目录
    chroma_dir = PROJECT_ROOT / "chroma_db"
    chroma_dir.mkdir(parents=True, exist_ok=True)
    logger.info("✅ 创建Chroma数据目录")
    return True


def main():
    """主函数"""
    print("=" * 50)
    print("旅途智伴 (TravelMate) 数据初始化脚本")
    print("=" * 50)

    logger.info("开始初始化项目...")

    # 执行初始化步骤
    steps = [
        ("创建目录结构", create_directory_structure),
        ("生成示例文档", generate_sample_documents),
        ("检查依赖包", check_dependencies),
        ("检查API配置", check_apis_config),
        ("初始化Chroma目录", init_chroma_placeholder),
    ]

    all_success = True
    for step_name, step_func in steps:
        print(f"\n>>> {step_name}...")
        try:
            success = step_func()
            if not success:
                all_success = False
        except Exception as e:
            logger.error(f"{step_name} 失败: {e}")
            all_success = False

    print("\n" + "=" * 50)
    if all_success:
        logger.info("🎉 项目初始化完成！")
        print("\n下一步操作：")
        print("1. 编辑 config/apis.yml 填入API密钥")
        print("2. 运行 streamlit run app.py 启动应用")
    else:
        logger.warning("⚠️ 初始化部分完成，请根据提示补充配置")

    print("=" * 50)


if __name__ == "__main__":
    main()