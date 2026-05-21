# ModelMux UI 重做方案 — Stage 1 (设计语言)

> 受众: CEO / Stage 2 工程师 · 范围: `index.html` 三页 (landing/recommend/chat), 不引入构建工具

## 1. flock.io 解构 (从 WebFetch 提取)

| 维度 | flock.io platform 实测/推断 |
|---|---|
| 主题 | **亮主题** (白底深字), 与我们当前暗主题方向相反 |
| 主色 | `#0066CC` 类深蓝/青 (CTA、品牌, [WebFetch 受限, 推断]) |
| 辅色 | `#00CC88` 类绿色 (折扣/活跃标签) |
| 中性色 | 白底 `#FFFFFF`、深文 `#0F172A` 级、灰文 `#64748B` 级 [推断] |
| 字体 | 系统栈或 Inter/Helvetica 类 sans, 未声明自定义字体 [推断] |
| 字重层级 | H1 ~48–64 / 700 · H2 ~32–40 / 600 · body 16 / 400 · btn 14–16 / 600 |
| Section 节奏 | 上下 padding ~60–80 px, line-height 1.5–1.6, 卡片 gap 24–32 px |
| 信息密度 | 每屏 3–4 块: Hero → 模型轮播 → 卡片网格 → 优势 → 合作 logo → 价格 → CTA |
| Hero | 标题 "Your Powerful AI Models Hub" + 副标 + "View Documentation" CTA, 配模型缩略轮播, **无代码块** |
| Feature/Model cards | 网格, 每卡含 logo + 名称 + 描述 + Input/Output 价格 + 链接, 折扣徽章 `-75% OFF` |
| Pricing | 分布式 (随模型卡内嵌), `$X / MTok` 单位, 非独立大表 |
| Footer | 三列: Brand+社交 / Developer / Connect, 底部版权 |
| 微交互 | 推断 hover 轻微提升 + 颜色过渡, 折扣徽章可能渐变 [推断] |
| 氛围词 | **专业、克制、产品目录感** |

> 备注: `https://flock.io/` 返回 429, `/pricing` 404, 颜色 hex 因 CSS 未暴露均为视觉推断, Stage 2 实施前建议人工截图二次校准。

## 2. ModelMux 当前 vs 目标 (差距表)

| 维度 | 当前 (index.html) | 目标 (参 flock.io) | 改造力度 |
|---|---|---|---|
| 主题基调 | Landing hero/CTA/footer 暗 navy, 中段亮; 三种风格切换割裂 | **统一亮主题** 全站, 仅 code block 局部暗 | 高 |
| 主色 | `--blue:#2563eb` + `--purple:#7c3aed` + `--gold:#d4a843` 三色齐飞 | 收敛为 **一主一辅** (深蓝主 + 绿辅) | 中 |
| Hero | h1 3.5rem + 渐变三色文字 + 粒子动画 + 网格底 + 双 CTA + 统计条 | 简化: 标题 + 副标 + 单 CTA + **代码块视觉锚点** (差异化, 我们是 API 不是模型目录) | 高 |
| 视觉装饰 | radial-gradient × 2 + grid bg + 6 粒子动画 + pulse 圆点 | 全部移除, 仅留 1 处微妙渐变作为强调 | 中 |
| Features | 3 张 + 4 张 supply + 2×N cap, **共 ~11 张卡片**, 信息过载 | **3 张核心 feature**, 不再 supply/cap 重复 | 高 |
| 代码示例 | **完全缺失** (开发者产品却不见代码) | Hero 旁或独立 section: Python/Node/curl tab + 复制按钮 | 高 |
| Trust bar | 缺失 | 灰阶 logo 行 (OpenAI/Anthropic/Google/DeepSeek/Kimi) | 中 |
| Pricing | landing 无, 仅 recommend 页结尾价格 | landing 加 **3 档简版** (Free / Pro / Enterprise) | 中 |
| Docs link | 缺失 | Footer 上方独立 cross-link section | 低 |
| Footer | 单行 logo + 版权, 信息稀薄 | **三列**: Brand / Developer / Connect | 低 |
| 字体栈 | 系统栈 (`SF Pro Display`, `PingFang SC`) | 保持系统栈, 不引入 Google Fonts (性能 > 美感) | 0 |
| 圆角 | `--r:12px` 单档 | scale: 4 / 8 / 12 | 低 |

## 3. 整页骨架 (Landing, 从上到下)

1. **Header** — 固定顶, 白底毛玻璃, logo + 4 链接 (Models / Docs / Pricing / Chat) + 主 CTA "Get API Key"
2. **Hero** — 标题 (中英双语保留) + 一句副标 + 单主 CTA + 次要 "Read Docs", **右侧或下方代码块** (3 行 curl 调用) 作视觉锚点
3. **Trust bar (logos)** — "Powered by" + 灰阶 6–8 个模型厂商 logo, 单行横排
4. **Code snippet showcase** — 独立 section, tab 切换 Python / Node / cURL, 暗色代码块带行号 + 复制按钮, 右侧文案解释 "一个 key 接入 30+ 模型"
5. **Features (3 张)** — 智能路由 / 成本透明 / Drop-in 兼容; 每卡 icon + 标题 + 60 字描述, 不再六大模块
6. **How it works (3 步)** — 拿 key → 改 baseURL → 享受路由; 横向编号 + 箭头
7. **Pricing 简版** — 3 档卡片 (Free $0 / Pro $19 / Enterprise 联系), 中间档高亮蓝边
8. **Docs cross-link** — 单行大块 "完整文档、SDK、Webhook 都在这里" + 右侧大箭头按钮
9. **Footer** — 三列 (Brand+社交 / Developer / Connect) + 底部版权和 ICP

## 4. Design tokens (即将进 CSS)

- **主色**: `#2563EB` (保留当前 blue, 与 flock 调性相近, 沉淀感)
- **辅色**: `#059669` (绿色, 用于 "online" / 成功 / 高亮档位; 替换 gold 的主导地位, gold 降为强调)
- **强调色**: `#D4A843` (gold, 仅 hero 渐变和 Enterprise 徽章, 不超过 5% 视觉占比)
- **中性 4 档**: `#FFFFFF` / `#F8FAFC` / `#E2E8F0` / `#0F172A`
- **辅助灰**: `#64748B` (body 次要), `#94A3B8` (placeholder)
- **字体栈**: `-apple-system, BlinkMacSystemFont, "SF Pro Display", "Inter", "PingFang SC", "Microsoft YaHei", sans-serif`
- **Mono 字体**: `"SF Mono", "JetBrains Mono", Menlo, Consolas, monospace` (代码块)
- **字重**: h1 = 800, h2 = 700, h3 = 600, body = 400, button = 600
- **字号 (rem)**: h1 = 3rem (移动 2rem), h2 = 2rem, h3 = 1.25rem, body = 1rem, small = 0.875rem
- **间距 scale**: 4 / 8 / 16 / 24 / 40 / 64 / 96 px
- **圆角**: `--r-sm:4px` / `--r:8px` / `--r-lg:12px`
- **阴影 subtle**: `0 1px 3px rgba(15,23,42,.06), 0 1px 2px rgba(15,23,42,.04)`
- **阴影 pronounced**: `0 10px 30px rgba(15,23,42,.08), 0 4px 12px rgba(15,23,42,.04)`
- **过渡**: `all .2s ease`

## 5. 关键组件描述 (Stage 2 工程师参考)

1. **Hero** — h1 中英双行 (中文主, 英文小一号灰色副) · 副标 ≤30 字 · 主 CTA "免费获取 API Key" + 次 CTA "查看文档" · 右下方放浮起的代码 card (3 行 curl)
2. **Code snippet block** — 暗背景 `#0F172A`, 顶部 tab (Python / Node / cURL) + 右上复制按钮, 行号灰色, 关键字 syntax-highlight (蓝 string, 紫 keyword, 绿 number)
3. **Feature cards** — 3 张等宽, 白底 + 1px 边 + subtle shadow, hover 上浮 4px 加 pronounced shadow; icon 44×44 圆角 10, body ≤60 字
4. **Pricing** — 3 档, 中间 Pro 高亮 (`#2563EB` 边 + "RECOMMENDED" 徽章); 月费数字 800 字重 2.5rem
5. **Docs cross-link** — 单卡通栏, 左侧 emoji + 标题 + 一句话, 右侧箭头按钮; 不堆 sub-links
6. **Footer** — 3 列 grid, 每列标题 0.75rem 大写灰 + 链接列表; 底部分隔线后单行版权 + 邮箱 `hello@modelmux.com`

## 6. 暗 vs 亮主题

- **推荐**: **亮主题为主, 代码块和 chat 顶栏保留暗** (混合)
- **理由**: 开发者工具市场 (Stripe/Vercel/Resend/flock) 普遍亮主题, 信任感 + 文档友好; 暗主题留给代码 (开发者天然预期)
- **flock.io 用的是**: 亮主题
- **Trade-off**: 当前 hero 的暗 navy "气场" 会减弱, 需要靠代码块 + 严谨排版补足专业感

## 7. 移动端

- 断点: `768px` (tablet), `480px` (phone)
- Hero h1 scale: 3rem → 2.25rem → 1.75rem
- Section padding: 80px → 56px → 40px
- 所有按钮和导航 touch target ≥ 44 × 44 px
- Feature/Pricing 三列 → 单列纵向, gap 16px
- Header 链接折叠为汉堡, 移动端 CTA 保留可见

## 8. 改造执行计划 (给 Stage 2 工程师)

- **改一个文件**: `/Users/dan/ai_token_platform/index.html` (单文件 SPA, 内嵌 CSS)
- **同步**: 若 `backend/static/index.html` 存在, 改完拷贝一次
- **分块 patch 顺序**:
  1. `:root` tokens + body / container 基础 (30 分钟)
  2. Header + nav 改亮底 (30 分钟)
  3. Hero 重写, 加 code card (90 分钟)
  4. 新增 Trust bar + Code snippet showcase section (90 分钟)
  5. Features 从 11 卡精简到 3 卡 (60 分钟)
  6. How it works + Pricing 简版 (90 分钟)
  7. Docs cross-link + Footer 三列 (45 分钟)
  8. 移动端断点 + 联调 (60 分钟)
- **估工时**: **约 8–10 小时** (一个工程日)

## 9. 决策岔路 (给 CEO)

- **D1 主题色**: A `#2563EB` (保留当前蓝) vs B 换 flock 风 `#0066CC` 青蓝 — **推荐 A**, 沉淀已有品牌资产, 改色边际收益低
- **D2 字体**: A 系统栈 (零加载) vs B 引入 Google Fonts Inter — **推荐 A**, 性能优先且中文 fallback 已稳, Inter 与 SF Pro 在屏幕上差异极小
- **D3 主题**: A 全暗 (保留现状) vs B 全亮 (像 flock) vs C **亮为主, 代码/chat 局部暗** — **推荐 C**, 兼顾开发者工具专业感和当前 chat 页可读性

## 10. 风险 / 不确定

- flock.io 颜色/字体 hex 均为视觉推断 (CSS 未暴露), Stage 2 前建议人工截图取色二次校准
- `flock.io/` 主站 429, 未能取到首页样式; 当前依据 platform 子站
- 三色 (蓝/紫/金) 渐变是当前品牌识别点之一, 若全部移除可能损失"识别度", 方案是把渐变保留在 hero h1 关键词和 logo 上 (≤5% 占比)
- 代码块是核心新增组件, 高亮逻辑用 CSS span 手写还是引入 Prism.js (~10KB) 需 Stage 2 决策, **推荐手写** (避免引依赖)
