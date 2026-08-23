from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.enums import InspectionStatus, RiskLevel, SiteStatus, SiteType
from app.models.site import Site
from app.repositories.anomaly_repository import AnomalyRepository
from app.repositories.site_repository import SiteRepository
from app.schemas.pagination import Page, page_response
from app.schemas.site import SiteCreate, SiteDetail, SiteRead, SiteUpdate


class SiteService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.sites = SiteRepository(session)
        self.anomalies = AnomalyRepository(session)

    def get(self, site_id: UUID) -> Site:
        site = self.sites.get(site_id)
        if site is None:
            raise NotFoundError("Site was not found.", code="site_not_found")
        return site

    def get_detail(self, site_id: UUID) -> SiteDetail:
        site = self.get(site_id)
        data = SiteRead.model_validate(site).model_dump()
        return SiteDetail(
            **data,
            inspection_count=self.sites.inspection_count(site_id),
            unresolved_anomaly_count=self.anomalies.unresolved_count(site_id),
        )

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
    ) -> Page[SiteRead]:
        items, total = self.sites.list(
            page=page,
            page_size=page_size,
            query=query,
            site_type=site_type,
            status=status,
            risk_levels=risk_levels,
            inspection_status=inspection_status,
            sort=sort,
        )
        return page_response(
            [SiteRead.model_validate(item) for item in items],
            page=page,
            page_size=page_size,
            total=total,
        )

    def create(self, data: SiteCreate) -> Site:
        if self.sites.get_by_name(data.name):
            raise ConflictError("A site with this name already exists.", code="site_name_conflict")
        site = Site(**data.model_dump(), current_risk_score=0, current_risk_level=RiskLevel.LOW)
        try:
            self.sites.add(site)
            self.session.commit()
        except IntegrityError as exception:
            self.session.rollback()
            raise ConflictError(
                "A site with this name already exists.", code="site_name_conflict"
            ) from exception
        return site

    def update(self, site_id: UUID, data: SiteUpdate) -> Site:
        site = self.get(site_id)
        changes = data.model_dump(exclude_unset=True, exclude_none=True)
        requested_name = changes.get("name")
        if requested_name and requested_name.strip().lower() != site.name.lower():
            conflict = self.sites.get_by_name(requested_name)
            if conflict:
                raise ConflictError(
                    "A site with this name already exists.", code="site_name_conflict"
                )
        for field, value in changes.items():
            setattr(site, field, value)
        try:
            self.session.commit()
        except IntegrityError as exception:
            self.session.rollback()
            raise ConflictError(
                "The site update conflicts with existing data.", code="site_update_conflict"
            ) from exception
        return site
