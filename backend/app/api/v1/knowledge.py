from __future__ import annotations

import json
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_api_key
from app.models.api_key import ApiKey
from app.models.knowledge_base import KnowledgeBase, Document, KBSubscription
from app.schemas.knowledge import KBCreate, KBUpdate

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTS = {"pdf", "docx", "txt", "md", "csv"}
MAX_FILE_SIZE = 20 * 1024 * 1024


def _kb_to_dict(kb: KnowledgeBase) -> dict:
    return {
        "id": kb.id,
        "name": kb.name,
        "industry": kb.industry,
        "skills": json.loads(kb.skills or "[]"),
        "embed": kb.embed,
        "visibility": kb.visibility,
        "attached": kb.attached,
        "publish_desc": kb.publish_desc,
        "publish_price_mode": kb.publish_price_mode,
        "publish_price": kb.publish_price,
        "docs": [
            {
                "id": d.id, "name": d.name, "type": d.type, "size": d.size,
                "chunks": d.chunks, "status": d.status,
                "uploaded_at": d.uploaded_at.isoformat(),
            }
            for d in kb.documents
        ],
        "created_at": kb.created_at.isoformat(),
    }


@router.get("/bases")
def list_my_bases(
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    kbs = db.query(KnowledgeBase).filter(KnowledgeBase.api_key_id == api_key.id).all()
    return [_kb_to_dict(kb) for kb in kbs]


@router.post("/bases")
def create_base(
    body: KBCreate,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    kb = KnowledgeBase(
        api_key_id=api_key.id,
        name=body.name,
        industry=body.industry,
        skills=json.dumps(body.skills),
        embed=body.embed,
        visibility="private",
        attached=False,
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return _kb_to_dict(kb)


@router.patch("/bases/{kb_id}")
def update_base(
    kb_id: int,
    body: KBUpdate,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.api_key_id == api_key.id,
    ).first()
    if not kb:
        raise HTTPException(404, "Knowledge base not found")

    if body.name is not None: kb.name = body.name
    if body.industry is not None: kb.industry = body.industry
    if body.skills is not None: kb.skills = json.dumps(body.skills)
    if body.visibility is not None:
        if body.visibility not in ("private", "team", "public"):
            raise HTTPException(400, "Invalid visibility")
        kb.visibility = body.visibility
    if body.attached is not None: kb.attached = body.attached
    if body.publish_desc is not None: kb.publish_desc = body.publish_desc
    if body.publish_price_mode is not None:
        if body.publish_price_mode not in ("free", "monthly", "onetime"):
            raise HTTPException(400, "Invalid price mode")
        kb.publish_price_mode = body.publish_price_mode
    if body.publish_price is not None:
        if body.publish_price < 0:
            raise HTTPException(400, "Price must be non-negative")
        kb.publish_price = body.publish_price

    db.commit()
    db.refresh(kb)
    return _kb_to_dict(kb)


@router.delete("/bases/{kb_id}")
def delete_base(
    kb_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.api_key_id == api_key.id,
    ).first()
    if not kb:
        raise HTTPException(404, "Knowledge base not found")
    # Remove file directory if exists
    kb_dir = os.path.join(UPLOAD_DIR, f"kb-{kb.id}")
    if os.path.isdir(kb_dir):
        for f in os.listdir(kb_dir):
            try:
                os.remove(os.path.join(kb_dir, f))
            except OSError:
                pass
        try:
            os.rmdir(kb_dir)
        except OSError:
            pass
    # Clean up subscriptions to this KB to avoid orphans
    db.query(KBSubscription).filter(KBSubscription.kb_id == kb.id).delete()
    db.delete(kb)
    db.commit()
    return {"deleted": kb_id}


@router.post("/bases/{kb_id}/documents")
async def upload_document(
    kb_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.api_key_id == api_key.id,
    ).first()
    if not kb:
        raise HTTPException(404, "Knowledge base not found")

    filename = file.filename or "untitled"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
    if ext not in ALLOWED_EXTS:
        raise HTTPException(400, f"Unsupported file type: {ext}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "File exceeds 20MB limit")

    kb_dir = os.path.join(UPLOAD_DIR, f"kb-{kb.id}")
    os.makedirs(kb_dir, exist_ok=True)
    file_path = os.path.join(kb_dir, f"{uuid.uuid4().hex[:12]}.{ext}")
    with open(file_path, "wb") as f:
        f.write(content)

    # Mock chunking: ~12KB per chunk, min 3
    chunks = max(3, len(content) // 12000)

    doc = Document(
        kb_id=kb.id,
        name=filename,
        type=ext,
        size=len(content),
        chunks=chunks,
        status="ready",
        file_path=file_path,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {
        "id": doc.id, "name": doc.name, "type": doc.type, "size": doc.size,
        "chunks": doc.chunks, "status": doc.status,
        "uploaded_at": doc.uploaded_at.isoformat(),
    }


@router.delete("/documents/{doc_id}")
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    doc = (
        db.query(Document)
        .join(KnowledgeBase, Document.kb_id == KnowledgeBase.id)
        .filter(Document.id == doc_id, KnowledgeBase.api_key_id == api_key.id)
        .first()
    )
    if not doc:
        raise HTTPException(404, "Document not found")

    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except OSError:
            pass
    db.delete(doc)
    db.commit()
    return {"deleted": doc_id}


@router.get("/marketplace")
def list_marketplace(
    industry: str = Query("all"),
    skill: str = Query("all"),
    sort: str = Query("hot"),
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    q = db.query(KnowledgeBase).filter(KnowledgeBase.visibility == "public")
    if industry != "all":
        q = q.filter(KnowledgeBase.industry == industry)
    kbs = q.all()
    if skill != "all":
        kbs = [kb for kb in kbs if skill in json.loads(kb.skills or "[]")]

    my_subs = {
        s.kb_id for s in db.query(KBSubscription)
        .filter(KBSubscription.api_key_id == api_key.id).all()
    }

    cards = []
    for kb in kbs:
        is_mine = kb.api_key_id == api_key.id
        price = 0 if kb.publish_price_mode == "free" else kb.publish_price
        cards.append({
            "id": kb.id,
            "name": kb.name,
            "author": kb.author or ("我" if is_mine else "未知"),
            "verified": kb.verified,
            "industry": kb.industry,
            "skills": json.loads(kb.skills or "[]"),
            "desc": kb.publish_desc or "暂无简介",
            "docs": len(kb.documents),
            "subscribers": kb.subscribers_count,
            "rating": kb.rating / 10.0 if kb.rating else 0,
            "price": price,
            "cover": kb.cover_idx,
            "is_mine": is_mine,
            "subscribed": kb.id in my_subs,
        })

    if sort == "free":
        cards = [c for c in cards if c["price"] == 0]
    if sort == "hot":
        cards.sort(key=lambda x: x["subscribers"], reverse=True)
    elif sort == "rating":
        cards.sort(key=lambda x: x["rating"], reverse=True)
    elif sort == "new":
        cards.sort(key=lambda x: x["id"], reverse=True)

    return cards


@router.post("/subscribe/{kb_id}")
def subscribe(
    kb_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb or kb.visibility != "public":
        raise HTTPException(404, "Public knowledge base not found")
    existing = db.query(KBSubscription).filter(
        KBSubscription.api_key_id == api_key.id,
        KBSubscription.kb_id == kb_id,
    ).first()
    if existing:
        return {"subscribed": True, "already": True}
    db.add(KBSubscription(api_key_id=api_key.id, kb_id=kb_id))
    kb.subscribers_count += 1
    db.commit()
    return {"subscribed": True}


@router.delete("/subscribe/{kb_id}")
def unsubscribe(
    kb_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    sub = db.query(KBSubscription).filter(
        KBSubscription.api_key_id == api_key.id,
        KBSubscription.kb_id == kb_id,
    ).first()
    if not sub:
        raise HTTPException(404, "Not subscribed")
    db.delete(sub)
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if kb and kb.subscribers_count > 0:
        kb.subscribers_count -= 1
    db.commit()
    return {"unsubscribed": True}
