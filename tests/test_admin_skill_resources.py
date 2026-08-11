import pytest

from app.models.models import User
from app.models.skill_resource_models import SkillResource
from app.routes import admin_skill_resources as routes


def _admin(db_session):
    user = User(email="admin@example.com", hashed_password="x", role="admin")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_create_skill_resource_normalizes_key(db_session):
    admin = _admin(db_session)
    result = routes.create_skill_resource(
        routes.SkillResourceInput(skillLabel="Node.js", youtubeUrl="https://youtube.com/x"), db_session, admin
    )
    assert result["skillKey"] == "nodejs"
    assert result["skillLabel"] == "Node.js"
    assert result["youtubeUrl"] == "https://youtube.com/x"
    assert result["courseUrl"] is None


def test_create_skill_resource_rejects_duplicate_key(db_session):
    admin = _admin(db_session)
    routes.create_skill_resource(routes.SkillResourceInput(skillLabel="Docker"), db_session, admin)

    with pytest.raises(Exception) as exc_info:
        routes.create_skill_resource(routes.SkillResourceInput(skillLabel="  docker  "), db_session, admin)
    assert exc_info.value.status_code == 400


def test_update_skill_resource_changes_fields(db_session):
    admin = _admin(db_session)
    created = routes.create_skill_resource(routes.SkillResourceInput(skillLabel="Docker"), db_session, admin)

    updated = routes.update_skill_resource(
        created["id"],
        routes.SkillResourceInput(skillLabel="Docker", youtubeUrl="https://youtube.com/docker", docsUrl="https://docs.docker.com"),
        db_session,
        admin,
    )
    assert updated["youtubeUrl"] == "https://youtube.com/docker"
    assert updated["docsUrl"] == "https://docs.docker.com"


def test_update_skill_resource_rejects_key_collision(db_session):
    admin = _admin(db_session)
    routes.create_skill_resource(routes.SkillResourceInput(skillLabel="Docker"), db_session, admin)
    kubernetes = routes.create_skill_resource(routes.SkillResourceInput(skillLabel="Kubernetes"), db_session, admin)

    with pytest.raises(Exception) as exc_info:
        routes.update_skill_resource(kubernetes["id"], routes.SkillResourceInput(skillLabel="Docker"), db_session, admin)
    assert exc_info.value.status_code == 400


def test_delete_skill_resource(db_session):
    admin = _admin(db_session)
    created = routes.create_skill_resource(routes.SkillResourceInput(skillLabel="Docker"), db_session, admin)

    routes.delete_skill_resource(created["id"], db_session, admin)
    assert db_session.query(SkillResource).count() == 0


def test_list_skill_resources_paginates_and_searches(db_session):
    admin = _admin(db_session)
    routes.create_skill_resource(routes.SkillResourceInput(skillLabel="Docker"), db_session, admin)
    routes.create_skill_resource(routes.SkillResourceInput(skillLabel="Kubernetes"), db_session, admin)

    result = routes.list_skill_resources(page=1, pageSize=20, search="dock", db=db_session, current_user=admin)
    assert result["total"] == 1
    assert result["items"][0]["skillLabel"] == "Docker"
