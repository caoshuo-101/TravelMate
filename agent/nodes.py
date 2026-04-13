# agent/nodes.py
import copy
import re
from typing import Dict, Any
from agent.state import TravelState, ConversationMode
from rag.retriever import RetrievalService
from model.chat_model import ChatModelWrapper
from utils.logger import get_logger

logger = get_logger("agent_nodes")

# 初始化服务
retriever = RetrievalService()
chat_model = ChatModelWrapper()


def router_node(state: TravelState) -> TravelState:
    """路由节点：分析用户意图，检测未知城市"""
    logger.info(f"路由节点")

    new_state = copy.deepcopy(state)
    user_input = new_state.get("user_input", "")
    user_input_lower = user_input.lower()

    # 已知城市列表
    known_cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "西安", "南京",
                    "重庆", "武汉", "苏州", "长沙", "青岛", "厦门", "三亚", "丽江",
                    "大理", "桂林", "张家界", "敦煌", "拉萨", "乌鲁木齐", "昆明"]

    import re

    # 提取可能的地名 - 修复：排除虚词
    city_patterns = [
        (r'介绍([\u4e00-\u9fa5]{2,3})(?![的]|[了]|[和]|[与])', 1),
        (r'推荐([\u4e00-\u9fa5]{2,3})(?![的]|[了]|[和]|[与])', 1),
        (r'([\u4e00-\u9fa5]{2,3})景点', 1),
        (r'([\u4e00-\u9fa5]{2,3})旅游', 1),
        (r'([\u4e00-\u9fa5]{2,3})美食', 1),
        (r'去([\u4e00-\u9fa5]{2,3})(?![的]|[了]|[和]|[与])', 1),
        (r'([\u4e00-\u9fa5]{2,3})有什么', 1),
        (r'([\u4e00-\u9fa5]{2,3})好玩', 1),
    ]

    potential_city = None
    for pattern, _ in city_patterns:
        match = re.search(pattern, user_input)
        if match:
            potential_city = match.group(1)
            # 排除常见非城市词
            exclude_words = ["什么", "怎么", "为什么", "哪里", "哪个", "多少", "如何",
                             "可以", "应该", "需要", "这个", "那个", "这些", "那些",
                             "的", "了", "和", "与", "或", "等", "有", "是", "在"]
            if potential_city not in exclude_words and len(potential_city) >= 2:
                # 去掉结尾的"的"
                if potential_city.endswith("的"):
                    potential_city = potential_city[:-1]
                break
            else:
                potential_city = None

    # 如果提取到城市名且不在已知列表中
    if potential_city and potential_city not in known_cities:
        new_state["city"] = potential_city
        new_state["current_mode"] = ConversationMode.UNKNOWN_CITY.value
        new_state["next_action"] = "unknown_city"
        logger.info(f"检测到未知城市: {potential_city} (来自模式匹配)")
        return new_state

    # 2. 检查是否直接询问某个已知城市的信息
    for city in known_cities:
        if city in user_input:
            new_state["city"] = city
            logger.info(f"检测到已知城市: {city}")
            break

    # 3. 正常意图识别
    if "规划" in user_input or "行程" in user_input:
        if "修改" in user_input or "调整" in user_input:
            new_state["current_mode"] = ConversationMode.MODIFYING.value
            new_state["next_action"] = "modify"
        else:
            new_state["current_mode"] = ConversationMode.PLANNING.value
            new_state["next_action"] = "plan"
    elif "天气" in user_input:
        new_state["current_mode"] = ConversationMode.QA.value
        new_state["next_action"] = "qa"
    elif "偏好" in user_input or "喜欢" in user_input:
        new_state["current_mode"] = ConversationMode.PLANNING.value
        new_state["next_action"] = "plan"
    elif potential_city:
        # 如果提取到城市但可能已在已知列表中，走未知城市流程让系统处理
        new_state["current_mode"] = ConversationMode.UNKNOWN_CITY.value
        new_state["next_action"] = "unknown_city"
    else:
        new_state["current_mode"] = ConversationMode.QA.value
        new_state["next_action"] = "qa"

    logger.info(
        f"路由结果: mode={new_state['current_mode']}, action={new_state['next_action']}, city={new_state.get('city')}")
    return new_state


def retrieve_node(state: TravelState) -> TravelState:
    """检索节点：调用RAG服务检索相关知识"""
    logger.info(f"检索节点")

    new_state = copy.deepcopy(state)
    user_input = new_state.get("user_input", "")

    # 提取城市信息
    cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "西安", "南京", "重庆", "武汉", "苏州", "长沙"]
    for c in cities:
        if c in user_input:
            new_state["city"] = c
            break

    city = new_state.get("city")

    # 执行检索
    if city:
        results = retriever.retrieve(user_input, city=city, top_k=5)
    else:
        results = retriever.retrieve(user_input, top_k=5)

    new_state["retrieved_docs"] = results
    logger.info(f"检索完成，返回 {len(results)} 条结果")

    return new_state


def plan_node(state: TravelState) -> TravelState:
    """规划节点：生成详细行程规划"""
    logger.info(f"规划节点: 生成行程")

    new_state = copy.deepcopy(state)
    user_input = new_state.get("user_input", "")
    city = new_state.get("city", "北京")
    preferences = new_state.get("user_preferences", {}).copy()
    retrieved_docs = new_state.get("retrieved_docs", [])

    # 提取天数
    days = 3
    day_match = re.search(r'(\d+)[天日]', user_input)
    if day_match:
        days = int(day_match.group(1))
        new_state["days"] = days

    # 提取预算关键词
    budget_keywords = ["经济", "省钱", "穷游", "豪华", "奢侈", "中等"]
    budget_map = {"经济": "budget", "省钱": "budget", "穷游": "budget",
                  "豪华": "luxury", "奢侈": "luxury", "中等": "moderate"}
    for kw in budget_keywords:
        if kw in user_input:
            preferences["budget"] = budget_map.get(kw, "moderate")
            break

    # 提取节奏关键词
    pace_keywords = ["悠闲", "轻松", "慢慢", "紧凑", "快速", "打卡"]
    pace_map = {"悠闲": "relaxed", "轻松": "relaxed", "慢慢": "relaxed",
                "紧凑": "intensive", "快速": "intensive", "打卡": "intensive"}
    for kw in pace_keywords:
        if kw in user_input:
            preferences["pacing"] = pace_map.get(kw, "moderate")
            break

    # 更新偏好
    new_state["user_preferences"] = preferences

    # 构建知识库上下文
    context = ""
    if retrieved_docs:
        attractions = [doc for doc in retrieved_docs if doc.get("metadata", {}).get("type") == "attraction"]
        restaurants = [doc for doc in retrieved_docs if doc.get("metadata", {}).get("type") == "restaurant"]
        guides = [doc for doc in retrieved_docs if doc.get("metadata", {}).get("type") == "guide"]

        if attractions:
            context += "\n## 景点信息\n"
            for attr in attractions[:3]:
                context += f"- {attr.get('content', '')[:300]}\n"

        if restaurants:
            context += "\n## 美食信息\n"
            for rest in restaurants[:2]:
                context += f"- {rest.get('content', '')[:200]}\n"

        if guides:
            context += "\n## 攻略信息\n"
            for guide in guides[:1]:
                context += f"- {guide.get('content', '')[:300]}\n"

    # 偏好映射
    pacing_map = {"relaxed": "悠闲放松（每天2-3个景点，充足休息时间）",
                  "moderate": "适中节奏（每天3-4个景点）",
                  "intensive": "紧凑充实（每天5-6个景点，高效打卡）"}
    budget_map = {"budget": "经济实惠（公共交通、小吃、免费景点）",
                  "moderate": "适中（部分出租车、特色餐厅）",
                  "luxury": "豪华舒适（专车、高端餐厅、VIP体验）"}

    # 生成节奏建议文本
    pacing_value = preferences.get('pacing', 'moderate')
    budget_value = preferences.get('budget', 'moderate')

    pacing_suggestion = {
        "relaxed": "建议每天安排2-3个景点，留出充足的休息时间，可以在咖啡馆或公园小憩",
        "moderate": "建议每天安排3-4个景点，保持舒适的游览节奏",
        "intensive": "建议每天安排5-6个景点，高效利用时间，适合想要多看景点的旅行者"
    }.get(pacing_value, "建议根据当天体力情况灵活调整")

    budget_suggestion = {
        "budget": "建议优先选择公共交通、免费景点和当地小吃，提前预订可享受优惠",
        "moderate": "建议适度使用出租车，选择有特色的中档餐厅",
        "luxury": "建议选择专车服务、高端餐厅和VIP通道，享受更舒适的体验"
    }.get(budget_value, "建议根据个人需求合理安排预算")

    # 兴趣文本
    interests = preferences.get('interests', [])
    interests_text = ', '.join(interests) if interests else '观光、美食、文化'

    # 生成详细行程的提示词
    prompt = f"""你是一个专业的旅行规划助手，请为用户规划一个{days}天的{city}详细行程。

## 用户偏好
- 旅行节奏：{pacing_map.get(pacing_value, '适中节奏')}
- 预算：{budget_map.get(budget_value, '适中')}
- 兴趣：{interests_text}

## 知识库信息
{context if context else "请根据你的知识推荐该城市的经典景点和美食"}

## 输出格式要求（请严格按照以下格式）

# {city}{days}日游行程规划

## 📊 行程概览
| 日期 | 上午 | 下午 | 晚上 | 餐饮推荐 |
|------|------|------|------|----------|
| 第1天 | [景点] | [景点] | [活动] | [餐厅] |
| 第2天 | [景点] | [景点] | [活动] | [餐厅] |
| 第3天 | [景点] | [景点] | [活动] | [餐厅] |

## 📅 详细行程

### 第1天
**上午** (9:00-12:00)
- [景点名称]：[详细描述，包括游览时间、门票、小贴士]

**中午** (12:00-13:30)
- [午餐推荐]：[餐厅名称、特色菜、人均消费]

**下午** (13:30-17:00)
- [景点名称]：[详细描述]

**晚上** (17:00-20:00)
- [晚餐推荐]：[餐厅名称、特色菜]
- [夜间活动]：[夜景、演出等]

**住宿建议**：[推荐区域和酒店类型]

### 第2天
...（同上格式）

### 第3天
...（同上格式）

## 💡 实用贴士
1. **交通**：[公共交通建议、打车费用参考]
2. **门票**：[需要预约的景点、票价信息]
3. **天气**：[当前季节天气特点、穿衣建议]
4. **注意事项**：[避坑指南、安全提示]

## 🎁 个性化建议
- 根据你的{pacing_value}节奏，建议：{pacing_suggestion}
- 根据你的{budget_value}预算，建议：{budget_suggestion}

请确保行程合理、时间充裕，提供实用的旅行建议。
"""

    try:
        response = chat_model.invoke(prompt)

        # 构建结构化行程
        itinerary = {
            "city": city,
            "days": days,
            "preferences": preferences,
            "content": response,
            "generated_at": new_state.get("timestamp", ""),
            "version": 1,
            "modification_history": []
        }

        new_state["current_itinerary"] = itinerary
        new_state["response"] = response
        new_state["next_action"] = "done"
        logger.info(f"行程规划生成成功: {city}, {days}天")

    except Exception as e:
        logger.error(f"生成行程失败: {e}")
        new_state["response"] = f"抱歉，生成行程时出现错误：{str(e)}\n\n请稍后重试或更详细地描述您的需求。"
        new_state["next_action"] = "done"

    return new_state


def modify_node(state: TravelState) -> TravelState:
    """修改节点：智能修改现有行程"""
    logger.info(f"修改节点: 修改行程")

    new_state = copy.deepcopy(state)
    user_input = new_state.get("user_input", "")
    current_itinerary = new_state.get("current_itinerary")

    if not current_itinerary:
        new_state["response"] = "当前没有行程可以修改，请先让我帮你规划一个行程。例如：帮我规划一个北京三日游"
        new_state["next_action"] = "done"
        return new_state

    # 解析修改意图
    modification_type = "general"
    if "增加" in user_input or "添加" in user_input:
        modification_type = "add"
    elif "删除" in user_input or "去掉" in user_input:
        modification_type = "remove"
    elif "调整" in user_input or "改" in user_input or "换" in user_input:
        modification_type = "adjust"
    elif "第" in user_input and ("天" in user_input or "日" in user_input):
        modification_type = "day_specific"

    # 提取天数
    day_num = None
    day_match = re.search(r'第\s*(\d+)\s*[天日]', user_input)
    if day_match:
        day_num = int(day_match.group(1))

    # 提取修改前后的内容
    old_attraction = ""
    new_attraction = ""
    if "改成" in user_input:
        parts = user_input.split("改成")
        if len(parts) == 2:
            old_attraction = parts[0].replace("把", "").replace("的", "").strip()
            new_attraction = parts[1].strip()

    # 构建修改提示词
    prompt = f"""用户想要修改当前的行程规划。

## 当前行程
{current_itinerary.get('content', '无行程内容')}

## 修改需求
用户说：{user_input}
{f"将「{old_attraction}」改为「{new_attraction}」" if old_attraction and new_attraction else ""}
修改类型：{modification_type}
{f"目标天数：第{day_num}天" if day_num else ""}

## 修改要求
1. 理解用户的修改意图，精确执行修改
2. 如果用户说「把A改成B」，请将A替换为B
3. 保持行程的整体合理性
4. 保持原有的输出格式（包括表格和详细行程）

## 重要：请直接输出修改后的完整行程，保持与之前完全相同的格式。
"""

    try:
        response = chat_model.invoke(prompt)

        # 记录修改历史
        history_entry = {
            "timestamp": new_state.get("timestamp"),
            "modification": user_input,
            "modification_type": modification_type,
            "previous_version": current_itinerary.get("version", 1),
            "old_attraction": old_attraction,
            "new_attraction": new_attraction
        }

        modification_history = current_itinerary.get("modification_history", [])
        modification_history.append(history_entry)

        # 更新行程
        updated_itinerary = {
            **current_itinerary,
            "content": response,
            "version": current_itinerary.get("version", 1) + 1,
            "modification_history": modification_history,
            "last_modified": new_state.get("timestamp")
        }

        new_state["current_itinerary"] = updated_itinerary
        new_state["response"] = f"✅ 已根据您的要求修改行程：{user_input}\n\n{response}"
        new_state["next_action"] = "done"

        logger.info(f"行程修改成功: {modification_type}, 新版本: v{updated_itinerary['version']}")

    except Exception as e:
        logger.error(f"修改行程失败: {e}")
        new_state["response"] = f"抱歉，修改行程时出现错误：{str(e)}\n\n请重新描述您的修改需求。"
        new_state["next_action"] = "done"

    return new_state


def qa_node(state: TravelState) -> TravelState:
    """问答节点：回答问题"""
    logger.info(f"问答节点: 回答问题")

    new_state = copy.deepcopy(state)
    user_input = new_state.get("user_input", "")
    retrieved_docs = new_state.get("retrieved_docs", [])

    # 天气查询 - 直接调用天气工具
    if "天气" in user_input:
        city = new_state.get("city")
        if not city:
            cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "西安", "南京", "重庆", "武汉"]
            for c in cities:
                if c in user_input:
                    city = c
                    break

        if city:
            from tools.weather import query_weather_func, format_weather_info
            weather_data = query_weather_func(city)
            new_state["response"] = format_weather_info(weather_data)
            new_state["next_action"] = "done"
            return new_state
        else:
            new_state["response"] = "请告诉我您想查询哪个城市的天气？例如：北京天气怎么样"
            new_state["next_action"] = "done"
            return new_state

    # 构建知识库上下文
    context = ""
    if retrieved_docs:
        context = "\n".join([doc.get("content", "")[:500] for doc in retrieved_docs[:3]])

    # 使用 LLM 回答问题
    prompt = f"""请回答用户的问题。你是旅途智伴旅行助手。

用户问题：{user_input}

参考信息：
{context if context else "（无特定参考信息，请根据你的知识回答）"}

要求：
1. 如果是旅行相关问题，提供实用建议
2. 如果是景点查询，推荐特色景点
3. 如果是闲聊，友好回应
4. 回答要简洁有用
"""

    try:
        response = chat_model.invoke(prompt)
        new_state["response"] = response
        new_state["next_action"] = "done"

    except Exception as e:
        logger.error(f"问答失败: {e}")
        new_state[
            "response"] = f"抱歉，我暂时无法回答这个问题。请尝试问我旅行相关的问题，比如「北京有什么好玩的」或「推荐成都美食」。"
        new_state["next_action"] = "done"

    return new_state


def call_tools_node(state: TravelState) -> TravelState:
    """工具调用节点：执行工具调用（增强版）"""
    logger.info(f"工具调用节点")

    new_state = copy.deepcopy(state)
    user_input = new_state.get("user_input", "")
    tool_results = new_state.get("tool_results", {}).copy()
    current_itinerary = new_state.get("current_itinerary")

    # 1. 天气查询
    if "天气" in user_input:
        city = new_state.get("city")
        if city:
            logger.info(f"调用天气工具: {city}")
            from tools.weather import query_weather_func
            result = query_weather_func(city)
            tool_results["weather"] = result
            new_state["tool_results"] = tool_results
            new_state["next_action"] = "generate_response"
            return new_state

    # 2. 保存行程
    if "保存" in user_input and current_itinerary:
        logger.info(f"调用保存行程工具")
        from tools.itinerary import save_itinerary_func
        result = save_itinerary_func(current_itinerary)
        tool_results["save"] = result
        new_state["tool_results"] = tool_results
        new_state["response"] = result.get("message", "行程已保存")
        new_state["next_action"] = "done"
        return new_state

    # 3. 导出行程
    if "导出" in user_input or "报告" in user_input:
        if current_itinerary:
            from tools.itinerary import save_itinerary_func, export_itinerary_func
            save_result = save_itinerary_func(current_itinerary)
            if save_result.get("status") == "success":
                export_result = export_itinerary_func(save_result["itinerary_id"])
                tool_results["export"] = export_result
                new_state["tool_results"] = tool_results
                new_state["response"] = export_result.get("message", "行程报告已生成")
                new_state["next_action"] = "done"
                return new_state

    # 4. 景点搜索
    if any(kw in user_input for kw in ["景点", "好玩", "美食", "吃", "推荐"]):
        city = new_state.get("city")
        if city:
            logger.info(f"调用景点搜索工具: {city}")
            from tools.attraction import search_attractions_func
            result = search_attractions_func(city)
            tool_results["attractions"] = result
            new_state["tool_results"] = tool_results

    # 5. 偏好更新
    if any(kw in user_input for kw in ["喜欢", "偏好", "安静", "热闹", "经济", "豪华"]):
        logger.info(f"调用偏好管理工具")
        preferences = new_state.get("user_preferences", {}).copy()

        if "安静" in user_input or "悠闲" in user_input:
            preferences["pacing"] = "relaxed"
            tool_results["preference"] = {"status": "success", "message": "已将节奏调整为悠闲模式"}
        elif "紧凑" in user_input or "高效" in user_input:
            preferences["pacing"] = "intensive"
            tool_results["preference"] = {"status": "success", "message": "已将节奏调整为紧凑模式"}

        if "经济" in user_input or "省钱" in user_input:
            preferences["budget"] = "budget"
            tool_results["preference"] = {"status": "success", "message": "已调整为经济预算模式"}
        elif "豪华" in user_input or "奢侈" in user_input:
            preferences["budget"] = "luxury"
            tool_results["preference"] = {"status": "success", "message": "已调整为豪华预算模式"}

        if "历史" in user_input:
            interests = preferences.get("interests", [])
            if "history" not in interests:
                interests.append("history")
                preferences["interests"] = interests
                tool_results["preference"] = {"status": "success", "message": "已添加历史兴趣"}
        elif "美食" in user_input:
            interests = preferences.get("interests", [])
            if "food" not in interests:
                interests.append("food")
                preferences["interests"] = interests
                tool_results["preference"] = {"status": "success", "message": "已添加美食兴趣"}

        new_state["user_preferences"] = preferences
        new_state["tool_results"] = tool_results

    new_state["next_action"] = "done"
    logger.info(f"工具调用完成，结果: {list(tool_results.keys())}")

    return new_state


def generate_response_node(state: TravelState) -> TravelState:
    """生成回复节点：根据状态生成真正的回复"""
    logger.info(f"生成回复节点")

    new_state = copy.deepcopy(state)

    # 如果已经有响应，直接返回
    if new_state.get("response") and new_state["response"] != "收到您的需求，我正在处理中...":
        return new_state

    user_input = new_state.get("user_input", "")
    current_mode = new_state.get("current_mode", "")
    tool_results = new_state.get("tool_results", {})
    retrieved_docs = new_state.get("retrieved_docs", [])

    # 1. 如果有工具结果，优先使用工具结果生成回复
    if "weather" in tool_results:
        from tools.weather import format_weather_info
        new_state["response"] = format_weather_info(tool_results["weather"])
        return new_state

    if "save" in tool_results:
        new_state["response"] = tool_results["save"].get("message", "行程已保存")
        return new_state

    if "export" in tool_results:
        new_state["response"] = tool_results["export"].get("message", "行程报告已生成")
        return new_state

    # 2. 如果是规划模式，调用 plan_node 生成行程
    if current_mode == "planning" or "规划" in user_input or "行程" in user_input:
        return plan_node(state)

    # 3. 如果是修改模式，调用 modify_node 修改行程
    if current_mode == "modifying" or "修改" in user_input or "调整" in user_input:
        if new_state.get("current_itinerary"):
            return modify_node(state)
        else:
            new_state["response"] = "当前没有行程可以修改，请先让我帮你规划一个行程。"
            return new_state

    # 4. 如果是问答模式，调用 qa_node 回答问题
    if current_mode == "qa" or "?" in user_input or "什么" in user_input or "怎么" in user_input:
        return qa_node(state)

    # 5. 默认：使用 LLM 生成通用回复
    try:
        context = ""
        if retrieved_docs:
            context = "\n".join([doc.get("content", "")[:300] for doc in retrieved_docs[:2]])

        prompt = f"""用户说：{user_input}

参考信息：
{context}

请根据用户输入生成友好的回复。如果是问候，友好回应；如果是问题，尽力回答；如果是闲聊，自然对话。
你是旅途智伴旅行助手，专注于帮助用户规划旅行。
"""
        response = chat_model.invoke(prompt)
        new_state["response"] = response

    except Exception as e:
        logger.error(f"生成回复失败: {e}")
        new_state["response"] = f"您好！我是旅途智伴旅行助手。您可以说「帮我规划北京三日游」或「北京天气怎么样」来开始体验。"

    new_state["next_action"] = "done"
    return new_state


# agent/nodes.py - 完整的 unknown_city_node

def unknown_city_node(state: TravelState) -> TravelState:
    """未知城市处理节点：先检查知识库，没有再生成并后台学习"""
    logger.info(f"未知城市节点")

    new_state = copy.deepcopy(state)
    user_input = new_state.get("user_input", "")
    city = new_state.get("city", "")

    # 如果没有提取到城市，尝试从用户输入中提取
    if not city:
        import re
        # 修复：排除"的"、"了"等虚词
        patterns = [
            (r'介绍([\u4e00-\u9fa5]{2,3})(?![的]|[了]|[和]|[与])', 1),
            (r'推荐([\u4e00-\u9fa5]{2,3})(?![的]|[了]|[和]|[与])', 1),
            (r'([\u4e00-\u9fa5]{2,3})景点', 1),
            (r'([\u4e00-\u9fa5]{2,3})美食', 1),
            (r'([\u4e00-\u9fa5]{2,3})旅游', 1),
            (r'去([\u4e00-\u9fa5]{2,3})(?![的]|[了]|[和]|[与])', 1),
            (r'([\u4e00-\u9fa5]{2,3})有什么', 1),
            (r'([\u4e00-\u9fa5]{2,3})好玩', 1),
            (r'([\u4e00-\u9fa5]{2,3})攻略', 1),
        ]

        # 已知城市白名单
        known_cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "西安", "南京",
                        "重庆", "武汉", "苏州", "长沙", "青岛", "厦门", "三亚", "丽江",
                        "大理", "桂林", "张家界", "敦煌", "拉萨", "乌鲁木齐", "昆明"]

        for pattern, _ in patterns:
            match = re.search(pattern, user_input)
            if match:
                potential_city = match.group(1)
                # 排除虚词和单字
                exclude_words = ["什么", "怎么", "为什么", "哪里", "哪个", "多少", "如何",
                                 "可以", "应该", "需要", "这个", "那个", "这些", "那些",
                                 "的", "了", "和", "与", "或", "等", "有", "是", "在"]
                if potential_city not in exclude_words and len(potential_city) >= 2:
                    # 如果城市名以"的"结尾，去掉
                    if potential_city.endswith("的"):
                        potential_city = potential_city[:-1]
                    city = potential_city
                    new_state["city"] = city
                    logger.info(f"从模式匹配提取到城市: {city}")
                    break

    if not city:
        new_state["response"] = "请告诉我您想了解哪个城市的信息？例如：介绍一下长沙、成都景点推荐"
        new_state["next_action"] = "done"
        return new_state

    # 检查知识库中是否已有该城市信息
    from rag.retriever import RetrievalService
    retriever = RetrievalService()

    # 尝试多种查询方式检索
    existing = retriever.retrieve(city, city=city, top_k=3)

    # 如果没找到，尝试更具体的查询
    if not existing:
        logger.info(f"尝试扩展查询: {city}旅行指南")
        existing = retriever.retrieve(f"{city}旅行指南", city=city, top_k=3)

    if not existing:
        logger.info(f"尝试扩展查询: {city}景点推荐")
        existing = retriever.retrieve(f"{city}景点推荐", city=city, top_k=3)

    if not existing:
        logger.info(f"尝试扩展查询: {city}城市介绍")
        existing = retriever.retrieve(f"{city}城市介绍", city=city, top_k=3)

    # 检查是否有该城市的文档
    has_city_data = False
    city_docs = []
    for doc in existing:
        metadata = doc.get("metadata", {})
        if metadata.get("city") == city:
            has_city_data = True
            city_docs.append(doc)
            logger.info(f"找到{city}的文档，相似度: {doc.get('similarity', 0)}")

    # 如果知识库中已有数据，直接返回
    if has_city_data and city_docs:
        logger.info(f"城市 {city} 已在知识库中，直接返回")

        # 合并内容
        content_parts = []
        for doc in city_docs[:2]:
            content = doc.get("content", "")
            if content:
                content_parts.append(content)

        context = "\n\n".join(content_parts)

        # 根据用户问题类型定制回复
        if "美食" in user_input:
            # 提取美食相关部分
            if "美食" in context or "吃" in context:
                response = f"关于{city}的美食推荐：\n\n"
                # 简单提取包含美食的行
                lines = context.split('\n')
                for line in lines:
                    if any(kw in line for kw in ["美食", "吃", "餐厅", "小吃", "口味"]):
                        response += line + "\n"
                if len(response) < 50:
                    response = f"关于{city}的美食信息：\n\n{context[:500]}"
            else:
                response = f"关于{city}的旅行信息：\n\n{context[:800]}"
        elif "景点" in user_input:
            response = f"关于{city}的景点推荐：\n\n{context[:800]}"
        else:
            response = f"关于{city}的旅行信息：\n\n{context[:800]}"

        response += "\n\n如需更详细的信息，请继续提问。"
        new_state["response"] = response
        new_state["next_action"] = "done"
        return new_state

    # 知识库中没有，使用LLM生成
    logger.info(f"知识库中无{city}数据，使用LLM生成")

    # 根据用户问题类型定制生成提示词
    if "美食" in user_input:
        prompt = f"""请为用户详细介绍【{city}】的特色美食。

用户问题：{user_input}

请提供：
1. 城市美食文化简介
2. 必吃特色美食（3-5个，每个附简短描述和推荐餐厅）
3. 美食街区推荐
4. 小吃推荐
5. 饮食注意事项

请用友好的语气回复，让旅行者能轻松找到美食。
"""
    elif "景点" in user_input:
        prompt = f"""请为用户详细介绍【{city}】的必去景点。

用户问题：{user_input}

请提供：
1. 城市简介
2. 必去景点（3-5个，每个附简短描述、游玩时间、门票参考）
3. 小众景点推荐（1-2个）
4. 景点分布及交通建议

请用友好的语气回复，让旅行者能轻松规划行程。
"""
    else:
        prompt = f"""请为用户详细介绍【{city}】的旅行信息。

用户问题：{user_input}

请提供：
1. 城市简介（100字左右）
2. 必去景点（3-5个，每个附简短描述）
3. 特色美食（2-3个）
4. 最佳旅行季节
5. 建议游玩天数
6. 实用小贴士

请用友好的语气回复，格式清晰易读。
"""

    try:
        response = chat_model.invoke(prompt)

        # 触发后台学习
        from rag.background_learner import get_background_learner
        learner = get_background_learner()
        learner.submit_learning_task(city, user_input)

        new_state["response"] = response + f"\n\n---\n📚 *关于{city}的详细信息正在后台学习中，下次查询将更全面！*"
        logger.info(f"已触发{city}的后台学习")

    except Exception as e:
        logger.error(f"未知城市处理失败: {e}")
        new_state["response"] = f"抱歉，获取{city}信息时出现错误：{str(e)}\n\n请稍后重试或询问其他城市。"

    new_state["next_action"] = "done"
    return new_state