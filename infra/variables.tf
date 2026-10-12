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
