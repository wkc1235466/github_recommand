"""AI Provider Service - 统一处理 Claude 兼容 API 的连接测试"""

from enum import Enum
from typing import Optional, Dict, Any
import httpx
from pydantic import BaseModel
import time
import json


class AIProviderType(str, Enum):
    """AI 提供商类型"""
    CLAUDE = "claude"  # Claude Messages API 格式


class AIProviderConfig(BaseModel):
    """AI 提供商配置"""
    api_url: str
    api_key: str
    model: str
    provider_type: AIProviderType = AIProviderType.CLAUDE


class ConnectionTestResult(BaseModel):
    """连接测试结果"""
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    response_time_ms: Optional[int] = None


class AIProviderService:
    """AI 提供商服务"""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    async def test_connection(self, config: AIProviderConfig) -> ConnectionTestResult:
        """
        测试 AI 提供商连接

        Args:
            config: AI 提供商配置

        Returns:
            ConnectionTestResult: 测试结果
        """
        start_time = time.time()

        try:
            if config.provider_type == AIProviderType.CLAUDE:
                return await self._test_claude_api(config, start_time)
            else:
                return ConnectionTestResult(
                    success=False,
                    message=f"不支持的提供商类型: {config.provider_type}"
                )

        except httpx.TimeoutException:
            return ConnectionTestResult(
                success=False,
                message="请求超时，请检查网络连接或增加超时时间"
            )
        except httpx.ConnectError as e:
            return ConnectionTestResult(
                success=False,
                message=f"无法连接到服务器: {str(e)}"
            )
        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message=f"测试失败: {str(e)}"
            )

    async def _test_claude_api(
        self,
        config: AIProviderConfig,
        start_time: float
    ) -> ConnectionTestResult:
        """测试 Claude API 连接"""
        test_prompt = "你好，请回复OK来确认连接正常。"

        # 确保 URL 以 /v1/messages 结尾（BigModel 等提供商的 Claude 兼容端点）
        api_url = config.api_url
        if not api_url.endswith('/v1/messages'):
            if api_url.endswith('/'):
                api_url = api_url + 'v1/messages'
            else:
                api_url = api_url + '/v1/messages'

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    api_url,
                    headers={
                        "Content-Type": "application/json",
                        "x-api-key": config.api_key,
                        "anthropic-version": "2023-06-01",
                    },
                    json={
                        "model": config.model,
                        "max_tokens": 10,
                        "messages": [{"role": "user", "content": test_prompt}],
                    },
                )

                response_time = int((time.time() - start_time) * 1000)

                # 尝试解析 JSON 响应
                try:
                    response_data = response.json()
                except:
                    response_data = {}

                # 处理 BigModel/GLM 特殊错误（套餐权限限制）
                if response.status_code == 429:
                    error_msg = self._extract_bigmodel_permission_error(response_data)
                    if error_msg:
                        return ConnectionTestResult(
                            success=False,
                            message=error_msg,
                            details={
                                "status_code": response.status_code,
                                "error_type": "permission_denied"
                            },
                            response_time_ms=response_time
                        )

                # 提取其他错误信息
                error_msg = self._extract_error_from_response(response_data)
                if error_msg:
                    return ConnectionTestResult(
                        success=False,
                        message=error_msg,
                        details={
                            "status_code": response.status_code,
                            "response": response.text[:500] if response.text else ""
                        },
                        response_time_ms=response_time
                    )

                # 检查成功响应
                if response.status_code == 200:
                    if "content" in response_data and len(response_data.get("content", [])) > 0:
                        return ConnectionTestResult(
                            success=True,
                            message="连接成功",
                            details={
                                "model": config.model,
                                "response_time_ms": response_time
                            },
                            response_time_ms=response_time
                        )
                    else:
                        return ConnectionTestResult(
                            success=False,
                            message="响应格式异常：缺少 content 字段",
                            details={"response": response.text[:500] if response.text else ""},
                            response_time_ms=response_time
                        )
                else:
                    return ConnectionTestResult(
                        success=False,
                        message=f"HTTP {response.status_code}: {response.text[:100] if response.text else '无响应内容'}",
                        details={"response": response.text[:500] if response.text else ""},
                        response_time_ms=response_time
                    )

        except httpx.HTTPStatusError as e:
            response_time = int((time.time() - start_time) * 1000)

            # 尝试解析错误响应
            try:
                error_data = e.response.json()
            except:
                error_data = {}

            # 处理 429 错误（可能是权限限制）
            if e.response.status_code == 429:
                error_msg = self._extract_bigmodel_permission_error(error_data)
                if error_msg:
                    return ConnectionTestResult(
                        success=False,
                        message=error_msg,
                        details={
                            "status_code": e.response.status_code,
                            "error_type": "permission_denied"
                        },
                        response_time_ms=response_time
                    )

            return ConnectionTestResult(
                success=False,
                message=f"HTTP 错误: {e.response.status_code}",
                details={"response": e.response.text[:500] if e.response.text else ""},
                response_time_ms=response_time
            )

    def _extract_bigmodel_permission_error(self, response_data: Dict) -> Optional[str]:
        """
        提取 BigModel/GLM 的权限限制错误信息

        处理类似错误：
        {
            "error": {
                "message": "HTTP 429 Too Many Requests: {\"error\":{\"code\":\"1311\",\"message\":\"当前订阅套餐暂未开放GLM-5权限\"}}",
                "type": "rate_limit_error"
            }
        }
        """
        if not response_data:
            return None

        # 检查 BigModel 套餐权限错误
        if "error" in response_data:
            error = response_data["error"]
            if isinstance(error, dict):
                error_msg = error.get("message", "")

                # 解析嵌套的 JSON 错误消息
                if "Too Many Requests" in error_msg or "429" in error_msg:
                    # 尝试提取内部的中文错误消息
                    try:
                        # 查找最后一个 { ... } 部分
                        start = error_msg.rfind("{")
                        if start != -1:
                            inner_json = error_msg[start:]
                            inner_data = json.loads(inner_json)

                            # 提取真正的错误消息
                            if "error" in inner_data:
                                inner_error = inner_data["error"]
                                if isinstance(inner_error, dict):
                                    msg = inner_error.get("message", "")
                                    if "暂未开放" in msg or "权限" in msg:
                                        return f"模型权限不足：{msg}"
                    except:
                        pass

                # 通用 429 处理
                if error.get("type") == "rate_limit_error":
                    return "请求频率限制或模型权限不足，请检查您的套餐是否支持该模型"

        return None

    def _extract_error_from_response(self, response_data: Dict) -> Optional[str]:
        """
        从 API 响应中提取错误信息

        支持多种错误格式：
        1. Claude: {"error": {"message": "...", "type": "..."}}
        2. BigModel: {"error": {"message": "...", "type": "rate_limit_error"}}
        3. 通用: {"message": "..."}
        4. 自定义: {"code": int, "msg": "...", "success": false}
        """
        if not response_data:
            return None

        # 格式1: Claude/BigModel API 错误
        if "error" in response_data:
            error = response_data["error"]
            if isinstance(error, dict):
                # 优先返回 message
                if "message" in error:
                    msg = error["message"]
                    # 过滤掉嵌套的 JSON，返回清晰的错误
                    if "Too Many Requests" in msg:
                        # 交给 _extract_bigmodel_permission_error 处理
                        pass
                    else:
                        return msg
                return error.get("type") or str(error)
            return str(error)

        # 格式2: 直接的 message 字段
        if "message" in response_data:
            return response_data["message"]

        # 格式3: 自定义格式
        if response_data.get("success") is False:
            return response_data.get("msg") or response_data.get("message")

        # 格式4: type 为 error
        if response_data.get("type") == "error":
            return response_data.get("message")

        return None
