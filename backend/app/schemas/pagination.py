from pydantic import BaseModel, Field


class Page[T](BaseModel):
    items: list[T]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    has_next: bool


def page_response[T](items: list[T], *, page: int, page_size: int, total: int) -> Page[T]:
    return Page(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        has_next=page * page_size < total,
    )
