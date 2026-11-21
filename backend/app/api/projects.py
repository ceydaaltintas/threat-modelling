"""Project endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models import AnalysisRun, Project, Threat
from app.schemas.api import ProjectCreate, ProjectOut

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[dict])
async def list_projects(session: AsyncSession = Depends(get_session)) -> list[dict]:
    """Projects with a short risk summary for the project list screen."""
    projects = (
        await session.execute(select(Project).order_by(Project.created_at.desc()))
    ).scalars().all()

    out: list[dict] = []
    for project in projects:
        last_run = (
            await session.execute(
                select(AnalysisRun)
                .where(AnalysisRun.project_id == project.id)
                .order_by(AnalysisRun.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        critical = high = 0
        if last_run is not None:
            # One shared expression object, so the SELECT and the GROUP BY
            # render identically (Postgres compares them literally).
            level = Threat.system_calc["level"].as_string().label("level")
            rows = (
                await session.execute(
                    select(level, func.count())
                    .where(Threat.run_id == last_run.id)
                    .group_by(level)
                )
            ).all()
            counts = {level: count for level, count in rows if level}
            critical = counts.get("Kritik", 0)
            high = counts.get("Yüksek", 0)

        out.append(
            {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "sample_key": project.sample_key,
                "created_at": project.created_at,
                "last_run": (
                    {
                        "id": last_run.id,
                        "status": last_run.status,
                        "started_at": last_run.started_at,
                        "finished_at": last_run.finished_at,
                    }
                    if last_run
                    else None
                ),
                "risk_summary": {"critical": critical, "high": high},
            }
        )
    return out


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate, session: AsyncSession = Depends(get_session)
) -> Project:
    project = Project(
        name=payload.name,
        description=payload.description,
        sample_key=payload.sample_key,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: str, session: AsyncSession = Depends(get_session)
) -> Project:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Proje bulunamadı.")
    return project
