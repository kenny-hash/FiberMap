# FiberMap

FiberMap 是一个面向内部业务网络的资产视角拓扑映射平台。MVP 采用 **FastAPI + React + PostgreSQL** 的产品形态设计，当前本地开发默认使用 SQLite，生产/集成环境可通过 `FIBERMAP_DATABASE_URL` 切换到 PostgreSQL。

## MVP 范围

- 设备导入/导出：优先支持 CSV 与 Excel。
- 设备字段：`ip`、`type`、`protocol`、`port`、`username`、`password`、`name`（RFID/名称）。
- 智能默认值：交换机默认 telnet/23，服务器与存储默认 ssh/22。
- 设备类型固定为 `switch` / `host` / `storage`。
- 拓扑展示：以资产节点为中心展示设备与链路证据。
- 拓扑快照：保留历史快照，并记录新增/删除节点与链路 diff。
- 采集任务 API：保留 API 服务 + Worker + 任务队列演进接口，MVP 中同步生成快照。
- 多集群数据模型：设备、任务、快照均归属 `cluster_id`。

## 导入清单格式

| 字段名称 | 内部 Key | 必填 | 说明 |
| --- | --- | --- | --- |
| IP 地址 | `ip` | 是 | 设备管理平面 IP。 |
| 设备类型 | `type` | 是 | `switch` / `host` / `storage`。 |
| 协议 | `protocol` | 否 | `ssh` 或 `telnet`；留空按设备类型推断。 |
| 端口 | `port` | 否 | 留空按协议推断 22 或 23。 |
| 账号 | `username` | 否 | 登录凭证。 |
| 密码 | `password` | 否 | MVP 按需求持久化保存；后续建议加密和权限审计。 |
| RFID / 名称 | `name` | 否 | 资产编号或自定义展示名称，也兼容 `rfid` 列。 |

## 本地运行

### 一键启动

```bash
./scripts/start_local.sh
```

脚本会自动同步后端依赖、安装前端依赖，并同时启动 FastAPI 与 Vite 开发服务。默认地址：

- 前端：`http://localhost:5173`
- 后端：`http://127.0.0.1:8000`
- 健康检查：`http://127.0.0.1:8000/api/health`

常用环境变量：

- `FIBERMAP_SKIP_INSTALL=1`：跳过依赖安装，适合依赖已安装后的快速重启。
- `FIBERMAP_BACKEND_HOST=0.0.0.0`：修改后端监听地址；当监听地址是 `0.0.0.0` 或 `::` 时，脚本默认向浏览器注入 `localhost` 作为可访问的 API 主机。
- `FIBERMAP_BACKEND_CLIENT_HOST=192.168.1.10`：单独指定浏览器访问后端时使用的主机名或 IP。
- `FIBERMAP_API_BASE=http://192.168.1.10:8000`：完整覆盖前端使用的后端 API 基础地址。
- `FIBERMAP_BACKEND_PORT=8001`：修改后端监听端口。
- `FIBERMAP_FRONTEND_PORT=5174`：修改前端监听端口。

### 后端

```bash
uv sync --dev
uv run uvicorn app.main:app --app-dir backend --reload
```

后端默认监听 `http://127.0.0.1:8000`，健康检查：`GET /api/health`。

如需使用 PostgreSQL：

```bash
export FIBERMAP_DATABASE_URL='postgresql+psycopg://user:password@127.0.0.1:5432/fibermap'
uv run uvicorn app.main:app --app-dir backend --reload
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端开发服务通过 Vite 将 `/api` 代理到后端。

## 测试与 CI

GitHub Actions 会执行：

- 后端 Ruff lint；
- 后端单元测试；
- CSV / Excel 导入测试；
- API 冒烟测试；
- 前端 ESLint；
- 前端 TypeScript + Vite 构建。

本地可运行：

```bash
uv run ruff check backend scripts
uv run pytest
FIBERMAP_DATABASE_URL=sqlite:///./smoke.db uv run python scripts/smoke_api.py
cd frontend && npm run lint && npm run build
```

## 拓扑发现设计说明

MVP 当前将“采集证据”和“拓扑构图”解耦：后端已经提供设备、端口、快照、采集任务模型，演示路径可通过端口 MAC 证据构造链路。后续真实采集建议按以下优先级融合证据：

1. 交换机 LLDP 邻居信息：高置信度，但覆盖不完整。
2. 交换机 MAC 地址表：适合发现未启用 LLDP 的主机/存储，但需处理主机未发包导致的空缺。
3. 服务器/存储登录采集：补充业务网卡、bond/聚合、VLAN、速率、链路状态。
4. 周期性采集任务：按集群定时维护拓扑快照，并在 diff 中呈现变化。

## 权限与安全演进

当前 MVP 先完成展示闭环。面向生产演进时建议增加：

- RBAC 用户、角色、集群级数据访问权限；
- 密码字段加密、密钥轮转、访问审计；
- 异步 Worker 与任务队列；
- PostgreSQL migration 管理；
- Electron 打包所需的本地启动器与配置导入导出。
