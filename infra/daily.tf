# ---------- 每日 07:00 邮件：SES + 第二个 Lambda + EventBridge Scheduler ----------

# SES 邮箱身份。apply 后 AWS 会给这个邮箱发验证邮件，点了才能收发。
# 新账号在 SES 沙盒里：只能发给已验证地址，所以发件人 = 收件人 = 这个邮箱。
resource "aws_sesv2_email_identity" "coach" {
  email_identity = var.coach_email
}

# daily 函数自己的执行角色：和 Web 函数分开，各拿各的最小权限
resource "aws_iam_role" "daily" {
  name               = "${var.app_name}-daily"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy_attachment" "daily_logs" {
  role       = aws_iam_role.daily.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# 读预约：复用 Web 函数那份"只许碰这一张表"的策略文档
resource "aws_iam_role_policy" "daily_dynamodb" {
  name   = "${var.app_name}-dynamodb"
  role   = aws_iam_role.daily.id
  policy = data.aws_iam_policy_document.lambda_dynamodb.json
}

# 发信：只允许用这一个已验证身份发
data "aws_iam_policy_document" "daily_ses" {
  statement {
    actions   = ["ses:SendEmail"]
    resources = [aws_sesv2_email_identity.coach.arn]
  }
}

resource "aws_iam_role_policy" "daily_ses" {
  name   = "${var.app_name}-ses"
  role   = aws_iam_role.daily.id
  policy = data.aws_iam_policy_document.daily_ses.json
}

resource "aws_cloudwatch_log_group" "daily" {
  name              = "/aws/lambda/${var.app_name}-daily"
  retention_in_days = 14
}

# 同一个镜像、同一个 uvicorn 入口。区别全在环境变量：
# - AWS_LWA_PASS_THROUGH_PATH：Lambda Web Adapter 收到非 HTTP 事件（定时器 JSON）时，POST 到这个路径
# - TASKS_ENABLED=1：代码里只有带这个变量的进程才响应 /tasks/*，Web 函数上是 404
resource "aws_lambda_function" "daily" {
  function_name = "${var.app_name}-daily"
  role          = aws_iam_role.daily.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.app.repository_url}:${var.image_tag}"
  architectures = ["arm64"]
  memory_size   = 512
  timeout       = 30

  environment {
    variables = {
      TABLE_NAME                = aws_dynamodb_table.main.name
      COACH_EMAIL               = var.coach_email
      TASKS_ENABLED             = "1"
      AWS_LWA_PASS_THROUGH_PATH = "/tasks/daily-email"
    }
  }

  lifecycle {
    ignore_changes = [image_uri] # 和 Web 函数一样，镜像版本归 CI 管
  }

  depends_on = [
    aws_iam_role_policy_attachment.daily_logs,
    aws_cloudwatch_log_group.daily,
  ]
}

# ---------- EventBridge Scheduler ----------
# 比老的 EventBridge Rule 多了时区支持：cron 直接写本地 07:00，夏令时自动处理。

data "aws_iam_policy_document" "scheduler_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "${var.app_name}-scheduler"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume.json
}

data "aws_iam_policy_document" "scheduler_invoke" {
  statement {
    actions   = ["lambda:InvokeFunction"]
    resources = [aws_lambda_function.daily.arn]
  }
}

resource "aws_iam_role_policy" "scheduler_invoke" {
  name   = "invoke-daily"
  role   = aws_iam_role.scheduler.id
  policy = data.aws_iam_policy_document.scheduler_invoke.json
}

resource "aws_scheduler_schedule" "daily" {
  name                         = "${var.app_name}-daily-email"
  schedule_expression          = "cron(0 7 * * ? *)"
  schedule_expression_timezone = "America/Vancouver"

  flexible_time_window {
    mode = "OFF" # 准点触发，不要 AWS 帮我们在窗口内随机
  }

  target {
    arn      = aws_lambda_function.daily.arn
    role_arn = aws_iam_role.scheduler.arn
    input    = jsonencode({ source = "scheduler" })
  }
}

output "daily_function_name" {
  value = aws_lambda_function.daily.function_name
}
