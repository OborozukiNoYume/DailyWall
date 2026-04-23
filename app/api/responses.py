from typing import Any

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

SUCCESS_MSG = "success"
NOT_FOUND_MSG = "未找到数据"
SERVER_ERROR_MSG = "服务器异常"
PARAM_ERROR_PREFIX = "参数错误："
DEFAULT_PARAM_ERROR_MSG = "请求参数无效"


def success_response(data: Any, status_code: int = 200) -> dict[str, Any]:
    return {"code": status_code, "msg": SUCCESS_MSG, "data": data}


def error_response(status_code: int, msg: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"code": status_code, "msg": msg, "data": None},
    )


def build_param_error_msg(detail: str | None = None) -> str:
    detail = (detail or "").strip()
    if not detail:
        detail = DEFAULT_PARAM_ERROR_MSG
    return f"{PARAM_ERROR_PREFIX}{detail}"


def format_validation_error(exc: RequestValidationError) -> str:
    first_error = next(iter(exc.errors()), None)
    if not first_error:
        return build_param_error_msg()

    loc = [
        str(item)
        for item in first_error.get("loc", [])
        if item not in {"query", "path", "body"}
    ]
    field = ".".join(loc)
    error_type = first_error.get("type", "")
    ctx = first_error.get("ctx") or {}

    if error_type == "missing":
        detail = f"{field} 为必填项" if field else "缺少必填参数"
    elif error_type == "string_too_short":
        min_length = ctx.get("min_length")
        detail = f"{field} 长度不能少于 {min_length}" if field else "字符串长度过短"
    elif error_type == "greater_than_equal":
        ge = ctx.get("ge")
        detail = f"{field} 不能小于 {ge}" if field else "数值过小"
    elif error_type == "less_than_equal":
        le = ctx.get("le")
        detail = f"{field} 不能大于 {le}" if field else "数值过大"
    elif error_type == "int_parsing":
        detail = f"{field} 必须是整数" if field else "参数必须是整数"
    elif error_type in {"date_parsing", "date_from_datetime_parsing"}:
        detail = f"{field} 日期格式无效，应为 YYYY-MM-DD" if field else "日期格式无效，应为 YYYY-MM-DD"
    elif error_type == "bool_parsing":
        detail = f"{field} 必须是布尔值" if field else "参数必须是布尔值"
    elif error_type == "string_pattern_mismatch":
        detail = f"{field} 格式无效" if field else "参数格式无效"
    else:
        raw_msg = first_error.get("msg") or DEFAULT_PARAM_ERROR_MSG
        detail = f"{field} {raw_msg}".strip() if field else raw_msg

    return build_param_error_msg(detail)
