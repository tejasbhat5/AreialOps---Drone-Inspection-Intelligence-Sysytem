from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    """Allow response schemas to validate SQLAlchemy model attributes."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")
