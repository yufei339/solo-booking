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

# 只保留最近 3 个镜像：ECR 免费额度 500 MB/月，每次部署都推一个新 tag，不清理会慢慢超出。
# 保留 3 个足够回滚；latest 标签始终指向最新那个。
resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "keep last 3 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 3
      }
      action = { type = "expire" }
    }]
  })
}
