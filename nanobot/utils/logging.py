"""通用日志工具"""

import sys
import json
import logging
import inspect
from pathlib import Path
from typing import Any
from loguru import logger


def setup_logging(verbose: bool = False, log_dir: Path | None = None) -> Path:
    """
    配置日志系统（loguru + standard logging）
    
    Args:
        verbose: 是否启用详细日志（DEBUG 级别）
        log_dir: 日志目录，默认为 ~/.nanobot/logs
    
    Returns:
        日志文件路径
    """
    # 确定日志目录和文件
    if log_dir is None:
        log_dir = Path.home() / ".nanobot" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "nanobot.log"
    
    # 确定日志级别
    log_level = "DEBUG" if verbose else "INFO"
    
    # 移除 loguru 默认 handler
    logger.remove()
    
    # 添加控制台 handler（带颜色）
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True,
    )
    
    # 添加文件 handler（无颜色，带轮转）
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        level=log_level,
        rotation="10 MB",
        retention="7 days",
        compression="zip",
    )
    
    # 配置标准 logging 模块（用于第三方库）
    # 使用 loguru 的 intercept handler，让所有日志都通过 loguru 处理
    _setup_standard_logging_intercept(verbose)
    
    logger.info(f"Logging to: {log_file}")
    return log_file


def _setup_standard_logging_intercept(verbose: bool) -> None:
    """
    配置标准 logging 模块，将日志重定向到 loguru
    
    Args:
        verbose: 是否启用详细日志
    """
    import logging
    
    # 确定日志级别
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # 创建一个 handler，将 logging 的日志重定向到 loguru
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            # 获取对应的 loguru level
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
            
            # 直接使用 record 中的信息，不要尝试追踪调用栈
            # 这样可以保留原始的模块、函数和行号信息
            logger.patch(lambda r: r.update(
                name=record.name,
                function=record.funcName,
                line=record.lineno
            )).log(level, record.getMessage())
    
    # 配置 root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(InterceptHandler())
    root_logger.setLevel(log_level)
    
    # 为第三方库设置日志级别
    third_party_libs = [
        "LiteLLM",
        "httpx", 
        "httpcore", 
        "openai", 
        "urllib3",
        "asyncio",
        "websockets",
        "Lark"  # 飞书 SDK
    ]
    
    for lib_name in third_party_libs:
        lib_logger = logging.getLogger(lib_name)
        lib_logger.setLevel(log_level)
        lib_logger.handlers.clear()
        lib_logger.propagate = True


def log_llm_request(
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    api_base: str | None = None,
    depth: int = 1
) -> None:
    """
    记录 LLM 请求日志
    
    Args:
        model: 模型名称
        messages: 消息列表
        tools: 工具定义列表
        temperature: 温度参数
        max_tokens: 最大 token 数
        api_base: API 基础地址
        depth: 调用栈深度，用于获取正确的调用者信息
    """
    # 获取调用者信息
    frame = inspect.currentframe()
    for _ in range(depth):
        if frame and frame.f_back:
            frame = frame.f_back
    
    caller_info = {}
    if frame:
        caller_info = {
            "name": frame.f_code.co_filename,
            "function": frame.f_code.co_name,
            "line": frame.f_lineno
        }
    
    # 使用 opt 方法绑定调用者信息
    log = logger.opt(depth=depth)
    
    log.info("=" * 80)
    log.info("📤 LLM REQUEST")
    log.info("=" * 80)
    log.info(f"Model: {model}")
    log.info(f"Temperature: {temperature}")
    log.info(f"Max Tokens: {max_tokens}")
    if api_base:
        log.info(f"API Base: {api_base}")
    
    log.info("\n📝 Messages:")
    for i, msg in enumerate(messages):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        
        # 对于 system message，完整记录到日志文件
        if role == "system" and isinstance(content, str):
            # 检查是否包含 skills 和 memory
            has_skills = "# Skills" in content
            has_memory = "# Memory" in content
            
            # 显示简短摘要
            log.info(f"  [{i}] {role}: (length: {len(content)} chars)")
            if has_skills:
                log.info(f"    ✓ Contains Skills section")
            if has_memory:
                log.info(f"    ✓ Contains Memory section")
            
            # 完整内容记录到日志（使用单独的日志条目）
            log.info(f"  [{i}] {role} (full content):\n{content}")
        else:
            # 其他消息正常截断
            if isinstance(content, str) and len(content) > 500:
                content_preview = content[:500] + f"... (truncated, total {len(content)} chars)"
            else:
                content_preview = content
            
            log.info(f"  [{i}] {role}: {content_preview}")
    
    if tools:
        log.info(f"\n🔧 Tools Available: {len(tools)}")
        for tool in tools:
            tool_name = tool["function"]["name"]
            tool_desc = tool["function"]["description"]
            # 只显示第一行或前200字符
            if "\n" in tool_desc:
                # 如果有多行，只显示第一行
                first_line = tool_desc.split("\n")[0]
                if len(first_line) > 200:
                    tool_desc_preview = first_line[:200] + "..."
                else:
                    tool_desc_preview = first_line + " ..."
            elif len(tool_desc) > 200:
                tool_desc_preview = tool_desc[:200] + "..."
            else:
                tool_desc_preview = tool_desc
            log.info(f"  - {tool_name}: {tool_desc_preview}")
        
        # 记录完整的工具定义到 DEBUG 级别
        logger.debug(f"Full tool definitions: {json.dumps(tools, ensure_ascii=False, indent=2)}")
    else:
        log.info("\n🔧 Tools: None")
    
    log.info("=" * 80)


def log_llm_response(
    content: str | None,
    tool_calls: list[Any] | None = None,
    finish_reason: str = "stop",
    usage: dict[str, int] | None = None,
    raw_response: Any = None,
    depth: int = 1
) -> None:
    """
    记录 LLM 响应日志
    
    Args:
        content: 响应内容
        tool_calls: 工具调用列表
        finish_reason: 结束原因
        usage: token 使用情况
        raw_response: 原始响应对象（可选）
        depth: 调用栈深度
    """
    log = logger.opt(depth=depth)
    
    log.info("=" * 80)
    log.info("📥 LLM RESPONSE")
    log.info("=" * 80)
    
    log.info(f"Finish Reason: {finish_reason}")
    
    if content:
        content_preview = content
        if len(content_preview) > 500:
            content_preview = content_preview[:500] + f"... (truncated, total {len(content)} chars)"
        log.info(f"\n💬 Content:\n{content_preview}")
    else:
        log.info("\n💬 Content: (empty)")
    
    if tool_calls:
        log.info(f"\n🔧 Tool Calls: {len(tool_calls)}")
        for tc in tool_calls:
            if hasattr(tc, 'function'):
                # LiteLLM 格式
                log.info(f"  - {tc.function.name}")
                log.info(f"    ID: {tc.id}")
                log.info(f"    Arguments: {tc.function.arguments}")
            elif hasattr(tc, 'name'):
                # 自定义格式
                log.info(f"  - {tc.name}")
                log.info(f"    ID: {tc.id}")
                args_str = json.dumps(tc.arguments, ensure_ascii=False)
                log.info(f"    Arguments: {args_str}")
    else:
        log.info("\n🔧 Tool Calls: None")
    
    if usage:
        log.info(f"\n📊 Usage:")
        log.info(f"  Prompt Tokens: {usage.get('prompt_tokens', 0)}")
        log.info(f"  Completion Tokens: {usage.get('completion_tokens', 0)}")
        log.info(f"  Total Tokens: {usage.get('total_tokens', 0)}")
    
    log.info("=" * 80)
    
    # 记录原始响应到 DEBUG 级别
    if raw_response:
        try:
            # 尝试序列化为 JSON
            if hasattr(raw_response, 'model_dump'):
                raw_dict = raw_response.model_dump()
            elif hasattr(raw_response, '__dict__'):
                raw_dict = raw_response.__dict__
            else:
                raw_dict = dict(raw_response)
            
            raw_json = json.dumps(raw_dict, ensure_ascii=False, indent=2, default=str)
            logger.debug(f"RAW RESPONSE:\n{raw_json}")
        except Exception as e:
            logger.debug(f"RAW RESPONSE (string):\n{str(raw_response)}")
            logger.debug(f"Failed to serialize raw response: {e}")


def log_llm_error(
    error: Exception,
    error_type: str | None = None,
    depth: int = 1
) -> None:
    """
    记录 LLM 错误日志
    
    Args:
        error: 异常对象
        error_type: 错误类型
        depth: 调用栈深度
    """
    log = logger.opt(depth=depth)
    
    log.error("=" * 80)
    log.error("❌ LLM ERROR")
    log.error("=" * 80)
    log.error(f"Error: {str(error)}")
    log.error(f"Error Type: {error_type or type(error).__name__}")
    
    import traceback
    log.error("\n📋 Traceback:")
    log.error(traceback.format_exc())
    log.error("=" * 80)


def log_tool_call(
    tool_name: str,
    tool_id: str,
    arguments: dict[str, Any],
    depth: int = 1
) -> None:
    """
    记录工具调用日志
    
    Args:
        tool_name: 工具名称
        tool_id: 工具调用 ID
        arguments: 工具参数
        depth: 调用栈深度
    """
    log = logger.opt(depth=depth)
    
    args_str = json.dumps(arguments, ensure_ascii=False, indent=2)
    
    log.info("=" * 80)
    log.info(f"🔧 TOOL CALL: {tool_name}")
    log.info("=" * 80)
    log.info(f"Tool ID: {tool_id}")
    log.info(f"Arguments:\n{args_str}")
    log.info("-" * 80)


def log_tool_result(
    tool_name: str,
    result: str,
    depth: int = 1
) -> None:
    """
    记录工具执行结果日志
    
    Args:
        tool_name: 工具名称
        result: 执行结果
        depth: 调用栈深度
    """
    log = logger.opt(depth=depth)
    
    result_preview = result if len(result) <= 500 else result[:500] + f"... (truncated, total {len(result)} chars)"
    log.info(f"Tool Result:\n{result_preview}")
    log.info("=" * 80)


def log_cron_request(
    params: dict[str, Any],
    depth: int = 1
) -> None:
    """
    记录创建定时任务请求日志
    
    Args:
        params: 请求参数
        depth: 调用栈深度
    """
    log = logger.opt(depth=depth)
    
    log.info("=" * 80)
    log.info("📅 CREATE CRON JOB - Request")
    log.info("=" * 80)
    log.info(f"Parameters:\n{json.dumps(params, ensure_ascii=False, indent=2)}")
    log.info("-" * 80)


def log_cron_success(
    job_id: str,
    job_name: str,
    schedule_type: str,
    next_run_time: str | None = None,
    depth: int = 1
) -> None:
    """
    记录创建定时任务成功日志
    
    Args:
        job_id: 任务 ID
        job_name: 任务名称
        schedule_type: 调度类型
        next_run_time: 下次运行时间
        depth: 调用栈深度
    """
    log = logger.opt(depth=depth)
    
    log.info("=" * 80)
    log.info("📅 CREATE CRON JOB - Success")
    log.info("=" * 80)
    log.info(f"Job ID: {job_id}")
    log.info(f"Job Name: {job_name}")
    log.info(f"Schedule Type: {schedule_type}")
    if next_run_time:
        log.info(f"Next Run: {next_run_time}")
    log.info("=" * 80)


def log_cron_error(
    error: Exception,
    params: dict[str, Any],
    depth: int = 1
) -> None:
    """
    记录创建定时任务错误日志
    
    Args:
        error: 异常对象
        params: 请求参数
        depth: 调用栈深度
    """
    log = logger.opt(depth=depth)
    
    log.error("=" * 80)
    log.error("📅 CREATE CRON JOB - Error")
    log.error("=" * 80)
    log.error(f"Error: {str(error)}")
    log.error(f"Parameters: {json.dumps(params, ensure_ascii=False, indent=2)}")
    
    import traceback
    log.error(f"Traceback:\n{traceback.format_exc()}")
    log.error("=" * 80)
