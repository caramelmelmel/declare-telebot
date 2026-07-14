import asyncio
import io

from minio import Minio
from minio.commonconfig import Filter
from minio.error import S3Error
from minio.lifecycleconfig import Expiration, LifecycleConfig, Rule

from src.repositories.ports import PayloadStore

DEFAULT_LIFECYCLE_RULE_ID = "expire-prompt-payloads"


class MinioPayloadStore(PayloadStore):
    """Real adapter: stores raw update payloads as objects in MinIO."""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False,
        retention_days: int = 30,
    ) -> None:
        self._client = Minio(
            endpoint, access_key=access_key, secret_key=secret_key, secure=secure
        )
        self._bucket = bucket
        self._retention_days = retention_days

    def _ensure_bucket(self) -> None:
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)
        self._ensure_lifecycle_rule()

    def _ensure_lifecycle_rule(self) -> None:
        """Bucket-level object expiry backstop (FR-009, SC-006, research.md §4)."""
        config = LifecycleConfig(
            [
                Rule(
                    rule_id=DEFAULT_LIFECYCLE_RULE_ID,
                    status="Enabled",
                    rule_filter=Filter(prefix=""),
                    expiration=Expiration(days=self._retention_days),
                )
            ]
        )
        self._client.set_bucket_lifecycle(self._bucket, config)

    async def put_raw_payload(self, object_key: str, payload: bytes) -> None:
        await asyncio.to_thread(self._put_sync, object_key, payload)

    def _put_sync(self, object_key: str, payload: bytes) -> None:
        self._ensure_bucket()
        self._client.put_object(
            self._bucket, object_key, io.BytesIO(payload), length=len(payload)
        )

    async def delete_raw_payload(self, object_key: str) -> None:
        await asyncio.to_thread(self._delete_sync, object_key)

    def _delete_sync(self, object_key: str) -> None:
        try:
            self._client.remove_object(self._bucket, object_key)
        except S3Error:
            pass

    async def ping(self) -> bool:
        try:
            await asyncio.to_thread(self._client.bucket_exists, self._bucket)
            return True
        except Exception:
            return False
