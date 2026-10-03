FROM public.ecr.aws/docker/library/python:3.12-slim

# Lambda Web Adapter：在 Lambda 里把事件翻译成 HTTP
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:1.1.0 /lambda-adapter /opt/extensions/lambda-adapter

# 把 uv 拷进镜像，装依赖
COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /bin/uv

WORKDIR /app


COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev


COPY app ./app

ENV PATH="/app/.venv/bin:$PATH" \
    PORT=8080 \
    AWS_LWA_READINESS_CHECK_PATH=/health

EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]