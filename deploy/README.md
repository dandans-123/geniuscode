# GeniusCode 后端部署（日本 VPS + Docker + 自动 HTTPS）

网关本身不跑模型推理，所有推理转发给上游 aicodewith。资源需求很低：
**2 核 4G + 大带宽**，无 GPU。日本节点免 ICP 备案，建议选 CN2 GIA / 优化线路。

## 一、服务器准备

```bash
# Ubuntu/Debian，装 Docker
curl -fsSL https://get.docker.com | sh
# 放行端口（云厂商安全组也要放行 80/443）
```

DNS：把 `api.geniuscode.online` 的 **A 记录**指向服务器公网 IP（先解析好再启动，Caddy 要用它签证书）。

## 二、拉代码 + 配置

```bash
git clone https://github.com/dandans-123/geniuscode.git
cd geniuscode/deploy
cp .env.example .env
# 编辑 .env：
#   DOMAIN=api.geniuscode.online
#   AICODEWITH_API_KEY / AICODEWITH_BASE_URL（aicodewith 控制台拿）
#   JWT_SECRET、ADMIN_API_KEY 改成随机串：openssl rand -hex 32
vim .env
```

## 三、启动

```bash
docker compose up -d --build
docker compose logs -f app     # 看启动日志（建表 + seed 33 模型）
```

启动后：
- API：`https://api.geniuscode.online/v1/chat/completions`（OpenAI 兼容）
- 健康检查：`https://api.geniuscode.online/health`
- 接口文档：`https://api.geniuscode.online/docs`
- 会员接口：`/auth/register`、`/auth/login`、`/auth/membership/purchase`

首次访问 HTTPS 时 Caddy 会自动签发证书（几秒～几十秒）。

## 四、验证

```bash
curl https://api.geniuscode.online/health
# 注册一个会员（送体验额度）
curl -X POST https://api.geniuscode.online/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"secret123"}'
```

## 五、升级 / 运维

```bash
git pull && docker compose up -d --build   # 更新
docker compose restart app                 # 重启
docker compose down                        # 停止
```

- **数据**：SQLite 在 `deploy/data/geniuscode.db`，定期备份该文件即可。
- **证书**：在 `caddy_data` 卷里，勿随意删卷（频繁重签会触发 Let's Encrypt 限流）。

## 注意事项 / 后续

- **单进程 + SQLite** 足够起步。上量后：换 PostgreSQL（托管 DB）+ 多 worker / 多实例，再在 Caddy 后做负载均衡。
- **带宽是主要成本**：出网流量 ≈ 所有模型输出 token 之和，选大带宽 / 不限量套餐。
- **支付目前是桩**：`membership.purchase_membership` 默认支付成功，接真实支付（支付宝/微信/Stripe）后再放开购买入口。
- **前端**：GitHub Pages 上的站点调用本 API，跨域已在 `CORS_ORIGINS` 放行；登录页/控制台 wiring 待接。
