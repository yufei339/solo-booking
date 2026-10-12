import boto3
import pytest
from moto import mock_aws

from app import db


@pytest.fixture(autouse=True)
def fake_dynamodb(monkeypatch):
    """每个测试跑在一个全新的假 DynamoDB 里，带一张空的 solo-booking 表。"""
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ca-central-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    with mock_aws():
        boto3.resource("dynamodb").create_table(
            TableName=db.TABLE_NAME,
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        db._table = None
        yield
        db._table = None
