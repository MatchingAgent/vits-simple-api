from fastapi import APIRouter, status
from pydantic import BaseModel, Field

router = APIRouter()


class HealthcheckResponse(BaseModel):
    message: str = Field(examples=["ok"])


@router.get(
    "/healthcheck",
    status_code=status.HTTP_200_OK,
    tags=["Healthcheck"],
    summary="Check system status",
    description="Check system status.",
)
def healthcheck() -> HealthcheckResponse:
    return HealthcheckResponse(message="ok")
