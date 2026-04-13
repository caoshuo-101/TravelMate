# 旅途智伴 (TravelMate) - README.md

# ✈️ 旅途智伴 (TravelMate)

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)

[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)

[![LangChain](https://img.shields.io/badge/LangChain-0.1+-green.svg)](https://www.langchain.com/)

[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 基于 LangChain + LangGraph + RAG 的智能旅行规划助手

旅途智伴是一个智能旅行规划助手，具备检索增强生成（RAG）、多工具调用、状态化多轮对话与知识库自学习能力，为用户提供个性化、可交互、可扩展的旅行规划体验。

## ## ✨ 核心功能

|功能模块|描述|
|---|---|
|🧠 **RAG知识库检索**|从本地文档中检索景点、餐厅、攻略信息，支持向量检索与相似度匹配|
|🔧 **Agent工具集**|天气查询、交通耗时计算、景点搜索、用户偏好管理、行程保存导出|
|💬 **状态机对话**|基于LangGraph的多轮交互，支持行程规划、修改、问答、报告导出|
|📚 **后台学习**|自动识别未录入城市，异步学习并补充到知识库|
|🗺️ **流式响应**|打字机效果，提升用户体验|
## ## 🏗️ 系统架构

TravelMate/

├── app.py # Streamlit 前端入口

├── agent/ # Agent核心模块（LangGraph状态图）

├── tools/ # 工具集模块（天气、交通、景点、偏好、行程）

├── rag/ # RAG检索增强模块（向量存储、检索服务）

├── model/ # 模型工厂模块（千问Chat/Embedding）

├── config/ # 配置模块（API密钥、提示词、系统配置）

├── data/ # 知识库原始数据（按城市分类）

├── scripts/ # 脚本工具（初始化、测试、学习管理）

├── utils/ # 通用工具（日志、配置加载、校验）

└── logs/ # 系统日志存储

## ## 🚀 快速开始

### ### 1. 环境要求

- Python 3.10+

- pip 20.0+

### ### 2. 安装依赖

```bash
# 克隆项目
git clone https://github.com/caoshuo-101/TravelMate.git
cd TravelMate

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

### ### 3. 配置API密钥

创建 config/apis.yml 文件（请勿提交到Git）：

```yaml
# config/apis.yml
amap:
  weather_api_key: "your_amap_weather_key"  # 高德天气API密钥
  map_api_key: "your_amap_map_key"          # 高德地图API密钥

qwen:
  api_key: "your_qwen_api_key"              # 千问API密钥
  model_name: "qwen-turbo"                  # 模型名称
  embedding_model: "text-embedding-v1"      # 嵌入模型
```

### ### 4. 初始化知识库

```bash
# 创建目录结构并生成示例文档
python scripts/setup_data.py

# 初始化向量数据库
python scripts/init_vector_db.py
```

### ### 5. 启动应用

```bash
streamlit run app.py
```

访问 http://localhost:8501 开始使用。

## ## 📖 使用示例

### ### 基础对话

|用户输入|系统响应|
|---|---|
|你好|友好问候，介绍功能|
|北京天气怎么样|返回实时天气和预报|
|北京有什么好玩的|推荐景点和美食|
### ### 行程规划

|用户输入|系统响应|
|---|---|
|帮我规划一个北京三日游|生成详细行程（含景点、餐饮、贴士）|
|我喜欢安静的地方|调整偏好，重新规划|
|把第一天的故宫改成颐和园|智能修改行程|
|保存这个行程|保存到本地|
|导出行程报告|导出Markdown格式报告|
### ### 未知城市自动学习

|用户输入|系统行为|
|---|---|
|介绍长沙|LLM生成信息 + 后台异步学习|
|长沙景点推荐|从知识库检索（学习完成后）|
## ## 🛠️ 工具脚本

|脚本|功能|
|---|---|
|python scripts/setup_data.py|创建目录结构、生成示例文档|
|python scripts/init_vector_db.py|初始化向量数据库|
|python scripts/test_rag.py|测试RAG检索功能|
|python scripts/manage_learning.py --status|查看后台学习状态|
|python scripts/manage_learning.py --learn 成都|手动学习指定城市|
|python scripts/sync_learn.py 昆明|同步学习（调试用）|
## ## 📋 技术栈

|组件|技术|
|---|---|
|大语言模型|千问 (Qwen)|
|嵌入模型|text-embedding-v1|
|向量数据库|Chroma|
|地图/天气API|高德地图API|
|Agent框架|LangGraph|
|前端框架|Streamlit|
## ## 🔧 配置说明

### ### 系统配置 (config/settings.py)

|参数|默认值|说明|
|---|---|---|
|AGENT_MAX_ITERATIONS|10|Agent最大迭代次数|
|AGENT_TIMEOUT|60|LLM调用超时（秒）|
|RETRIEVAL_TOP_K|5|检索返回文档数|
|RETRIEVAL_SCORE_THRESHOLD|0.3|相似度阈值|
### ### 提示词配置 (config/prompts.py)

集中管理所有LLM提示词模板，支持：

- 系统角色提示词

- 行程规划提示词

- 行程修改提示词

- 未知城市生成提示词

- 问答提示词

## ## 🧪 测试

```bash
# 运行所有测试
python scripts/test_rag.py

# 快速功能测试
python scripts/quick_test.py

# 检索功能测试
python scripts/test_retrieval.py
```

## ## 📁 数据目录结构

data/

├── 北京/

│   ├── attractions.md    # 景点信息

│   ├── restaurants.md    # 美食信息

│   └── guide.txt         # 攻略信息

├── 上海/

│   └── ...

└── 昆明/                  # 自动学习生成


