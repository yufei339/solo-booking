# 私有镜像仓库，相当于自己的 Docker Hub
resource "aws_ecr_repository" "app" {
  name                 = var.app_name
  image_tag_mutability = "MUTABLE"
  force_delete         = true # 项目结束 destroy 时连镜像一起删
  image_scanning_configuration {
    scan_on_push = true
  }
}

output "ecr_repository_url" {
  value = aws_ecr_repository.app.repository_url
}
