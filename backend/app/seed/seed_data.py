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


PROVIDERS = [
    {"name": "openai", "base_url": "https://api.openai.com/v1", "api_key_env_var": "OPENAI_API_KEY"},
    {"name": "anthropic", "base_url": "https://api.anthropic.com/v1", "api_key_env_var": "ANTHROPIC_API_KEY"},
    {"name": "deepseek", "base_url": "https://api.deepseek.com/v1", "api_key_env_var": "DEEPSEEK_API_KEY"},
    {"name": "alibaba", "base_url": "https://dashscope.aliyuncs.com/api/v1", "api_key_env_var": "ALIBABA_API_KEY"},
    {"name": "baidu", "base_url": "https://aip.baidubce.com/rpc/2.0", "api_key_env_var": "BAIDU_API_KEY"},
    {"name": "zhipu", "base_url": "https://open.bigmodel.cn/api/paas/v4", "api_key_env_var": "ZHIPU_API_KEY"},
    {"name": "moonshot", "base_url": "https://api.moonshot.cn/v1", "api_key_env_var": "MOONSHOT_API_KEY"},
]

# Models: (name, provider_name, quality, speed, cost_in, cost_out, latency, tps, context, capabilities)
# `gpt-3.5-turbo` is included so the Quickstart curl example (which still
# references the cheapest OpenAI model) has a real route. Task 3 wires the
# OpenAI provider; the rest stay mocked until Task 5+.
MODELS = [
    ("gpt-4o", "openai", 0.95, 0.80, 0.005, 0.015, 800, 80, 128000, '["chat","code","analysis","vision"]'),
    ("gpt-4o-mini", "openai", 0.82, 0.92, 0.00015, 0.0006, 400, 120, 128000, '["chat","code","analysis"]'),
    ("gpt-3.5-turbo", "openai", 0.70, 0.93, 0.0005, 0.0015, 350, 130, 16385, '["chat","code"]'),
    ("claude-3.5-sonnet", "anthropic", 0.96, 0.75, 0.003, 0.015, 900, 70, 200000, '["chat","code","analysis","vision"]'),
    ("claude-3-haiku", "anthropic", 0.78, 0.95, 0.00025, 0.00125, 300, 150, 200000, '["chat","code"]'),
    ("deepseek-v3", "deepseek", 0.88, 0.85, 0.0002, 0.0006, 600, 100, 64000, '["chat","code","analysis"]'),
    ("deepseek-r1", "deepseek", 0.92, 0.60, 0.0004, 0.0016, 1200, 50, 64000, '["chat","code","reasoning"]'),
    ("qwen-max", "alibaba", 0.85, 0.82, 0.0004, 0.0012, 700, 90, 32000, '["chat","code","analysis"]'),
    ("ernie-4.0", "baidu", 0.83, 0.78, 0.0008, 0.002, 650, 85, 8000, '["chat","analysis"]'),
    ("glm-4", "zhipu", 0.80, 0.88, 0.0003, 0.001, 500, 95, 128000, '["chat","code"]'),
    ("moonshot-v1", "moonshot", 0.79, 0.90, 0.00025, 0.001, 450, 110, 128000, '["chat","code","analysis"]'),
]

INDUSTRIES = ["finance", "healthcare", "legal", "education", "ecommerce", "technology", "manufacturing", "media"]
TASK_TYPES = ["chat", "code_generation", "data_analysis", "content_writing", "translation", "summarization", "reasoning", "customer_service"]

# Mapping: (industry, task) -> (primary, fallback, specialist) model names
# Simplified: use quality-first for complex tasks, cost-first for simple ones
ROUTING_LOGIC = {
    "finance": {
        "chat": ("gpt-4o-mini", "claude-3-haiku", "qwen-max"),
        "code_generation": ("gpt-4o", "claude-3.5-sonnet", "deepseek-v3"),
        "data_analysis": ("gpt-4o", "deepseek-r1", "qwen-max"),
        "content_writing": ("claude-3.5-sonnet", "gpt-4o", "ernie-4.0"),
        "translation": ("gpt-4o-mini", "qwen-max", "glm-4"),
        "summarization": ("claude-3-haiku", "gpt-4o-mini", "deepseek-v3"),
        "reasoning": ("deepseek-r1", "gpt-4o", "claude-3.5-sonnet"),
        "customer_service": ("gpt-4o-mini", "claude-3-haiku", "moonshot-v1"),
    },
    "healthcare": {
        "chat": ("claude-3.5-sonnet", "gpt-4o", "ernie-4.0"),
        "code_generation": ("gpt-4o", "deepseek-v3", "claude-3.5-sonnet"),
        "data_analysis": ("gpt-4o", "deepseek-r1", "claude-3.5-sonnet"),
        "content_writing": ("claude-3.5-sonnet", "gpt-4o", "qwen-max"),
        "translation": ("gpt-4o-mini", "qwen-max", "glm-4"),
        "summarization": ("claude-3-haiku", "gpt-4o-mini", "deepseek-v3"),
        "reasoning": ("deepseek-r1", "claude-3.5-sonnet", "gpt-4o"),
        "customer_service": ("claude-3-haiku", "gpt-4o-mini", "moonshot-v1"),
    },
    "legal": {
        "chat": ("claude-3.5-sonnet", "gpt-4o", "deepseek-r1"),
        "code_generation": ("gpt-4o", "deepseek-v3", "claude-3.5-sonnet"),
        "data_analysis": ("deepseek-r1", "gpt-4o", "claude-3.5-sonnet"),
        "content_writing": ("claude-3.5-sonnet", "gpt-4o", "ernie-4.0"),
        "translation": ("gpt-4o", "qwen-max", "glm-4"),
        "summarization": ("claude-3.5-sonnet", "gpt-4o-mini", "deepseek-v3"),
        "reasoning": ("deepseek-r1", "claude-3.5-sonnet", "gpt-4o"),
        "customer_service": ("gpt-4o-mini", "claude-3-haiku", "qwen-max"),
    },
    "education": {
        "chat": ("gpt-4o-mini", "claude-3-haiku", "moonshot-v1"),
        "code_generation": ("deepseek-v3", "gpt-4o", "claude-3.5-sonnet"),
        "data_analysis": ("gpt-4o-mini", "deepseek-v3", "qwen-max"),
        "content_writing": ("claude-3.5-sonnet", "gpt-4o", "qwen-max"),
        "translation": ("qwen-max", "gpt-4o-mini", "glm-4"),
        "summarization": ("claude-3-haiku", "gpt-4o-mini", "deepseek-v3"),
        "reasoning": ("deepseek-r1", "gpt-4o", "claude-3.5-sonnet"),
        "customer_service": ("moonshot-v1", "gpt-4o-mini", "claude-3-haiku"),
    },
    "ecommerce": {
        "chat": ("gpt-4o-mini", "claude-3-haiku", "moonshot-v1"),
        "code_generation": ("gpt-4o", "deepseek-v3", "claude-3.5-sonnet"),
        "data_analysis": ("deepseek-v3", "gpt-4o-mini", "qwen-max"),
        "content_writing": ("gpt-4o", "claude-3.5-sonnet", "qwen-max"),
        "translation": ("qwen-max", "gpt-4o-mini", "glm-4"),
        "summarization": ("gpt-4o-mini", "claude-3-haiku", "deepseek-v3"),
        "reasoning": ("gpt-4o", "deepseek-r1", "claude-3.5-sonnet"),
        "customer_service": ("gpt-4o-mini", "moonshot-v1", "claude-3-haiku"),
    },
    "technology": {
        "chat": ("gpt-4o-mini", "claude-3-haiku", "deepseek-v3"),
        "code_generation": ("claude-3.5-sonnet", "gpt-4o", "deepseek-v3"),
        "data_analysis": ("gpt-4o", "deepseek-r1", "deepseek-v3"),
        "content_writing": ("claude-3.5-sonnet", "gpt-4o", "qwen-max"),
        "translation": ("gpt-4o-mini", "qwen-max", "glm-4"),
        "summarization": ("claude-3-haiku", "deepseek-v3", "gpt-4o-mini"),
        "reasoning": ("deepseek-r1", "claude-3.5-sonnet", "gpt-4o"),
        "customer_service": ("gpt-4o-mini", "claude-3-haiku", "moonshot-v1"),
    },
    "manufacturing": {
        "chat": ("gpt-4o-mini", "qwen-max", "ernie-4.0"),
        "code_generation": ("deepseek-v3", "gpt-4o", "claude-3.5-sonnet"),
        "data_analysis": ("deepseek-v3", "gpt-4o", "qwen-max"),
        "content_writing": ("qwen-max", "gpt-4o", "ernie-4.0"),
        "translation": ("qwen-max", "glm-4", "gpt-4o-mini"),
        "summarization": ("deepseek-v3", "gpt-4o-mini", "claude-3-haiku"),
        "reasoning": ("deepseek-r1", "gpt-4o", "qwen-max"),
        "customer_service": ("qwen-max", "gpt-4o-mini", "moonshot-v1"),
    },
    "media": {
        "chat": ("gpt-4o-mini", "moonshot-v1", "claude-3-haiku"),
        "code_generation": ("gpt-4o", "deepseek-v3", "claude-3.5-sonnet"),
        "data_analysis": ("gpt-4o-mini", "deepseek-v3", "qwen-max"),
        "content_writing": ("claude-3.5-sonnet", "gpt-4o", "moonshot-v1"),
        "translation": ("gpt-4o-mini", "qwen-max", "glm-4"),
        "summarization": ("claude-3-haiku", "gpt-4o-mini", "deepseek-v3"),
        "reasoning": ("gpt-4o", "deepseek-r1", "claude-3.5-sonnet"),
        "customer_service": ("moonshot-v1", "gpt-4o-mini", "claude-3-haiku"),
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

    # Create models. OpenAI models go through the real provider; everything
    # else stays mocked until Task 5+ wires the remaining providers.
    real_provider_names = {"openai"}
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

    # Create routing rules (64 = 8 industries × 8 tasks)
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
        key="sk-modelmux-dev-000000000000000000000000",
        name="Development Key",
        owner_email="dev@modelmux.ai",
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
