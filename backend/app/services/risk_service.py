from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.enums import AnomalySeverity, RiskLevel
from app.models.risk_assessment import RiskAssessment
from app.repositories.risk_repository import RiskRepository
from app.repositories.site_repository import SiteRepository

FORMULA_VERSION = "deterministic-v1"
SEVERITY_WEIGHTS: dict[AnomalySeverity, int] = {
    AnomalySeverity.LOW: 2,
    AnomalySeverity.MODERATE: 6,
    AnomalySeverity.HIGH: 12,
    AnomalySeverity.CRITICAL: 20,
}
SEVERITY_CAP = 60
CRITICAL_BONUS = 15
VOLUME_POINTS_PER_ANOMALY = 3
VOLUME_CAP = 15
CLASSIFICATION_THRESHOLDS = {
    "LOW": [0, 30],
    "MODERATE": [31, 60],
    "HIGH": [61, 80],
    "CRITICAL": [81, 100],
}


@dataclass(frozen=True)
class RiskCalculation:
    score: int
    level: RiskLevel
    factors: dict[str, Any]


def classify_risk(score: int) -> RiskLevel:
    if score >= 81:
        return RiskLevel.CRITICAL
    if score >= 61:
        return RiskLevel.HIGH
    if score >= 31:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


def recency_points(days: int | None) -> int:
    if days is None or days > 90:
        return 10
    if days > 60:
        return 6
    if days > 30:
        return 3
    return 0


class RiskService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.sites = SiteRepository(session)
        self.risks = RiskRepository(session)

    def calculate(self, site_id: UUID, *, now: datetime | None = None) -> RiskCalculation:
        if self.sites.get(site_id) is None:
            raise NotFoundError("Site was not found.", code="site_not_found")
        calculation_time = now or datetime.now(UTC)
        if calculation_time.tzinfo is None:
            calculation_time = calculation_time.replace(tzinfo=UTC)

        anomalies = self.risks.unresolved_anomalies(site_id)
        counts = {severity.value: 0 for severity in AnomalySeverity}
        for anomaly in anomalies:
            counts[anomaly.severity.value] += 1
        severity_raw = sum(
            counts[severity.value] * weight for severity, weight in SEVERITY_WEIGHTS.items()
        )
        severity_score = min(SEVERITY_CAP, severity_raw)
        critical = CRITICAL_BONUS if counts[AnomalySeverity.CRITICAL.value] else 0
        volume = min(VOLUME_CAP, len(anomalies) * VOLUME_POINTS_PER_ANOMALY)

        latest = self.risks.latest_completed_inspection_at(site_id)
        if latest is not None and latest.tzinfo is None:
            latest = latest.replace(tzinfo=UTC)
        days_since = max(0, (calculation_time - latest).days) if latest else None
        recency = recency_points(days_since)
        score = min(100, severity_score + critical + volume + recency)
        level = classify_risk(score)
        factors: dict[str, Any] = {
            "formula_version": FORMULA_VERSION,
            "unresolved_anomaly_count": len(anomalies),
            "severity_counts": counts,
            "severity_weights": {
                severity.value: weight for severity, weight in SEVERITY_WEIGHTS.items()
            },
            "severity_raw_points": severity_raw,
            "severity_points": severity_score,
            "severity_cap": SEVERITY_CAP,
            "critical_bonus": critical,
            "critical_bonus_weight": CRITICAL_BONUS,
            "volume_points": volume,
            "volume_points_per_anomaly": VOLUME_POINTS_PER_ANOMALY,
            "volume_cap": VOLUME_CAP,
            "latest_completed_inspection_at": latest.isoformat() if latest else None,
            "days_since_completed_inspection": days_since,
            "recency_points": recency,
            "recency_bands": {
                "0_30_days": 0,
                "31_60_days": 3,
                "61_90_days": 6,
                "over_90_or_never": 10,
            },
            "classification_thresholds": CLASSIFICATION_THRESHOLDS,
            "score_before_cap": severity_score + critical + volume + recency,
            "score_cap": 100,
        }
        return RiskCalculation(score=score, level=level, factors=factors)

    def recalculate(self, site_id: UUID, *, now: datetime | None = None) -> RiskAssessment:
        site = self.sites.get(site_id)
        if site is None:
            raise NotFoundError("Site was not found.", code="site_not_found")
        self.session.flush()
        calculated_at = now or datetime.now(UTC)
        calculation = self.calculate(site_id, now=calculated_at)
        assessment = self.risks.add(
            RiskAssessment(
                site_id=site_id,
                score=calculation.score,
                level=calculation.level,
                formula_version=FORMULA_VERSION,
                factor_snapshot=calculation.factors,
                calculated_at=calculated_at,
            )
        )
        site.current_risk_score = calculation.score
        site.current_risk_level = calculation.level
        self.session.flush()
        return assessment

    def latest(self, site_id: UUID) -> RiskAssessment | None:
        if self.sites.get(site_id) is None:
            raise NotFoundError("Site was not found.", code="site_not_found")
        return self.risks.latest(site_id)

    def history(self, site_id: UUID, *, limit: int = 20) -> list[RiskAssessment]:
        if self.sites.get(site_id) is None:
            raise NotFoundError("Site was not found.", code="site_not_found")
        return self.risks.history(site_id, limit=limit)
