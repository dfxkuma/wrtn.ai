from typing import Any, Dict, List, Optional, TYPE_CHECKING

from json import dumps
from datetime import datetime
from abcmeta import WrtnModelABC

if TYPE_CHECKING:
    from http import HTTPClient


class BaseWrtnModel(WrtnModelABC):
    def __init__(self, **response_data: Any) -> None:
        self.response_data = response_data

    @property
    def data(self) -> Dict[str, Any]:
        return self.response_data

    @property
    def wrapped_data(self) -> str:
        return dumps(self.response_data)


class User(BaseWrtnModel):
    def __init__(
        self,
        http_client: "HTTPClient",
        **response_data: Any,
    ) -> None:
        super().__init__(**response_data)
        self._http: "HTTPClient" = http_client

    @property
    def id(self) -> str:
        return self.data.get("_id")

    @property
    def name(self) -> str:
        return self.data.get("name")

    @property
    def email(self) -> str:
        return self.data.get("email")

    @property
    def encrypted_password(self) -> str:
        return self.data.get("password")

    @property
    def salt(self) -> int:
        return int(self.data.get("salt"))

    @property
    def phone_number(self) -> Optional[str]:
        return self.data.get("number")

    @property
    def login_provider(self) -> str:
        return self.data.get("provider")

    @property
    def inflow(self) -> Optional[str]:
        return self.data.get("inflow")

    @property
    def company(self) -> Optional[str]:
        return self.data.get("company")

    @property
    def job(self) -> Optional[List[str]]:
        return self.data.get("job")

    @property
    def purpose(self) -> Optional[List[str]]:
        return self.data.get("purpose")

    @property
    def is_newbie(self) -> bool:
        return bool(self.data.get("isNewbie"))

    @property
    def agreement_date(self) -> Optional[datetime]:
        return datetime.strptime(
            self.data.get("agreementDate"), "%Y-%m-%dT%H:%M:%S.%fZ"
        )

    @property
    def service_term_date(self) -> Optional[datetime]:
        return datetime.strptime(self.data.get("serviceTerm"), "%Y-%m-%dT%H:%M:%S.%fZ")

    @property
    def privacy_term_date(self) -> Optional[datetime]:
        return datetime.strptime(self.data.get("privacyTerm"), "%Y-%m-%dT%H:%M:%S.%fZ")

    @property
    def marketing_term_date(self) -> Optional[datetime]:
        return datetime.strptime(
            self.data.get("marketingTerm"), "%Y-%m-%dT%H:%M:%S.%fZ"
        )

    @property
    def is_account_active(self) -> bool:
        return bool(self.data.get("isActive"))

    @property
    def is_account_deleted(self) -> bool:
        return bool(self.data.get("isDeleted"))

    @property
    def deleted_at(self) -> Optional[datetime]:
        return datetime.strptime(self.data.get("deletedAt"), "%Y-%m-%dT%H:%M:%S.%fZ")

    @property
    def plan(self) -> str:
        return self.data.get("plan")

    @property
    def next_month_plan(self) -> Optional[str]:
        return self.data.get("nextPlan")

    @property
    def payment_date(self) -> Optional[datetime]:
        return datetime.strptime(self.data.get("paymentDate"), "%Y-%m-%dT%H:%M:%S.%fZ")

    @property
    def payment_due_date(self) -> Optional[datetime]:
        return datetime.strptime(self.data.get("dueDate"), "%Y-%m-%dT%H:%M:%S.%fZ")


class ChatRoom(BaseWrtnModel):
    def __init__(
        self,
        http_client: "HTTPClient",
        **response_data: Any,
    ) -> None:
        super().__init__(**response_data)
        self._http: "HTTPClient" = http_client

    @property
    def id(self) -> str:
        return self.data.get("_id")

    @property
    def user_id(self) -> str:
        return self.data.get("userId")

    @property
    def is_deleted(self) -> bool:
        return bool(self.data.get("isDeleted"))

    @property
    def version(self) -> str:
        return self.data.get("version")

    @property
    def created_at(self) -> datetime:
        return datetime.strptime(self.data.get("createdAt"), "%Y-%m-%dT%H:%M:%S.%fZ")

    @property
    def updated_at(self) -> datetime:
        return datetime.strptime(self.data.get("createdAt"), "%Y-%m-%dT%H:%M:%S.%fZ")

    @property
    def topic(self) -> str:
        return self.data.get("topic")
