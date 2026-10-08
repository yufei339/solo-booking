# ---------- GitHub Actions 免密钥部署（OIDC） ----------
# 原理：GitHub 给每次 job 签短期 JWT，AWS 校验后换临时凭证。

variable "github_repo" {
  type    = string
  default = "yufei339/solo-booking"
}

# 1. 登记 GitHub 这个"签发方"
resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
  # GitHub 的根证书指纹；AWS 现在对 GitHub 已改为按根 CA 校验，这两个值只是 API 仍要求填
  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd",
  ]
}

# 2. 信任策略：只有本仓库 main 分支签出的 JWT 才能扮演这个角色
data "aws_iam_policy_document" "github_assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }
    # aud：这张 token 必须是签给 AWS STS 的
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    # sub：仓库 + 分支精确匹配。
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repo}:ref:refs/heads/main"]
    }
  }
}

resource "aws_iam_role" "github_actions" {
  name               = "${var.app_name}-github-actions"
  assume_role_policy = data.aws_iam_policy_document.github_assume.json
}

output "github_actions_role_arn" {
  value = aws_iam_role.github_actions.arn
}

# 3. 最小权限：只能推这一个 ECR 仓库、改这一个 Lambda 函数
data "aws_iam_policy_document" "github_deploy" {
  # docker login 用的临时口令；这个动作不支持按资源限制
  statement {
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }
  # 推镜像：分层上传 + 写 manifest；BatchGetImage/GetDownloadUrlForLayer 给 buildx 复用已有层
  statement {
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload",
      "ecr:PutImage",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
    ]
    resources = [aws_ecr_repository.app.arn]
  }
  # 换 Lambda 镜像，以及 wait function-updated 轮询用的读权限
  statement {
    actions = [
      "lambda:UpdateFunctionCode",
      "lambda:GetFunction",
      "lambda:GetFunctionConfiguration",
    ]
    resources = [aws_lambda_function.app.arn]
  }
}

resource "aws_iam_role_policy" "github_deploy" {
  name   = "deploy"
  role   = aws_iam_role.github_actions.id
  policy = data.aws_iam_policy_document.github_deploy.json
}