from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

import json

from app.models.provider import Provider
from app.models.model import Model
from app.models.routing_rule import RoutingRule
from app.models.api_key import ApiKey
from app.models.budget import Budget
from app.models.knowledge_base import KnowledgeBase, Document


# 唯一上游 = aicodewith（OpenAI 兼容中转）。所有模型都转发到这里。
# base_url 以 aicodewith 控制台/接入文档为准；key 走 AICODEWITH_API_KEY 环境变量。
PROVIDERS = [
    {"name": "aicodewith", "base_url": "https://api.aicodewith.com/v1", "api_key_env_var": "AICODEWITH_API_KEY"},
]

# 模型清单照搬 aicodewith /zh/models（与前端 MDB 的 id 一一对齐）。
# 字段：(name, provider, quality, speed, cost_in, cost_out, latency, tps, context, capabilities)
#   cost_in / cost_out 单位为 ¥ / 1K token（= aicodewith 的 ¥/1M ÷ 1000）。
#   quality/speed/latency/tps 为相对参考值，非基准跑分。
# ⚠️ name 直接透传给 aicodewith 作为上游 `model` 字段——接入时务必与 aicodewith
#    实际接受的模型 id 字符串核对（控制台/文档），不一致就在这里改这一列即可。
MODELS = [
    # —— 推理模型 ——
    ("deepseek-r1-0528", "aicodewith", 0.92, 0.60, 0.004, 0.016, 1200, 50, 65536, '["chat","code","reasoning"]'),
    ("kimi-k2-thinking", "aicodewith", 0.91, 0.62, 0.004, 0.016, 1100, 55, 256000, '["chat","reasoning"]'),
    ("qwq-32b", "aicodewith", 0.85, 0.70, 0.002, 0.006, 900, 70, 32768, '["chat","reasoning"]'),
    ("qwen3-235b-thinking", "aicodewith", 0.93, 0.60, 0.002, 0.020, 1200, 50, 262000, '["chat","reasoning"]'),
    ("qwen3-30b-thinking", "aicodewith", 0.84, 0.72, 0.0007, 0.0028, 800, 75, 65536, '["chat","reasoning"]'),
    ("qwen3-next-80b-thinking", "aicodewith", 0.86, 0.68, 0.001, 0.010, 900, 65, 65536, '["chat","reasoning"]'),
    # —— 对话 / 通用 ——
    ("deepseek-v3.2", "aicodewith", 0.88, 0.85, 0.002, 0.003, 600, 100, 65536, '["chat","code","analysis"]'),
    ("deepseek-v4-flash", "aicodewith", 0.86, 0.95, 0.001, 0.002, 350, 130, 1000000, '["chat","code"]'),
    ("deepseek-v4-pro", "aicodewith", 0.95, 0.70, 0.012, 0.024, 900, 70, 1000000, '["chat","code","analysis"]'),
    ("glm-4.6", "aicodewith", 0.88, 0.82, 0.002, 0.008, 600, 90, 200000, '["chat","code"]'),
    ("glm-4.7", "aicodewith", 0.90, 0.82, 0.002, 0.008, 600, 90, 200000, '["chat","code"]'),
    ("glm-5", "aicodewith", 0.93, 0.75, 0.004, 0.018, 800, 70, 200000, '["chat","code","analysis"]'),
    ("glm-5.1", "aicodewith", 0.94, 0.70, 0.006, 0.024, 900, 65, 200000, '["chat","code","analysis","agent"]'),
    ("kimi-k2", "aicodewith", 0.89, 0.80, 0.004, 0.016, 600, 90, 131072, '["chat","code"]'),
    ("kimi-k2.5", "aicodewith", 0.90, 0.78, 0.004, 0.021, 650, 85, 131072, '["chat","code","agent"]'),
    ("mimo-v2-flash", "aicodewith", 0.80, 0.95, 0.0007, 0.0021, 350, 130, 65536, '["chat","code"]'),
    ("minimax-m2.1", "aicodewith", 0.86, 0.82, 0.0021, 0.0084, 600, 90, 65536, '["chat","code"]'),
    ("minimax-m2.5", "aicodewith", 0.88, 0.83, 0.0021, 0.0084, 580, 92, 65536, '["chat","code"]'),
    ("minimax-m2.7", "aicodewith", 0.90, 0.83, 0.0021, 0.0084, 580, 92, 65536, '["chat","code","agent"]'),
    ("qwen2.5-7b", "aicodewith", 0.72, 0.95, 0.0005, 0.001, 300, 140, 32768, '["chat"]'),
    ("qwen2.5-32b", "aicodewith", 0.80, 0.85, 0.002, 0.006, 500, 95, 32768, '["chat","code"]'),
    ("qwen2.5-72b", "aicodewith", 0.84, 0.78, 0.004, 0.012, 650, 85, 128000, '["chat","code","analysis"]'),
    ("qwen3-14b", "aicodewith", 0.82, 0.88, 0.001, 0.004, 450, 110, 65536, '["chat","code"]'),
    ("qwen3-30b-instruct", "aicodewith", 0.83, 0.85, 0.0007, 0.0028, 500, 100, 65536, '["chat","code"]'),
    ("qwen3-32b", "aicodewith", 0.85, 0.82, 0.002, 0.008, 550, 95, 65536, '["chat","code"]'),
    ("qwen3-235b", "aicodewith", 0.90, 0.72, 0.002, 0.008, 700, 70, 65536, '["chat","code","analysis"]'),
    ("qwen3-235b-instruct", "aicodewith", 0.90, 0.75, 0.002, 0.008, 680, 75, 65536, '["chat","code","analysis"]'),
    ("qwen3-next-80b-instruct", "aicodewith", 0.86, 0.85, 0.001, 0.004, 500, 100, 65536, '["chat","code"]'),
    ("qwen3.5-397b", "aicodewith", 0.91, 0.90, 0.0012, 0.0072, 450, 120, 65536, '["chat","code","analysis"]'),
    ("longcat-flash-chat", "aicodewith", 0.85, 0.88, 0.001, 0.005, 450, 110, 65536, '["chat","code"]'),
    # —— 专用模型 ——
    ("gpt-image-2", "aicodewith", 0.90, 0.70, 0.0, 0.0, 3000, 0, 0, '["image"]'),
    ("qwen3-coder", "aicodewith", 0.90, 0.78, 0.006, 0.024, 700, 80, 65536, '["code"]'),
    ("qwen3-coder-next", "aicodewith", 0.89, 0.82, 0.004, 0.016, 600, 90, 65536, '["code"]'),
    # Claude Code 透传计费用(Anthropic 格式 /v1/messages)。单价为占位混合价,接入后按实际改。
    ("claude-code", "aicodewith", 0.96, 0.70, 0.02, 0.08, 900, 60, 200000, '["chat","code","agent"]'),
]

# V1 routing: 3 hard defaults (chat / code_generation / summarization)，全部指向
# 真实的 aicodewith 模型 id。其余 task_type 走调用方显式传入的 model，不做隐式路由。
INDUSTRIES = ["default"]
TASK_TYPES = ["chat", "code_generation", "summarization"]

ROUTING_LOGIC = {
    "default": {
        "chat": ("deepseek-v3.2", "glm-4.7", "qwen3-30b-instruct"),
        "code_generation": ("deepseek-v4-pro", "qwen3-coder", "deepseek-v4-flash"),
        "summarization": ("deepseek-v4-flash", "kimi-k2-thinking", "qwen3-30b-instruct"),
    },
}


PUBLIC_KBS_SEED = [
    {"name": "全球金融监管法规库", "author": "金融研究院", "verified": True, "industry": "finance", "skills": ["rag", "compliance", "risk"], "desc": "涵盖中、美、欧、日、新加坡等主要市场的金融监管法规，每日同步更新", "docs": 128, "subscribers": 1240, "rating": 48, "price": 0, "price_mode": "free", "cover": 0},
    {"name": "中医药典电子版", "author": "同仁堂", "verified": True, "industry": "medical", "skills": ["rag", "translation"], "desc": "国家药典委员会授权，含中药材性味、归经、主治、用法用量及现代研究", "docs": 86, "subscribers": 458, "rating": 46, "price": 199, "price_mode": "monthly", "cover": 1},
    {"name": "中国法律法规全集", "author": "平台官方", "verified": True, "industry": "legal", "skills": ["rag", "compliance"], "desc": "最高法、最高检、各部委、地方法规一站式检索，2026 年最新版", "docs": 312, "subscribers": 3520, "rating": 49, "price": 0, "price_mode": "free", "cover": 4},
    {"name": "跨境电商运营手册", "author": "电商之家", "verified": False, "industry": "ecommerce", "skills": ["writing", "translation", "cs"], "desc": "亚马逊/Shopify/TikTok Shop 全平台运营策略，含选品、广告、合规要点", "docs": 64, "subscribers": 892, "rating": 44, "price": 99, "price_mode": "monthly", "cover": 2},
    {"name": "K12教学大纲与题库", "author": "教研中心", "verified": True, "industry": "education", "skills": ["summary", "writing"], "desc": "人教版/北师大/华师大全学科大纲，含历年真题及解析，适合智能辅导", "docs": 215, "subscribers": 2150, "rating": 47, "price": 0, "price_mode": "free", "cover": 5},
    {"name": "中国制造业ISO标准", "author": "中国质量认证中心", "verified": True, "industry": "manufacture", "skills": ["rag", "compliance"], "desc": "ISO 9001/14001/45001 标准全文及实施指引，含中国 GB 标准对照", "docs": 48, "subscribers": 215, "rating": 45, "price": 299, "price_mode": "monthly", "cover": 3},
    {"name": "政府采购流程指南", "author": "平台官方", "verified": True, "industry": "government", "skills": ["rag", "report"], "desc": "政府采购法及实施条例，招投标全流程模板与案例库", "docs": 35, "subscribers": 567, "rating": 46, "price": 0, "price_mode": "free", "cover": 0},
    {"name": "房产交易法规与合同", "author": "链家研究院", "verified": False, "industry": "realestate", "skills": ["rag", "compliance"], "desc": "各城市限购限贷政策、交易税费、合同模板及风险提示", "docs": 42, "subscribers": 312, "rating": 43, "price": 149, "price_mode": "monthly", "cover": 6},
    {"name": "汽车维修技术资料", "author": "汽修联盟", "verified": False, "industry": "automotive", "skills": ["rag", "cs"], "desc": "主流品牌轿车/SUV 维修手册、故障码大全、配件价格参考", "docs": 178, "subscribers": 745, "rating": 44, "price": 0, "price_mode": "free", "cover": 7},
    {"name": "旅游景点百科", "author": "携程旅行", "verified": True, "industry": "tourism", "skills": ["rag", "writing"], "desc": "国内 5A/4A 景区详细介绍、攻略、当地特色与交通指南", "docs": 512, "subscribers": 1820, "rating": 47, "price": 0, "price_mode": "free", "cover": 1},
    {"name": "餐饮食品安全规范", "author": "中国食品工业协会", "verified": True, "industry": "catering", "skills": ["compliance"], "desc": "GB 食品安全国家标准、HACCP 体系、餐饮许可申请流程", "docs": 28, "subscribers": 423, "rating": 45, "price": 0, "price_mode": "free", "cover": 2},
    {"name": "HR招聘话术与面试题库", "author": "人才云", "verified": False, "industry": "hr", "skills": ["writing", "cs"], "desc": "500+ 岗位 JD 模板、行为面试题、薪酬数据，含 AI 智能面试评分", "docs": 96, "subscribers": 1180, "rating": 46, "price": 79, "price_mode": "monthly", "cover": 5},
    {"name": "学术论文检索与摘要", "author": "知网研学", "verified": True, "industry": "research", "skills": ["summary", "translation", "ner"], "desc": "CNKI 1.2 亿篇文献摘要库，支持中英双语检索与一键综述生成", "docs": 1280, "subscribers": 876, "rating": 48, "price": 199, "price_mode": "monthly", "cover": 4},
    {"name": "软件开发最佳实践", "author": "极客社区", "verified": False, "industry": "software", "skills": ["code", "rag"], "desc": "设计模式、架构案例、安全编码规范、code review checklist", "docs": 142, "subscribers": 2410, "rating": 47, "price": 0, "price_mode": "free", "cover": 0},
    {"name": "物流跨境清关指南", "author": "菜鸟国际", "verified": True, "industry": "logistics", "skills": ["rag", "translation"], "desc": "各国海关申报要素、HS 编码查询、跨境结算与税务合规", "docs": 58, "subscribers": 234, "rating": 44, "price": 99, "price_mode": "monthly", "cover": 3},
]


def seed_knowledge_bases(db: Session, dev_api_key_id: int):
    """Seed public marketplace KBs + one private demo KB for the dev key."""
    if db.query(KnowledgeBase).count() > 0:
        return

    # 15 public KBs (no owner — platform-managed)
    for p in PUBLIC_KBS_SEED:
        kb = KnowledgeBase(
            api_key_id=None,
            name=p["name"],
            industry=p["industry"],
            skills=json.dumps(p["skills"]),
            embed="bge-m3",
            visibility="public",
            attached=False,
            publish_desc=p["desc"],
            publish_price_mode=p["price_mode"],
            publish_price=p["price"],
            author=p["author"],
            verified=p["verified"],
            subscribers_count=p["subscribers"],
            rating=p["rating"],
            cover_idx=p["cover"],
        )
        db.add(kb)

    # One demo private KB owned by dev key, with 3 ready docs
    demo_kb = KnowledgeBase(
        api_key_id=dev_api_key_id,
        name="金融合规手册",
        industry="finance",
        skills=json.dumps(["rag", "compliance"]),
        embed="bge-m3",
        visibility="private",
        attached=True,
    )
    db.add(demo_kb)
    db.flush()
    for name, t, sz, ch in [
        ("2024年金融监管新规.pdf", "pdf", 2456000, 42),
        ("反洗钱条例解读.docx", "docx", 680000, 18),
        ("巴塞尔协议III要点.pdf", "pdf", 1820000, 31),
    ]:
        db.add(Document(kb_id=demo_kb.id, name=name, type=t, size=sz, chunks=ch, status="ready"))

    db.commit()


def seed_database(db: Session):
    """Seed database with initial data. Idempotent — skips per-table if data exists."""
    # Knowledge bases are seeded independently of providers (after the dev api_key exists below).
    if db.query(Provider).count() > 0:
        # Even if providers exist, ensure KBs are seeded (added after initial schema)
        dev_key = db.query(ApiKey).first()
        if dev_key:
            seed_knowledge_bases(db, dev_key.id)
        return

    # Create providers
    provider_map = {}
    for p in PROVIDERS:
        provider = Provider(**p)
        db.add(provider)
        db.flush()
        provider_map[p["name"]] = provider.id

    # 全部模型走真实上游 aicodewith（is_mock=False）。若 AICODEWITH_API_KEY 未配置，
    # provider 会在调用时 fail-fast 报 missing_api_key，而不是静默返回假数据。
    real_provider_names = {"aicodewith", "openai", "deepseek"}
    model_map = {}
    for name, prov_name, quality, speed, cost_in, cost_out, latency, tps, ctx, caps in MODELS:
        model = Model(
            name=name,
            provider_id=provider_map[prov_name],
            quality_score=quality,
            speed_score=speed,
            cost_per_1k_input=cost_in,
            cost_per_1k_output=cost_out,
            avg_latency_ms=latency,
            tokens_per_second=tps,
            max_context_length=ctx,
            capabilities=caps,
            is_mock=prov_name not in real_provider_names,
        )
        db.add(model)
        db.flush()
        model_map[name] = model.id

    # V1: 3 routing rules (default industry × 3 hard-default tasks).
    for industry in INDUSTRIES:
        for task_type in TASK_TYPES:
            models_tuple = ROUTING_LOGIC[industry][task_type]
            primary_name, fallback_name, specialist_name = models_tuple

            primary_model = db.query(Model).filter(Model.id == model_map[primary_name]).first()
            quality = primary_model.quality_score if primary_model else 0.8
            speed = primary_model.speed_score if primary_model else 0.7
            cost = primary_model.cost_per_1k_input * 100 if primary_model else 0.5

            rule = RoutingRule(
                industry=industry,
                task_type=task_type,
                primary_model_id=model_map[primary_name],
                fallback_model_id=model_map[fallback_name],
                specialist_model_id=model_map[specialist_name],
                quality_score=round(quality, 2),
                speed_score=round(speed, 2),
                cost_score=round(min(cost, 1.0), 2),
                description=f"{industry}/{task_type}: {primary_name} → {fallback_name} → {specialist_name}",
                reason=f"Optimized for {industry} {task_type} workloads",
                estimated_cost=f"${primary_model.cost_per_1k_input * 2:.4f}/req" if primary_model else "$0.001/req",
            )
            db.add(rule)

    # Create default API key
    api_key = ApiKey(
        key="sk-geniuscode-dev-000000000000000000000000",
        name="Development Key",
        owner_email="dev@geniuscode.online",
        is_active=True,
        rate_limit_rpm=60,
        rate_limit_tpm=100000,
    )
    db.add(api_key)
    db.flush()

    # Create default budget
    budget = Budget(
        api_key_id=api_key.id,
        monthly_limit_usd=100.0,
        daily_limit_usd=10.0,
        per_request_limit_usd=1.0,
        last_daily_reset=date.today(),
        last_monthly_reset=date.today(),
    )
    db.add(budget)

    db.commit()

    # Seed knowledge bases
    seed_knowledge_bases(db, api_key.id)
