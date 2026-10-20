variable "region" {
  type    = string
  default = "ca-central-1"
}

variable "app_name" {
  type    = string
  default = "solo-booking"
}

variable "image_tag" {
  type        = string
  default     = "latest"
  description = "首次创建 Lambda 时用的镜像 tag；之后由 CI 更新"
}

# 两个密钥：值放在 infra/terraform.tfvars（已被 .gitignore 排除），不进仓库。
# sensitive = true 让 plan/apply 输出里打码。
variable "admin_password" {
  type        = string
  sensitive   = true
  description = "教练后台登录密码"
}

variable "session_secret" {
  type        = string
  sensitive   = true
  description = "签名登录 Cookie 的密钥，泄露等于能伪造登录态"
}

variable "coach_email" {
  type        = string
  description = "SES 验证的邮箱：每日课表的发件人兼收件人（沙盒期间）"
}

variable "domain_name" {
  type        = string
  default     = "yufeichen.dev"
  description = "在 Cloudflare 注册的根域名；DNS 托管在 Route53"
}

variable "app_subdomain" {
  type        = string
  default     = "book"
  description = "约课系统挂的子域名，最终网址 https://book.yufeichen.dev"
}

variable "cloudflare_api_token" {
  type        = string
  sensitive   = true
  description = "Cloudflare API token，权限只需 Zone:DNS:Edit，限定 yufeichen.dev"
}

variable "cloudflare_zone_id" {
  type        = string
  description = "Cloudflare 里 yufeichen.dev 的 Zone ID（域名 Overview 页右侧）"
}
