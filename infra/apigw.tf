# ---------- API Gateway HTTP API ----------
# 给 Lambda 一个公网 https 入口，相当于 Nginx 反向代理。
# HTTP API 比老的 REST API 便宜 70%、延迟低，功能够用。
resource "aws_apigatewayv2_api" "app" {
  name          = var.app_name
  protocol_type = "HTTP"
}

# 后端集成：把请求原样转给 Lambda（AWS_PROXY = 不做任何转换）
resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.app.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.app.invoke_arn
  payload_format_version = "2.0"
}

# 路由：$default 匹配所有路径和方法，路由逻辑交给 FastAPI 自己
resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.app.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# 阶段：$default 阶段 + 自动部署，改了路由不用手动"发布"
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.app.id
  name        = "$default"
  auto_deploy = true
}

# 资源策略：允许 API Gateway 调用这个 Lambda。
# IAM 是双向的：Lambda 的角色管"它能调谁"，这条管"谁能调它"。
resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.app.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.app.execution_arn}/*/*"
}

output "api_url" {
  value = aws_apigatewayv2_api.app.api_endpoint
}
