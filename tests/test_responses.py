import pytest
from fastapi.exceptions import RequestValidationError

from app.api.responses import (
    build_param_error_msg,
    error_response,
    format_validation_error,
    success_response,
)


def test_success_response_wraps_payload():
    assert success_response({"ok": True}) == {
        "code": 200,
        "msg": "success",
        "data": {"ok": True},
    }


def test_error_response_uses_uniform_shape():
    response = error_response(404, "未找到数据")

    assert response.status_code == 404
    assert response.body.decode("utf-8") == (
        '{"code":404,"msg":"未找到数据","data":null}'
    )


def test_build_param_error_msg_uses_default_when_detail_missing():
    assert build_param_error_msg() == "参数错误：请求参数无效"
    assert build_param_error_msg("  size 格式无效 ") == "参数错误：size 格式无效"


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            {"loc": ("query", "keyword"), "type": "missing", "msg": "Field required"},
            "参数错误：keyword 为必填项",
        ),
        (
            {
                "loc": ("query", "keyword"),
                "type": "string_too_short",
                "msg": "String should have at least 2 characters",
                "ctx": {"min_length": 2},
            },
            "参数错误：keyword 长度不能少于 2",
        ),
        (
            {
                "loc": ("query", "page"),
                "type": "greater_than_equal",
                "msg": "Input should be greater than or equal to 1",
                "ctx": {"ge": 1},
            },
            "参数错误：page 不能小于 1",
        ),
        (
            {
                "loc": ("query", "size"),
                "type": "less_than_equal",
                "msg": "Input should be less than or equal to 100",
                "ctx": {"le": 100},
            },
            "参数错误：size 不能大于 100",
        ),
        (
            {"loc": ("query", "year"), "type": "int_parsing", "msg": "Input should be a valid integer"},
            "参数错误：year 必须是整数",
        ),
        (
            {"loc": ("query", "date"), "type": "date_parsing", "msg": "Input should be a valid date"},
            "参数错误：date 日期格式无效，应为 YYYY-MM-DD",
        ),
        (
            {"loc": ("query", "dedup"), "type": "bool_parsing", "msg": "Input should be a valid boolean"},
            "参数错误：dedup 必须是布尔值",
        ),
        (
            {
                "loc": ("query", "size"),
                "type": "string_pattern_mismatch",
                "msg": "String should match pattern",
            },
            "参数错误：size 格式无效",
        ),
        (
            {"loc": ("query", "mkt"), "type": "custom_error", "msg": "unexpected value"},
            "参数错误：mkt unexpected value",
        ),
    ],
)
def test_format_validation_error_covers_supported_branches(error, expected):
    exc = RequestValidationError([error])

    assert format_validation_error(exc) == expected
