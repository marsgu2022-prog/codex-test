# bazichart-engine

开发启动：

```bash
./start.sh
```

脚本会先安装 `requirements.txt` 中的依赖，再启动 FastAPI 服务。

API 地址：

- `http://localhost:8000`
- 健康检查：`GET /api/health`
- PDF 下载：`POST /api/report/pdf`

前端联调 CORS 已允许：

- Origin：`http://localhost:3003`
- Methods：`POST, GET, OPTIONS`
- Headers：`Content-Type`
