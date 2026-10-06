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
