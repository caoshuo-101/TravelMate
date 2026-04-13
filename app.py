# app.py
import streamlit as st
import time
from datetime import datetime
from agent.graph import travel_graph
from agent.state import create_initial_state
from utils.logger import get_logger
from config.settings import settings

logger = get_logger("app")


def init_session_state():
    """初始化Streamlit会话状态"""
    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        st.session_state.messages = []
        st.session_state.current_mode = "planning"
        st.session_state.user_preferences = {
            "pacing": "moderate",
            "budget": "moderate",
            "interests": []
        }
        # 确保使用正确的初始状态
        initial_state = create_initial_state()
        initial_state["messages"] = []
        st.session_state.agent_state = initial_state
        st.session_state.current_itinerary = None
        st.session_state.last_saved_id = None
        st.session_state.streaming = False
        logger.info("应用会话已初始化")


def process_user_input(user_input: str) -> str:
    """处理用户输入，调用Agent"""
    try:
        # 更新Agent状态
        st.session_state.agent_state["user_input"] = user_input
        st.session_state.agent_state["messages"] = st.session_state.messages
        st.session_state.agent_state["user_preferences"] = st.session_state.user_preferences
        st.session_state.agent_state["iteration"] += 1
        st.session_state.agent_state["timestamp"] = datetime.now().isoformat()
        st.session_state.agent_state["next_action"] = ""
        st.session_state.agent_state["response"] = ""
        st.session_state.agent_state["tool_results"] = {}

        # 调用LangGraph
        logger.info(f"处理用户输入: {user_input}")
        result = travel_graph.invoke(
            st.session_state.agent_state,
            {"recursion_limit": 50}
        )

        # 更新状态
        st.session_state.agent_state = result
        st.session_state.current_mode = result.get("current_mode", "planning")

        # 获取响应
        response = result.get("response", "抱歉，我无法处理这个请求。")

        # 如果有行程，更新到session
        if result.get("current_itinerary"):
            old_version = st.session_state.current_itinerary.get("version",
                                                                 0) if st.session_state.current_itinerary else 0
            new_version = result["current_itinerary"].get("version", 0)
            st.session_state.current_itinerary = result["current_itinerary"]
            logger.info(f"行程已更新: v{old_version} -> v{new_version}")

            # 调试：打印行程预览
            content = result["current_itinerary"].get("content", "")
            if '| 第1天 |' in content:
                for line in content.split('\n'):
                    if '| 第1天 |' in line:
                        logger.info(f"第1天行程预览: {line}")
                        break

        # 如果有工具结果中的保存/导出信息
        tool_results = result.get("tool_results", {})
        if "save" in tool_results and tool_results["save"].get("status") == "success":
            st.session_state.last_saved_id = tool_results["save"].get("itinerary_id")

        logger.info(f"Agent响应: {response[:100]}...")
        return response

    except Exception as e:
        logger.error(f"Agent处理失败: {e}")
        return f"抱歉，处理您的请求时出现错误：{str(e)}"


def process_user_input_streaming(user_input: str):
    """流式处理用户输入"""
    try:
        # 更新Agent状态
        st.session_state.agent_state["user_input"] = user_input
        st.session_state.agent_state["messages"] = st.session_state.messages
        st.session_state.agent_state["user_preferences"] = st.session_state.user_preferences
        st.session_state.agent_state["iteration"] += 1
        st.session_state.agent_state["timestamp"] = datetime.now().isoformat()
        st.session_state.agent_state["next_action"] = ""
        st.session_state.agent_state["response"] = ""
        st.session_state.agent_state["tool_results"] = {}

        # 调用LangGraph
        logger.info(f"流式处理用户输入: {user_input}")
        result = travel_graph.invoke(
            st.session_state.agent_state,
            {"recursion_limit": 50}
        )

        # 更新状态
        st.session_state.agent_state = result
        st.session_state.current_mode = result.get("current_mode", "planning")

        # 获取响应
        response = result.get("response", "抱歉，我无法处理这个请求。")

        # 如果有行程，更新到session
        if result.get("current_itinerary"):
            st.session_state.current_itinerary = result["current_itinerary"]

        # 流式输出
        for i in range(0, len(response), 5):
            yield response[i:i + 5]
            time.sleep(0.03)

    except Exception as e:
        logger.error(f"Agent处理失败: {e}")
        yield f"抱歉，处理您的请求时出现错误：{str(e)}"


def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.title("✈️ 旅途智伴")
        st.markdown("### TravelMate")
        st.markdown("---")

        # 显示当前状态
        st.subheader("📊 当前状态")
        mode_display = {
            "planning": "📝 规划模式",
            "modifying": "✏️ 修改模式",
            "qa": "💬 问答模式"
        }
        current_mode = st.session_state.get("current_mode", "planning")
        st.info(mode_display.get(current_mode, current_mode))

        # 显示当前行程概览
        if st.session_state.get("current_itinerary"):
            st.markdown("---")
            st.subheader("📋 当前行程")
            itinerary = st.session_state.current_itinerary
            st.caption(f"📍 目的地: {itinerary.get('city', '未设置')}")
            st.caption(f"📅 天数: {itinerary.get('days', 3)}天")
            st.caption(f"🔖 版本: v{itinerary.get('version', 1)}")

            # 显示行程预览
            content = itinerary.get('content', '')
            if '| 第1天 |' in content:
                lines = content.split('\n')
                for line in lines:
                    if '| 第1天 |' in line:
                        st.caption(f"📌 第1天预览: {line}")
                        break

            # 操作按钮
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 保存行程", use_container_width=True, key="save_btn"):
                    from tools.itinerary import save_itinerary_func
                    current_itinerary = st.session_state.current_itinerary
                    if current_itinerary:
                        result = save_itinerary_func(current_itinerary)
                        if result["status"] == "success":
                            st.success(result["message"])
                            st.session_state.last_saved_id = result["itinerary_id"]
                        else:
                            st.error(result["message"])
                    else:
                        st.warning("没有可保存的行程")
            with col2:
                if st.button("📄 导出报告", use_container_width=True, key="export_btn"):
                    from tools.itinerary import save_itinerary_func, export_itinerary_func
                    current_itinerary = st.session_state.current_itinerary
                    if current_itinerary:
                        save_result = save_itinerary_func(current_itinerary)
                        if save_result["status"] == "success":
                            export_result = export_itinerary_func(save_result["itinerary_id"])
                            if export_result["status"] == "success":
                                st.success(f"报告已导出：{export_result['file_path']}")
                                try:
                                    with open(export_result['file_path'], 'r', encoding='utf-8') as f:
                                        file_content = f.read()
                                    st.download_button(
                                        label="📥 点击下载报告",
                                        data=file_content,
                                        file_name=f"{current_itinerary.get('city', '行程')}_行程规划.md",
                                        mime="text/markdown",
                                        key="download_btn"
                                    )
                                except Exception as e:
                                    st.error(f"读取文件失败: {e}")
                            else:
                                st.error(export_result["message"])
                        else:
                            st.error(save_result["message"])
                    else:
                        st.warning("没有可导出的行程")

        # 用户偏好设置
        st.markdown("---")
        st.subheader("⚙️ 偏好设置")

        pacing = st.select_slider(
            "旅行节奏",
            options=["relaxed", "moderate", "intensive"],
            format_func=lambda x: {"relaxed": "🐢 悠闲", "moderate": "👍 适中", "intensive": "🐇 紧凑"}[x],
            value=st.session_state.user_preferences.get("pacing", "moderate")
        )

        budget = st.selectbox(
            "预算",
            options=["budget", "moderate", "luxury"],
            format_func=lambda x: {"budget": "💰 经济", "moderate": "💵 适中", "luxury": "💎 豪华"}[x],
            index=["budget", "moderate", "luxury"].index(st.session_state.user_preferences.get("budget", "moderate"))
        )

        interests = st.multiselect(
            "兴趣偏好",
            options=["history", "nature", "art", "food", "shopping"],
            format_func=lambda x: {"history": "🏛️ 历史", "nature": "🌿 自然", "art": "🎨 艺术",
                                   "food": "🍜 美食", "shopping": "🛍️ 购物"}[x],
            default=st.session_state.user_preferences.get("interests", [])
        )

        if st.button("💾 保存偏好设置", use_container_width=True):
            st.session_state.user_preferences = {
                "pacing": pacing,
                "budget": budget,
                "interests": interests
            }
            st.success("偏好已保存！")

        # 功能按钮
        st.markdown("---")
        if st.button("🔄 清空对话", use_container_width=True):
            st.session_state.messages = []
            st.session_state.agent_state = create_initial_state()
            st.session_state.current_itinerary = None
            st.session_state.last_saved_id = None
            st.rerun()

        # 查看已保存的行程
        st.markdown("---")
        with st.expander("📚 已保存的行程"):
            from tools.itinerary import list_saved_itineraries_func
            saved = list_saved_itineraries_func()
            if saved:
                for it in saved[:5]:
                    st.caption(f"📌 {it['name']}")
                    st.caption(f"   ID: `{it['id']}`")
                    st.caption(f"   {it['created_at']}")
                    st.divider()
            else:
                st.caption("暂无已保存的行程")


def render_main_chat():
    """渲染主聊天界面"""
    st.title("旅途智伴 TravelMate")
    st.caption("你的智能旅行规划助手 | 基于 LangGraph + RAG | 支持流式响应")

    # 显示对话历史
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 输入框
    if prompt := st.chat_input("输入你的旅行需求，例如：帮我规划一个北京三日游..."):
        # 添加用户消息
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 生成助手回复（流式）
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_response = ""

            try:
                # 使用流式处理
                for chunk in process_user_input_streaming(prompt):
                    full_response += chunk
                    placeholder.markdown(full_response + "▌")

                placeholder.markdown(full_response)

            except Exception as e:
                logger.error(f"流式响应失败: {e}")
                # 回退到普通处理
                response = process_user_input(prompt)
                placeholder.markdown(response)
                full_response = response

        # 添加助手消息
        st.session_state.messages.append({"role": "assistant", "content": full_response})


def main():
    """应用主入口"""
    st.set_page_config(
        page_title="旅途智伴 TravelMate",
        page_icon="✈️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 验证配置
    validation_results = settings.validate()
    if not validation_results.get("qwen_api_key", False):
        st.warning("⚠️ 请先配置 config/apis.yml 中的 qwen.api_key")

    # 初始化会话
    init_session_state()

    # 渲染界面
    render_sidebar()
    render_main_chat()

    # 页脚
    st.markdown("---")
    st.caption("旅途智伴 TravelMate | 智能旅行规划助手 | 基于 LangGraph + RAG")


if __name__ == "__main__":
    main()