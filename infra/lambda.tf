# ---------- Lambda 的"身份"：执行角色 ----------
# 相当于给应用一个服务账号。Lambda 启动时扮演这个角色，用它的权限调别的 AWS 服务。
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${var.app_name}-lambda"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

# AWS 预置策略：允许写 CloudWatch 日志。没有它 Lambda 跑了也看不到日志。
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# ---------- 日志组 ----------
# 自己建而不是让 Lambda 自动建，为的是能设保留天数；自动建的永不过期。
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.app_name}"
  retention_in_days = 14
}

# ---------- Lambda 函数本体 ----------
resource "aws_lambda_function" "app" {
  function_name = var.app_name
  role          = aws_iam_role.lambda.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.app.repository_url}:${var.image_tag}"
  architectures = ["arm64"]
  memory_size   = 512
  timeout       = 30

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.main.name
    }
  }

  # 第 3 天起由 CI 用 update-function-code 换镜像，Terraform 不要把它改回去
  lifecycle {
    ignore_changes = [image_uri]
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_logs,
    aws_cloudwatch_log_group.lambda,
  ]
}

output "lambda_function_name" {
  value = aws_lambda_function.app.function_name
}
