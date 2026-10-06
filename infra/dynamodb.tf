# ---------- DynamoDB 单表 ----------
# 单表设计：时段、预约都放一张表，靠 PK/SK 前缀区分类型。
# 第 4 天定具体键的格式，这里只定"有 PK 和 SK 两个字符串键"。
resource "aws_dynamodb_table" "main" {
  name         = var.app_name
  billing_mode = "PAY_PER_REQUEST" # 按请求计费，没流量不花钱，免费额度 2500 万次/月
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }
  attribute {
    name = "SK"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true # 35 天内任意时刻恢复，免费额度内
  }
}

# Lambda 读写这张表的权限。只给这一张表，不给 "*"。
data "aws_iam_policy_document" "lambda_dynamodb" {
  statement {
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:Query",
    ]
    resources = [aws_dynamodb_table.main.arn]
  }
}

resource "aws_iam_role_policy" "lambda_dynamodb" {
  name   = "${var.app_name}-dynamodb"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.lambda_dynamodb.json
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.main.name
}
