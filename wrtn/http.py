from __future__ import annotations

import asyncio
import contextlib
import datetime
import logging
from typing import Any, ClassVar, Dict, Literal, Optional, List

from jwt import decode as token_decode
from datetime import datetime
import json

_log = logging.getLogger(__name__)

import aiohttp
from .utils import get_expired_from

from .errors import (
    HTTPException,
    Forbidden,
    NotFound,
    ServerError,
    UserNotFound,
    InvalidEmailVerifyCode,
)


def content_type(response: Any) -> Any:
    if response.content_type == "text/html":
        return response.text()
    with contextlib.suppress(Exception):
        return response.json()
    return response.text()


class Route:
    API: ClassVar[str] = "https://api.wow.wrtn.ai"
    CHAT: ClassVar[str] = "https://william.wow.wrtn.ai"

    def __init__(
        self, method: str, path: str, api_type: Literal["api", "API", "chat", "CHAT"]
    ) -> None:
        api_types = {"API": self.API, "CHAT": self.CHAT}
        self.base = api_types[api_type.upper()]
        self.path: str = path
        self.method: str = method

        url = self.base + self.path
        self.url: str = url

    @classmethod
    def api(cls, *args, **kwargs) -> "Route":
        return cls(api_type="api", *args, **kwargs)

    @classmethod
    def chat(cls, *args, **kwargs) -> "Route":
        return cls(api_type="chat", *args, **kwargs)

    @property
    def endpoint(self) -> str:
        return self.base


class HTTPClient:
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        connector: Optional[aiohttp.BaseConnector] = None,
        *,
        proxy: Optional[str] = None,
        proxy_auth: Optional[aiohttp.BasicAuth] = None,
        api_user_agent: Optional[Dict[str, str]] = None,
    ) -> None:
        self.loop: asyncio.AbstractEventLoop = loop
        self.connector: aiohttp.BaseConnector = connector
        self.__session: Optional[aiohttp.ClientSession] = None
        self.__cookie_jar = aiohttp.CookieJar()

        self.token: Optional[str] = None
        self.refresh_user_token: Optional[str] = None
        self.refresh_time: Optional[datetime] = datetime.now()
        self.proxy: Optional[str] = proxy
        self.proxy_auth: Optional[aiohttp.BasicAuth] = proxy_auth

        self.api_user_agent: Dict[str, str] = api_user_agent or {}

    def clear(self) -> None:
        if self.__session and self.__session.closed:
            self.__session = None

    @staticmethod
    def set_browser_header(header: Dict[str, str]) -> Dict[str, str]:
        header["Accept"] = "application/json, text/plain, */*"
        header["Accept-Encoding"] = "gzip, deflate, br"
        header["Accept-Language"] = "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
        header["Origin"] = "https://wrtn.ai"
        header["Referer"] = "https://wrtn.ai"
        header[
            "Sec-Ch-Ua"
        ] = '"Not/A)Brand";v="99", "Google Chrome";v="115", "Chromium";v="115"'
        header["Sec-Ch-Ua-Mobile"] = "?0"
        header["Sec-Ch-Ua-Platform"] = '"Windows"'
        header["Sec-Fetch-Dest"] = "empty"
        header["Sec-Fetch-Mode"] = "cors"
        header["Sec-Fetch-Site"] = "same-site"
        header["User-Agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        )
        return header

    async def stream(
        self,
        route: Route,
        **kwargs: Any,
    ) -> Any:
        method = route.method
        url = route.url
        headers: Dict[str, Any] = kwargs.get("headers", {})

        headers = self.set_browser_header(headers)
        headers["Accept"] = "*/*"
        # text/event-stream type to read the contents

        if self.token is not None and headers.get("Authorization") is None:
            headers["Authorization"] = "Bearer " + self.token
        elif self.token is None and headers.get("Authorization") is None:
            headers["Authorization"] = "Bearer undefined"

        if "json" in kwargs:
            _content_type = "x-www-form-urlencoded" if method == "GET" else "json"
            headers["Content-Type"] = f"application/{_content_type};charset=UTF-8"
        if self.__cookie_jar:
            kwargs["cookie_jar"] = self.__cookie_jar

        kwargs["headers"] = headers

        if self.proxy is not None:
            kwargs["proxy"] = self.proxy
        if self.proxy_auth is not None:
            kwargs["proxy_auth"] = self.proxy_auth
        return self.__session.request(method, url, **kwargs)

    async def request(
        self,
        route: Route,
        **kwargs: Any,
    ) -> Any:
        method = route.method
        url = route.url
        headers: Dict[str, Any] = kwargs.get("headers", {})

        headers = self.set_browser_header(headers)
        if self.token is not None and headers.get("Authorization") is None:
            headers["Authorization"] = "Bearer " + self.token
        elif self.token is None and headers.get("Authorization") is None:
            headers["Authorization"] = "Bearer undefined"

        if "json" in kwargs:
            _content_type = "x-www-form-urlencoded" if method == "GET" else "json"
            headers["Content-Type"] = f"application/{_content_type};charset=UTF-8"
        if self.__cookie_jar:
            kwargs["cookie_jar"] = self.__cookie_jar

        kwargs["headers"] = headers

        if self.proxy is not None:
            kwargs["proxy"] = self.proxy
        if self.proxy_auth is not None:
            kwargs["proxy_auth"] = self.proxy_auth

        async with self.__session.request(method, url, **kwargs) as response:
            _log.debug(
                "%s %s with %s has returned %s",
                method,
                url,
                kwargs.get("data"),
                response.status,
            )

            data = await content_type(response)

            if 300 > response.status >= 200:
                _log.debug("%s %s has received %s", method, url, data)
                return data

            if not data.get("result") == "SUCCESS" or response.status == 403:
                raise Forbidden(response, data)
            elif response.status == 404:
                raise NotFound(response, data)
            elif response.status >= 500:
                raise ServerError(response, data)
            else:
                raise HTTPException(response, data)

    async def close(self) -> None:
        if self.__session:
            await self.__session.close()

    async def static_login(self, refresh_token: str) -> None:
        if self.connector is None:
            self.connector = aiohttp.TCPConnector(limit=0)
        self.__session = aiohttp.ClientSession(
            connector=self.connector, cookie_jar=self.__cookie_jar
        )

        self.refresh_user_token = refresh_token
        await self.refresh_token()
        decode = token_decode(self.token, options={"verify_signature": False})
        self.refresh_time = datetime.fromtimestamp(decode["exp"])

        user_data = await self.get_user()
        self.api_user_agent["email"] = user_data["email"]
        self.api_user_agent["user_id"] = user_data["_id"]
        if user_data["meta"].get("platform") is not None:
            self.api_user_agent["platform"] = user_data["meta"]["platform"]

    async def local_login(
        self,
        email: str,
        password: str,
    ) -> None:
        if self.connector is None:
            self.connector = aiohttp.TCPConnector(limit=0)
        self.__session = aiohttp.ClientSession(
            connector=self.connector, cookie_jar=self.__cookie_jar
        )

        response = await self.email_exist(email)
        if not response:
            raise UserNotFound("You are not signed in or are not a local user.")
        await self.email_exist(email)

        response = await self.request(
            Route.api("POST", "/auth/local"),
            json={"email": email, "password": password},
        )
        self.token = response["data"]["accessToken"]
        self.refresh_user_token = response["data"]["refreshToken"]
        self.refresh_time = get_expired_from(self.token)

        user_data = await self.get_user()
        self.api_user_agent["email"] = user_data["email"]
        self.api_user_agent["user_id"] = user_data["_id"]
        if user_data["meta"].get("platform") is not None:
            self.api_user_agent["platform"] = user_data["meta"]["platform"]

    async def email_exist(self, email: str) -> bool:
        response = await self.request(
            Route.api("GET", "/auth/check"), params={"email": email}
        )
        if len(response["data"]) == 0:
            return False
        elif not response["data"]["provider"] == "local":
            return False
        return True

    async def send_verify_code(self, email: str) -> None:
        for tries in range(5):
            try:
                await self.request(
                    Route.api("POST", "/auth/code"), params={"email": email}
                )
                return
            except ServerError as e:
                if "구독자 상태" in e.message.get("message"):
                    continue
                else:
                    raise e
        raise ServerError(500, {"message": "이메일 인증 코드 전송 실패"})

    async def enter_verify_code(
        self,
        email: str,
        code: str,
    ):
        response = await self.request(
            Route.api("GET", "/auth/code"), params={"email": email, "code": code}
        )
        if response.get("data") is None or response.get("data") is not True:
            raise InvalidEmailVerifyCode

    async def register(
        self,
        ga_device_id: str,
        email: str,
        password: str,
        platform: str = "web",
    ) -> None:
        await self.request(
            Route.api(
                "POST",
                "/auth/register",
            ),
            json={"email": email, "password": password},
            params={"deviceId": ga_device_id, "platform": platform},
        )

    async def update_agreement(
        self,
        marketing_term: bool = True,
        privacy_term: bool = True,
        service_term: bool = True,
    ) -> None:
        await self.request(
            Route.api("PUT", "/user"),
            json={
                "serviceTerm": service_term,
                "privacyTerm": privacy_term,
                "marketingTerm": marketing_term,
            },
        )

    async def update_info(
        self,
        job: Optional[List[str]],
        company: str = "",
    ) -> None:
        await self.request(
            Route.api("PUT", "/user"),
            json={
                "company": company,
                "job": job,
            },
        )

    async def get_user(self) -> Any:
        response = await self.request(
            Route.api("GET", "/user"),
        )
        return response["data"]

    async def get_activate_rooms(self) -> Any:
        response = await self.request(Route.api("GET", "/chat"))
        return response["data"]

    async def get_room(self, room_id: str) -> Any:
        response = await self.request(Route.api("GET", f"/chat/{room_id}"))
        return response["data"]

    async def create_room(self) -> Any:
        response = await self.request(Route.api("POST", "/chat"))
        return response["data"]

    async def refresh_token(self) -> None:
        response = await self.request(
            Route.api("POST", "/auth/refresh"),
            headers={"Authorization": "Bearer " + self.refresh_user_token},
        )
        self.token = response["data"]["accessToken"]
        self.refresh_time = get_expired_from(response["data"]["accessToken"])

    async def prompt_with_reader(
        self,
        room_id: str,
        content: str,
        model: Literal["GPT3.5", "GPT4", "GPT3.5_16K", "PALM"],
        reroll: bool = False,
        chip: bool = False,
    ) -> Any:
        json_data = {}
        if chip:
            json_data.update({"chip": True})
        json_data["reroll"] = reroll
        json_data["message"] = content

        requester = await self.stream(
            Route.chat("POST", f"/chat/{room_id}/stream"),
            params={
                "model": model,
                "platform": self.api_user_agent["platform"],
                "user": self.api_user_agent["email"],
            },
            json=json_data,
        )
        return requester

    async def prompt(
        self,
        room_id: str,
        content: str,
        model: Literal["GPT3.5", "GPT4", "GPT3.5_16K", "PALM"],
        reroll: bool = False,
        chip: bool = False,
    ) -> Dict[str, Any]:
        json_data = {}
        if chip:
            json_data.update({"chip": True})
        json_data["reroll"] = reroll
        json_data["message"] = content

        requester = await self.stream(
            Route.chat("POST", f"/chat/{room_id}/stream"),
            params={
                "model": model,
                "platform": self.api_user_agent["platform"],
                "user": self.api_user_agent["email"],
            },
            json=json_data,
        )
        async with requester as response:
            async for data in response.content:
                raw = data.decode("utf-8")
                raw = raw.replace('data: ', '')
                clean_data = raw.replace('\n', '')
                try:
                    data = json.loads(clean_data)
                    if data.get("message") is not None:
                        return data["message"]
                except json.decoder.JSONDecodeError:
                    pass
