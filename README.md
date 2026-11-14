# fastapi-service

[![CI](https://github.com/OWNER/fastapi-service/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/fastapi-service/actions/workflows/ci.yml)

一个用 [uv](https://docs.astral.sh/uv/) 管理、以 [FastAPI](https://fastapi.tiangolo.com/) 为框架的 Web 服务骨架。

## 快速开始

```bash
cd fastapi-service
uv sync            # 安装依赖（含 dev 依赖）
uv run fastapi-service   # 启动服务，默认 http://127.0.0.1:8000
```

开发模式（热重载）：

```bash
uv run uvicorn fastapi_service.app:app --reload
```

交互式 API 文档：http://127.0.0.1:8000/docs

## 项目结构

```
fastapi-service/
├── src/fastapi_service/
│   ├── __init__.py      # 包入口，惰性导出 create_app / app
│   ├── app.py           # create_app() 应用工厂 + ASGI 实例 app
│   ├── cli.py           # 命令行入口 fastapi-service
│   ├── config.py        # pydantic-settings 配置（环境变量 FASTAPI_* 前缀）
│   ├── errors.py        # 统一错误响应封装
│   ├── schemas.py       # 请求/响应 Pydantic 模型
│   └── api/
│       ├── __init__.py  # 路由汇总
│       ├── health.py    # /health、/ready 探针
│       └── items.py     # /items CRUD + 内存仓储
├── tests/               # pytest 测试
├── Dockerfile
├── Makefile             # make test / lint / typecheck / dev
├── pyproject.toml       # 依赖 + ruff/mypy/pytest 配置
└── uv.lock
```

采用 `src/` 布局：源码不进工作目录，只有从包目录导入，避免测试误导入本地模块。

## API

| 方法   | 路径             | 说明         |
| ------ | ---------------- | ------------ |
| GET    | `/health`        | 存活探针     |
| GET    | `/ready`         | 就绪探针     |
| GET    | `/api/v1/items`  | 列出条目     |
| POST   | `/api/v1/items`  | 创建条目     |
| GET    | `/api/v1/items/{id}` | 获取条目  |
| PATCH  | `/api/v1/items/{id}` | 局部更新  |
| DELETE | `/api/v1/items/{id}` | 删除条目  |

错误统一返回：

```json
{ "error": { "code": "not_found", "message": "Item 999 does not exist" } }
```

请求校验失败（422）会额外带上 `details` 列表。

## 配置

所有配置来自环境变量（前缀 `FASTAPI_`）或项目根目录的 `.env`，参见 [.env.example](.env.example)：

| 变量                    | 默认值                        | 说明                     |
| ----------------------- | ----------------------------- | ------------------------ |
| `FASTAPI_APP_NAME`      | `fastapi-service`             | 应用名，同时是 OpenAPI 标题 |
| `FASTAPI_DEBUG`         | `false`                       | 调试模式                 |
| `FASTAPI_API_PREFIX`    | `/api/v1`                     | 业务路由前缀             |
| `FASTAPI_HOST`          | `127.0.0.1`                   | 监听地址                 |
| `FASTAPI_PORT`          | `8000`                        | 监听端口                 |
| `FASTAPI_RELOAD`        | `false`                       | 是否开启热重载           |
| `FASTAPI_CORS_ORIGINS`  | `["http://localhost:3000"]`   | 允许的跨域来源（JSON 数组） |

## 常用命令

```bash
make install     # uv sync
make test        # pytest
make lint        # ruff check + format --check
make format      # ruff format + --fix
make typecheck   # mypy（strict）
make check       # lint + typecheck + test
```

## CI

[.github/workflows/ci.yml](.github/workflows/ci.yml) 在 push 到 `main`、pull request 或手动触发时运行，
在 Python 3.12 / 3.13 上执行 `make check`（lint + typecheck + test）：

- `uv` 由 [astral-sh/setup-uv](https://github.com/astral-sh/setup-uv) 安装并开启缓存
- 依赖用 `uv sync --locked --all-groups` 安装；`uv.lock` 与 `pyproject.toml` 不一致时直接失败
- 任一步失败即该 job 失败

> README 顶部的徽章里的 `OWNER` 需要替换成你的 GitHub 用户名/组织名（仓库地址确定后再改）。

## Docker

```bash
docker build -t fastapi-service .
docker run --rm -p 8000:8000 fastapi-service
```

镜像为多阶段构建：以非 root 用户运行，依赖由 `uv.lock` 固定。

## 下一步

- 把 `api/items.py` 里的 `InMemoryItemRepository` 换成真实数据库实现（方法签名保持一致即可）
- 需要鉴权时加 `fastapi-users` 或 OAuth2 依赖
- 部署：把 `Dockerfile` 接到 CI 构建并推送到镜像仓库
