terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = { project = "solo-booking" }
  }
}

# 域名在 Cloudflare 注册，它不允许改 NS，所以 DNS 记录也由 Cloudflare 托管、Terraform 通过 API token 写入
provider "cloudflare" {
  api_token = var.cloudflare_api_token
}
