from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import User
from app.models.skill_resource_models import SkillResource
from app.security import require_admin
from app.services.pagination import paginate, page_response
from app.services.skill_resources import normalize_skill_key

router = APIRouter(prefix="/admin/skill-resources", tags=["Admin - Skill Resources"])


def _serialize(resource: SkillResource) -> dict:
    return {
        "id": resource.id,
        "skillKey": resource.skill_key,
        "skillLabel": resource.skill_label,
        "youtubeUrl": resource.youtube_url,
        "courseUrl": resource.course_url,
        "docsUrl": resource.docs_url,
        "createdAt": resource.created_at,
        "updatedAt": resource.updated_at,
    }


@router.get("")
def list_skill_resources(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    query = db.query(SkillResource)
    if search:
        like = f"%{search}%"
        query = query.filter(SkillResource.skill_label.ilike(like))

    query = query.order_by(SkillResource.skill_label)
    items, total = paginate(query, page, pageSize)
    return page_response([_serialize(r) for r in items], total, page, pageSize)


class SkillResourceInput(BaseModel):
    skillLabel: str
    youtubeUrl: str | None = None
    courseUrl: str | None = None
    docsUrl: str | None = None


@router.post("")
def create_skill_resource(data: SkillResourceInput, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    skill_key = normalize_skill_key(data.skillLabel)
    if not skill_key:
        raise HTTPException(status_code=400, detail="Skill name cannot be empty.")

    existing = db.query(SkillResource).filter(SkillResource.skill_key == skill_key).first()
    if existing:
        raise HTTPException(status_code=400, detail="A resource for this skill already exists — edit it instead.")

    resource = SkillResource(
        skill_key=skill_key,
        skill_label=data.skillLabel,
        youtube_url=data.youtubeUrl or None,
        course_url=data.courseUrl or None,
        docs_url=data.docsUrl or None,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return _serialize(resource)


@router.patch("/{resource_id}")
def update_skill_resource(
    resource_id: int, data: SkillResourceInput, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
):
    resource = db.query(SkillResource).filter(SkillResource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Skill resource not found")

    new_key = normalize_skill_key(data.skillLabel)
    if not new_key:
        raise HTTPException(status_code=400, detail="Skill name cannot be empty.")
    if new_key != resource.skill_key:
        collision = db.query(SkillResource).filter(SkillResource.skill_key == new_key, SkillResource.id != resource_id).first()
        if collision:
            raise HTTPException(status_code=400, detail="A resource for this skill already exists.")

    resource.skill_key = new_key
    resource.skill_label = data.skillLabel
    resource.youtube_url = data.youtubeUrl or None
    resource.course_url = data.courseUrl or None
    resource.docs_url = data.docsUrl or None

    db.commit()
    db.refresh(resource)
    return _serialize(resource)


@router.delete("/{resource_id}")
def delete_skill_resource(resource_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    resource = db.query(SkillResource).filter(SkillResource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Skill resource not found")

    db.delete(resource)
    db.commit()
    return {"message": "Skill resource deleted."}
