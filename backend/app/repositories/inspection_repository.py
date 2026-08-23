from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import InspectionStatus
from app.models.inspection import Inspection


class InspectionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, inspection_id: UUID) -> Inspection | None:
        statement = (
            select(Inspection)
            .where(Inspection.id == inspection_id)
            .options(
                selectinload(Inspection.anomalies),
                selectinload(Inspection.images),
                selectinload(Inspection.report),
            )
        )
        return self.session.scalar(statement)

    def add(self, inspection: Inspection) -> Inspection:
        self.session.add(inspection)
        self.session.flush()
        return inspection

    def list(
        self,
        *,
        page: int,
        page_size: int,
        site_id: UUID | None = None,
        status: InspectionStatus | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort: str = "inspected_at_desc",
    ) -> tuple[list[Inspection], int]:
        statement: Select[tuple[Inspection]] = select(Inspection).options(
            selectinload(Inspection.anomalies)
        )
        if site_id:
            statement = statement.where(Inspection.site_id == site_id)
        if status:
            statement = statement.where(Inspection.status == status)
        if date_from:
            statement = statement.where(Inspection.inspected_at >= date_from)
        if date_to:
            statement = statement.where(Inspection.inspected_at <= date_to)
        total = (
            self.session.scalar(
                select(func.count()).select_from(statement.order_by(None).subquery())
            )
            or 0
        )
        order = (
            Inspection.inspected_at.asc()
            if sort == "inspected_at_asc"
            else Inspection.inspected_at.desc()
        )
        statement = (
            statement.order_by(order, Inspection.id).offset((page - 1) * page_size).limit(page_size)
        )
        return list(self.session.scalars(statement)), total

    def list_for_site(
        self, site_id: UUID, *, page: int, page_size: int
    ) -> tuple[list[Inspection], int]:
        return self.list(page=page, page_size=page_size, site_id=site_id)
