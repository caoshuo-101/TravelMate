# agent/graph.py (完整修复版)
from langgraph.graph import StateGraph, END
from agent.state import TravelState, ConversationMode
from agent.nodes import (
    router_node, retrieve_node, plan_node, modify_node,
    qa_node, call_tools_node, generate_response_node, unknown_city_node
)
from utils.logger import get_logger

logger = get_logger("agent_graph")


def build_travel_graph():
    """构建旅行规划Agent的状态图"""
    logger.info("构建旅行规划状态图")

    workflow = StateGraph(TravelState)

    # 添加节点
    workflow.add_node("router", router_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("plan", plan_node)
    workflow.add_node("modify", modify_node)
    workflow.add_node("qa", qa_node)
    workflow.add_node("call_tools", call_tools_node)
    workflow.add_node("unknown_city", unknown_city_node)
    workflow.add_node("generate_response", generate_response_node)

    workflow.set_entry_point("router")

    # agent/graph.py - 确保有到 unknown_city 的路由

    def route_after_router(state: TravelState) -> str:
        action = state.get("next_action", "")
        current_mode = state.get("current_mode", "")

        # 优先检查未知城市模式
        if current_mode == ConversationMode.UNKNOWN_CITY.value or action == "unknown_city":
            return "unknown_city"
        elif action == "plan":
            return "retrieve"
        elif action == "modify":
            return "modify"
        else:
            return "retrieve"

    def route_after_retrieve(state: TravelState) -> str:
        return "call_tools"

    def route_after_tools(state: TravelState) -> str:
        current_mode = state.get("current_mode", "")
        user_input = state.get("user_input", "")
        tool_results = state.get("tool_results", {})

        # 优先使用工具结果
        if tool_results:
            return "generate_response"

        # 根据模式路由
        if current_mode == "planning" or "规划" in user_input:
            return "plan"
        elif "天气" in user_input or "?" in user_input:
            return "qa"
        else:
            return "generate_response"

    workflow.add_conditional_edges("router", route_after_router)
    workflow.add_edge("retrieve", "call_tools")
    workflow.add_conditional_edges("call_tools", route_after_tools)
    workflow.add_edge("plan", "generate_response")
    workflow.add_edge("modify", "generate_response")
    workflow.add_edge("qa", "generate_response")
    workflow.add_edge("unknown_city", "generate_response")
    workflow.add_edge("generate_response", END)

    app = workflow.compile()
    logger.info("状态图构建完成")
    return app


travel_graph = build_travel_graph()