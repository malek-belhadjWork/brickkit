"""s3 source (stub). Defers boto3 import into the factory body so a folder/email
client never needs the AWS SDK installed, even though this file ships with the
brick."""
from __future__ import annotations

from ..registry import REGISTRY


@REGISTRY.register("s3")
def make_s3(**params):
    def fetch():
        import boto3  # noqa: F401  — deferred; only required if s3 is selected

        raise NotImplementedError(
            "s3 source not implemented yet; add it as a plugin only"
        )

    return fetch
