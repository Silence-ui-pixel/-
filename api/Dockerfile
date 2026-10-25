FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Shanghai

WORKDIR /app

# 先只拷依赖声明并安装，再拷业务代码。
# 这样改业务代码时不会触发依赖层重建 —— 冷启动从分钟级降到秒级。
# pip 用清华镜像 + 拉长超时：国内直连 PyPI 官方源经常 read timed out，
# 构建失败基本都是网络问题，不是代码问题。
COPY pyproject.toml ./
RUN pip install --upgrade pip && \
    pip install -e ".[dev]" \
        -i https://pypi.tuna.tsinghua.edu.cn/simple \
        --timeout 120 --retries 5

COPY . .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
