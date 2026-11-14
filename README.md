# fastapi-service

[![CI](https://github.com/cancannewbie/fastapi-service/actions/workflows/ci.yml/badge.svg)](https://github.com/cancannewbie/fastapi-service/actions/workflows/ci.yml)

一个用 [uv](https://docs.astral.sh/uv/) 管理、以 [FastAPI](https://fastapi.tiangolo.com/) + **SQLAlchemy 2.0 (async)** + **PostgreSQL** 为后端的 Web 服务骨架。

配套 Alembic 迁移、pytest 测试、ruff / mypy (strict)、GitHub Actions CI 和多阶段 Dockerfile。

## 快速开始

```bash
cd fastapi-service
uv sync                 # 安装依赖（含 dev 依赖）
make db-up              # 启动 Postgres（docker compose）
make migrate            # 应用数据库迁移
uv run fastapi-service  # 启动服务 → http://127.0.0.1:8000/docs
```

没有 Docker 也能跑 —— 测试会自动拉起一个内嵌的 PostgreSQL（见 [测试](#测试)）。

## 项目结构

```
fastapi-service/
├── src/fastapi_service/
│   ├── __init__.py      # 包入口
│   ├── app.py           # create_app() 应用工厂 + ASGI 实例
│   ├── cli.py           # 命令行入口（serve / migrate）
│   ├── config.py        # pydantic-settings 配置
│   ├── errors.py        # 统一错误响应封装
│   ├── schemas.py       # Pydantic 请求/响应模型
│   ├── db/
│   │   ├── base.py      # DeclarativeBase
│   │   ├── models.py    # ORM 模型（items 表）
│   │   ├── session.py   # engine / session factory / 依赖注入
│   │   └── repository.py# ItemRepository 协议 + SQLAlchemy 实现
│   └── api/
│       ├── health.py    # /health、/ready（ready 会探活数据库）
│       └── items.py     # /items CRUD
├── alembic/             # 迁移脚本
├── alembic.ini
├── compose.yaml         # 本地 Postgres
├── tests/               # pytest（async）
├── Dockerfile
├── Makefile
└── pyproject.toml
```

采用 `src/` 布局 + 依赖倒置：路由只依赖 `ItemRepository` 协议，换存储后端不用动路由。

## API

| 方法   | 路径                  | 说明                    |
| ------ | --------------------- | ----------------------- |
| GET    | `/health`             | 存活探针                |
| GET    | `/ready`              | 就绪探针（会查数据库）  |
| GET    | `/api/v1/items`       | 列出条目                |
| POST   | `/api/v1/items`       | 创建条目                |
| GET    | `/api/v1/items/{id}`  | 获取条目                |
| PATCH  | `/api/v1/items/{id}`  | 局部更新                |
| DELETE | `/api/v1/items/{id}`  | 删除条目                |

错误统一返回：

```json
{ "error": { "code": "not_found", "message": "Item 999 does not exist" } }
```

请求校验失败（422）会额外带上 `details` 列表。

## 配置

全部来自环境变量（前缀 `FASTAPI_`）或项目根目录的 `.env`，参见 [.env.example](.env.example)：

| 变量                        | 默认值                                                              | 说明                     |
| --------------------------- | ------------------------------------------------------------------- | ------------------------ |
| `FASTAPI_APP_NAME`          | `fastapi-service`                                                   | 应用名，也是 OpenAPI 标题 |
| `FASTAPI_DEBUG`             | `false`                                                             | 调试模式                 |
| `FASTAPI_API_PREFIX`        | `/api/v1`                                                           | 业务路由前缀             |
| `FASTAPI_HOST`              | `127.0.0.1`                                                         | 监听地址                 |
| `FASTAPI_PORT`              | `8000`                                                              | 监听端口                 |
| `FASTAPI_RELOAD`            | `false`                                                             | 是否开启热重载           |
| `FASTAPI_CORS_ORIGINS`      | `["http://localhost:3000"]`                                         | 跨域来源（JSON 数组）    |
| `FASTAPI_DATABASE_URL`      | `postgresql+psycopg://postgres:postgres@localhost:5432/fastapi_service` | SQLAlchemy 连接串  |
| `FASTAPI_DB_ECHO`           | `false`                                                             | 打印 SQL                 |
| `FASTAPI_DB_CHECK_ON_STARTUP` | `true`                                                            | 启动时探活数据库         |

数据库驱动用 **psycopg3**（`postgresql+psycopg://`，SQLAlchemy 官方推荐的现代驱动）；
换成 asyncpg 只需把 URL 改成 `postgresql+asyncpg://`，代码不用动。

`FASTAPI_DB_CHECK_ON_STARTUP=true` 时，连不上数据库会让进程**启动即失败**并给出明确报错，
而不是等第一个请求进来才 500 —— 容器编排下这行为更合适。

## 数据库与迁移

表结构（`items`）：

| 列            | 类型              | 约束              |
| ------------- | ----------------- | ----------------- |
| `id`          | `integer`         | 主键，自增        |
| `name`        | `varchar(100)`    | 非空              |
| `description` | `varchar(1000)`   | 可空              |
| `price`       | `numeric(12, 2)`  | 非空（金额用精确小数，不用 float）|
| `created_at`  | `timestamptz`     | 非空，默认 `now()`|

```bash
make migrate                        # alembic upgrade head
uv run alembic revision --autogenerate -m "add x"   # 生成新迁移
uv run alembic downgrade -1         # 回滚一版
```

迁移脚本和运行时读的是同一个 `FASTAPI_DATABASE_URL`，不会出现「迁移到 A、服务连 B」。

## 测试

测试**永远跑在真 PostgreSQL 上**，不是 mock：

- 设了 `TEST_DATABASE_URL` 就用它（CI 指向 service container）；
- 否则用 [pgserver](https://pypi.org/project/pgserver/) 拉起一个内嵌 PostgreSQL —— **不需要 Docker**。
  pgserver 只发布了 CPython ≤ 3.12 的 wheel，所以在 3.13 上必须设 `TEST_DATABASE_URL`。

每次跑测试都会先执行一遍 Alembic 迁移，所以迁移脚本本身也在测试覆盖范围内。

```bash
uv run pytest                 # 10 个用例
TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/mydb uv run pytest
```

## 常用命令

```bash
make install     # uv sync
make db-up       # docker compose 起 Postgres
make db-down     # 停掉
make migrate     # 应用迁移
make test        # pytest
make lint        # ruff check + format --check
make format      # ruff format + --fix
make typecheck   # mypy（strict）
make check       # lint + typecheck + test
```

## CI

[.github/workflows/ci.yml](.github/workflows/ci.yml) 在 push 到 `main`、pull request 或手动触发时运行，
在 Python 3.12 / 3.13 上用 `services:` 起一个 Postgres 容器，执行 `make check`。

- `uv` 由 [astral-sh/setup-uv](https://github.com/astral-sh/setup-uv) 安装并开启缓存
- 依赖用 `uv sync --locked --all-groups` 安装；`uv.lock` 与 `pyproject.toml` 不一致时直接失败
- action 版本锁定到精确 tag（`setup-uv@v10.3.3`、`checkout@v7.0.1`）—— `setup-uv` 没有 `v10` 这种浮动 tag

## Docker

```bash
docker build -t fastapi-service .
docker run --rm -p 8000:8000 -e FASTAPI_DATABASE_URL=postgresql+psycopg://... fastapi-service
```

镜像为多阶段构建，以非 root 用户运行，依赖由 `uv.lock` 固定。镜像里带了 `alembic.ini`，
可以直接 `docker run ... fastapi-service migrate` 执行迁移。

## 下一步

- 加鉴权（OAuth2 / JWT）和用户表
- 把 `items` 换成自己的领域模型，换 `alembic revision --autogenerate` 生成迁移
- CI 里加镜像构建和推送
- 需要多副本部署时给连接池加上限（`pool_size` / `max_overflow`），并注意 `pool_pre_ping` 已开启
