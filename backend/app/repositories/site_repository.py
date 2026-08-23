from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.models.enums import InspectionStatus, RiskLevel, SiteStatus, SiteType
from app.models.inspection import Inspection
from app.models.site import Site


class SiteRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, site_id: UUID) -> Site | None:
        return self.session.get(Site, site_id)

    def get_by_name(self, name: str) -> Site | None:
        statement = select(Site).where(func.lower(Site.name) == name.strip().lower())
        return self.session.scalar(statement)

    def add(self, site: Site) -> Site:
        self.session.add(site)
        self.session.flush()
        return site

    def list(
        self,
        *,
        page: int,
        page_size: int,
        query: str | None = None,
        site_type: SiteType | None = None,
        status: SiteStatus | None = None,
        risk_levels: list[RiskLevel] | None = None,
        inspection_status: InspectionStatus | None = None,
        sort: str = "name",
    ) -> tuple[list[Site], int]:
        statement: Select[tuple[Site]] = select(Site)
        if query:
            normalized = f"%{query.strip().lower()}%"
            statement = statement.where(
                or_(
                    func.lower(Site.name).like(normalized),
                    func.lower(Site.location).like(normalized),
                )
            )
        if site_type:
            statement = statement.where(Site.site_type == site_type)
        if status:
            statement = statement.where(Site.status == status)
        if risk_levels:
            statement = statement.where(Site.current_risk_level.in_(risk_levels))
        if inspection_status:
            statement = statement.where(
                Site.inspections.any(Inspection.status == inspection_status)
            )

        total = (
            self.session.scalar(
                select(func.count()).select_from(statement.order_by(None).subquery())
            )
            or 0
        )
        if sort == "risk_desc":
            statement = statement.order_by(Site.current_risk_score.desc(), Site.name)
        elif sort == "created_at_desc":
            statement = statement.order_by(Site.created_at.desc(), Site.name)
        else:
            statement = statement.order_by(Site.name)
        statement = statement.offset((page - 1) * page_size).limit(page_size)
        return list(self.session.scalars(statement)), total

    def inspection_count(self, site_id: UUID) -> int:
        return (
            self.session.scalar(
                select(func.count()).select_from(Inspection).where(Inspection.site_id == site_id)
            )
            or 0
        )
