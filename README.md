# fastapi-service

[![CI](https://github.com/cancannewbie/fastapi-service/actions/workflows/ci.yml/badge.svg)](https://github.com/cancannewbie/fastapi-service/actions/workflows/ci.yml)

使用 FastAPI、SQLAlchemy async、PostgreSQL 和 uv 的任务管理服务，包含用户注册、OAuth2 密码登录、JWT 鉴权及任务管理页面。

## 使用 Docker Compose

```bash
cp .env.example .env
```

为 `.env` 中的 `FASTAPI_JWT_SECRET` 设置独立的随机密钥，例如使用下面的命令生成，然后将输出填入 `.env`：

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
```

```bash
make up
```

打开 http://127.0.0.1:8000/ 注册账号并管理任务；API 文档位于 http://127.0.0.1:8000/docs。Compose 会等待 PostgreSQL 健康、运行 Alembic 迁移，然后启动应用。`make logs` 查看日志；`make down` 停止容器并保留数据库卷。

`APP_PORT` 和 `POSTGRES_PORT` 可分别配置宿主机端口，默认是 8000 和 5433。应用容器通过 Compose 网络中的 `postgres:5432` 连接数据库。若更改了数据库宿主机端口，本机运行服务时也要同步修改 `FASTAPI_DATABASE_URL`。

## 本机开发

```bash
uv sync
make db-up
make migrate
make dev
```

服务默认使用 `localhost:5433` 的 PostgreSQL。`make db-up` 只启动 PostgreSQL；`make db-down` 与 `make down` 都会停止整个 Compose 项目。

## 账号和任务 API

API 前缀默认为 `/api/v1`，可通过 `FASTAPI_API_PREFIX` 修改。注册使用 `POST /auth/register`，请求 JSON 为 `{"username":"alice","password":"至少8位密码"}`。登录使用 `POST /auth/token`，提交 OAuth2 表单字段 `username` 和 `password`，获取 bearer token；`GET /auth/me` 返回当前用户。任务接口均需要 `Authorization: Bearer <token>`：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET / POST | `/api/v1/tasks` | 列出 / 创建当前用户的任务 |
| GET / PATCH / DELETE | `/api/v1/tasks/{id}` | 查看 / 修改 / 删除当前用户的任务 |

任务包含 `title`、可选 `description`、`status`（`todo`、`in_progress`、`done`）及创建时间。用户无法访问其他用户的任务。

迁移保留原有的 `items` 数据表及其记录，但新 API 和页面使用 `tasks`；旧记录不会自动归属于用户或转换为任务。

## 配置与部署

完整示例见 [.env.example](.env.example)。应用从环境变量或工作目录下的 `.env` 读取配置；Compose 的应用服务也会读取可选的 `.env`。

- `FASTAPI_JWT_SECRET`：JWT 签名密钥。生产环境必须设置高熵随机值，所有副本和进程需使用同一个密钥。未设置时，每个进程随机生成密钥，重启或切换副本会使令牌失效。
- `FASTAPI_JWT_EXPIRE_MINUTES`：令牌有效期，默认 30 分钟。
- `FASTAPI_DATABASE_URL`：SQLAlchemy 连接串，本机默认 `postgresql+psycopg://postgres:postgres@localhost:5433/fastapi_service`。
- `FASTAPI_DB_POOL_SIZE` / `FASTAPI_DB_MAX_OVERFLOW`：每个应用进程的连接池大小及额外连接数，默认分别为 5 和 10；`pool_pre_ping` 保持启用。部署多个副本或 worker 时，按进程数乘以两者之和，预留迁移及其他连接，确保不超过 PostgreSQL 的连接上限。`pool_size=0` 和 `max_overflow=-1` 表示无限制，通常不适合生产环境。

密码以 Argon2 哈希保存。密码登录和 bearer token 应通过 HTTPS 使用；公开部署前还应配置适合业务的注册策略、登录限流及反向代理。前端令牌仅保存在页面内存中，刷新页面后需要重新登录。

## 迁移、测试与 CI

```bash
make migrate
uv run alembic revision --autogenerate -m "describe change"
make check
```

测试使用真实 PostgreSQL：设置 `TEST_DATABASE_URL` 时使用该数据库，否则在 Python 3.12 下使用 `pgserver` 启动独立实例。测试会执行迁移并清空测试表，**不要将 `TEST_DATABASE_URL` 指向包含需要保留数据的数据库**。Python 3.13 需要显式设置该变量。

GitHub Actions 在 Python 3.12 和 3.13 上运行 `make check`。容器工作流为 PR 构建镜像；推送到 `main` 时构建并发布 `ghcr.io/cancannewbie/fastapi-service`，标签为 `latest` 和完整提交 SHA。首次发布后的镜像可见性取决于 GitHub Packages 设置。

## 常用命令

```bash
make up          # 构建并启动完整服务
make down        # 停止服务，保留数据库卷
make logs        # 跟踪容器日志
make migrate     # 应用迁移
make check       # ruff、mypy、pytest
make docker-build
```
