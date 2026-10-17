# ---------- 告警通道：SNS → 邮件 ----------
resource "aws_sns_topic" "alarms" {
  name = "${var.app_name}-alarms"
}

# apply 后 AWS 发确认邮件，点了订阅才生效
resource "aws_sns_topic_subscription" "alarms_email" {
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.coach_email
}

locals {
  api_dim    = { ApiId = aws_apigatewayv2_api.app.id }
  web_dim    = { FunctionName = aws_lambda_function.app.function_name }
  daily_dim  = { FunctionName = aws_lambda_function.daily.function_name }
  alarm_acts = [aws_sns_topic.alarms.arn]
}

# ---------- 告警 1：5xx 比例 ----------
# 用 metric math 算比例而不是绝对数：请求少的时候 1 个错误就是 100%，所以再加"请求 >= 5 才算"。
resource "aws_cloudwatch_metric_alarm" "api_5xx_ratio" {
  alarm_name          = "${var.app_name}-5xx-ratio"
  alarm_description   = "5 分钟内 5xx 比例超过 5%（且请求数 >= 5）"
  comparison_operator = "GreaterThanThreshold"
  threshold           = 5
  evaluation_periods  = 1
  treat_missing_data  = "notBreaching" # 没流量 = 没问题，别半夜报"数据缺失"
  alarm_actions       = local.alarm_acts
  ok_actions          = local.alarm_acts

  metric_query {
    id          = "ratio"
    expression  = "IF(requests >= 5, 100 * errors / requests, 0)"
    label       = "5xx %"
    return_data = true
  }
  metric_query {
    id = "errors"
    metric {
      namespace   = "AWS/ApiGateway"
      metric_name = "5xx"
      dimensions  = local.api_dim
      period      = 300
      stat        = "Sum"
    }
  }
  metric_query {
    id = "requests"
    metric {
      namespace   = "AWS/ApiGateway"
      metric_name = "Count"
      dimensions  = local.api_dim
      period      = 300
      stat        = "Sum"
    }
  }
}

# ---------- 告警 2：p95 延迟 ----------
# 连续 2 个 5 分钟窗口都超过 3 秒才报：Lambda 冷启动约 5 秒，低流量时一次冷启动就能把单个窗口的 p95 顶上去。
resource "aws_cloudwatch_metric_alarm" "api_p95_latency" {
  alarm_name          = "${var.app_name}-p95-latency"
  alarm_description   = "p95 延迟连续 10 分钟超过 3 秒"
  namespace           = "AWS/ApiGateway"
  metric_name         = "Latency"
  dimensions          = local.api_dim
  period              = 300
  extended_statistic  = "p95"
  comparison_operator = "GreaterThanThreshold"
  threshold           = 3000
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_acts
  ok_actions          = local.alarm_acts
}

# ---------- 告警 3 / 4：Lambda 本身报错（超时、崩溃、daily 邮件发失败） ----------
# 注意 FastAPI 自己处理掉的 500 不算 Lambda Errors，那个走告警 1。
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each = {
    web   = local.web_dim
    daily = local.daily_dim
  }
  alarm_name          = "${var.app_name}-${each.key}-lambda-errors"
  alarm_description   = "${each.key} 函数 1 小时内有调用失败"
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  dimensions          = each.value
  period              = 3600
  statistic           = "Sum"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  evaluation_periods  = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_acts
  ok_actions          = local.alarm_acts
}

# ---------- 看板 ----------
locals {
  api_ns   = "AWS/ApiGateway"
  api_id   = aws_apigatewayv2_api.app.id
  web_fn   = aws_lambda_function.app.function_name
  daily_fn = aws_lambda_function.daily.function_name
  dashboard = {
    widgets = [
      {
        type = "metric", x = 0, y = 0, width = 8, height = 6
        properties = {
          title = "请求量 / 4xx / 5xx", region = var.region, period = 300, stat = "Sum", view = "timeSeries"
          metrics = [
            [local.api_ns, "Count", "ApiId", local.api_id, { label = "请求" }],
            [local.api_ns, "4xx", "ApiId", local.api_id, { label = "4xx" }],
            [local.api_ns, "5xx", "ApiId", local.api_id, { label = "5xx", color = "#d62728" }],
          ]
        }
      },
      {
        type = "metric", x = 8, y = 0, width = 8, height = 6
        properties = {
          title = "延迟 p50 / p95 (ms)", region = var.region, period = 300, view = "timeSeries"
          metrics = [
            [local.api_ns, "Latency", "ApiId", local.api_id, { stat = "p50", label = "p50" }],
            [local.api_ns, "Latency", "ApiId", local.api_id, { stat = "p95", label = "p95" }],
          ]
          annotations = { horizontal = [{ value = 3000, label = "告警线 3s" }] }
        }
      },
      {
        type = "metric", x = 16, y = 0, width = 8, height = 6
        properties = {
          title = "5xx 比例 (%)", region = var.region, period = 300, view = "timeSeries"
          metrics = [
            [{ expression = "IF(requests >= 5, 100 * errors / requests, 0)", label = "5xx %", id = "ratio" }],
            [local.api_ns, "5xx", "ApiId", local.api_id, { id = "errors", stat = "Sum", visible = false }],
            [local.api_ns, "Count", "ApiId", local.api_id, { id = "requests", stat = "Sum", visible = false }],
          ]
          annotations = { horizontal = [{ value = 5, label = "告警线 5%" }] }
        }
      },
      {
        type = "metric", x = 0, y = 6, width = 8, height = 6
        properties = {
          title = "Web Lambda 耗时 (ms)", region = var.region, period = 300, view = "timeSeries"
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", local.web_fn, { stat = "Average", label = "avg" }],
            ["AWS/Lambda", "Duration", "FunctionName", local.web_fn, { stat = "p95", label = "p95" }],
          ]
        }
      },
      {
        type = "metric", x = 8, y = 6, width = 8, height = 6
        properties = {
          title = "Web Lambda 并发 / 错误 / 限流", region = var.region, period = 300, view = "timeSeries"
          metrics = [
            ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", local.web_fn, { stat = "Maximum", label = "并发" }],
            ["AWS/Lambda", "Errors", "FunctionName", local.web_fn, { stat = "Sum", label = "错误", color = "#d62728" }],
            ["AWS/Lambda", "Throttles", "FunctionName", local.web_fn, { stat = "Sum", label = "限流" }],
          ]
        }
      },
      {
        type = "metric", x = 16, y = 6, width = 8, height = 6
        properties = {
          title = "每日邮件函数", region = var.region, period = 86400, view = "timeSeries"
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", local.daily_fn, { stat = "Sum", label = "调用" }],
            ["AWS/Lambda", "Errors", "FunctionName", local.daily_fn, { stat = "Sum", label = "错误", color = "#d62728" }],
          ]
        }
      },
      {
        type = "alarm", x = 0, y = 12, width = 24, height = 3
        properties = {
          title = "告警状态"
          alarms = concat(
            [aws_cloudwatch_metric_alarm.api_5xx_ratio.arn, aws_cloudwatch_metric_alarm.api_p95_latency.arn],
            [for a in aws_cloudwatch_metric_alarm.lambda_errors : a.arn],
          )
        }
      },
      {
        type = "log", x = 0, y = 15, width = 24, height = 8
        properties = {
          title  = "最近的 5xx 请求（JSON 日志）"
          region = var.region
          query  = "SOURCE '/aws/lambda/${local.web_fn}' | fields @timestamp, data.method, data.path, data.status, data.duration_ms, data.request_id | filter data.status >= 500 | sort @timestamp desc | limit 20"
          view   = "table"
        }
      },
    ]
  }
}

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = var.app_name
  dashboard_body = jsonencode(local.dashboard)
}

output "dashboard_url" {
  value = "https://${var.region}.console.aws.amazon.com/cloudwatch/home?region=${var.region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}
