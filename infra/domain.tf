# ---------- 自定义域名：Cloudflare DNS + ACM 证书 + API Gateway 域名绑定 ----------
# 域名在 Cloudflare 注册。Cloudflare Registrar 不允许改 nameserver（自定义 NS 要付费版），
# 所以 DNS 记录就放 Cloudflare，由 Terraform 通过 Cloudflare provider 写入；证书和域名绑定在 AWS。
# 一次 apply 跨两家云，这就是多 provider。

locals {
  app_host = "${var.app_subdomain}.${var.domain_name}" # book.yufeichen.dev
}

# 证书：免费，DNS 验证（在 DNS 里放一条 CNAME 证明域名是你的）。
# HTTP API 的自定义域名是 Regional 的，证书必须在同一个区域（ca-central-1）。
resource "aws_acm_certificate" "app" {
  domain_name       = local.app_host
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true # 换证书时先建新的再删旧的，不断服务
  }
}

# 验证记录写到 Cloudflare。proxied=false 表示纯 DNS，不经过 Cloudflare 的反向代理。
resource "cloudflare_dns_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.app.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }
  zone_id = var.cloudflare_zone_id
  name    = trimsuffix(each.value.name, ".") # ACM 给的名字带末尾的点，Cloudflare 不要
  type    = each.value.type
  content = trimsuffix(each.value.record, ".")
  ttl     = 300
  proxied = false
  comment = "ACM validation for ${local.app_host}"
}

# 等 ACM 看到验证记录、把证书签出来（通常几分钟）。
resource "aws_acm_certificate_validation" "app" {
  certificate_arn         = aws_acm_certificate.app.arn
  validation_record_fqdns = [for r in cloudflare_dns_record.cert_validation : r.name]
}

# API Gateway 这边：登记这个域名 + 证书，再把 $default 阶段映射上去
resource "aws_apigatewayv2_domain_name" "app" {
  domain_name = local.app_host

  domain_name_configuration {
    certificate_arn = aws_acm_certificate_validation.app.certificate_arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }
}

resource "aws_apigatewayv2_api_mapping" "app" {
  api_id      = aws_apigatewayv2_api.app.id
  domain_name = aws_apigatewayv2_domain_name.app.id
  stage       = aws_apigatewayv2_stage.default.id
}

# DNS：book.yufeichen.dev → API Gateway 的区域域名。
# 必须 proxied=false：开了 Cloudflare 代理会由 Cloudflare 终止 TLS，和 API Gateway 的证书打架。
resource "cloudflare_dns_record" "app" {
  zone_id = var.cloudflare_zone_id
  name    = local.app_host
  type    = "CNAME"
  content = aws_apigatewayv2_domain_name.app.domain_name_configuration[0].target_domain_name
  ttl     = 300
  proxied = false
  comment = "solo-booking → API Gateway"
}

output "app_url" {
  value = "https://${local.app_host}"
}
