"""Chart endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from io import BytesIO

from src.database.connection import get_database
from src.services.chart_service import ChartService
from src.models.chart import ChartRequest, ChartResponse
from src.core.exceptions import ChartGenerationError, ValidationError

router = APIRouter()


def get_chart_service() -> ChartService:
    """Get chart service dependency."""
    return ChartService()


@router.post("/generate", response_model=ChartResponse)
async def generate_chart(
    chart_request: ChartRequest,
    db: AsyncSession = Depends(get_database),
    chart_service: ChartService = Depends(get_chart_service),
):
    """Generate a forex chart."""
    try:
        chart_response = await chart_service.generate_chart(db, chart_request)
        return chart_response
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ChartGenerationError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/generate/image")
async def generate_chart_image(
    chart_request: ChartRequest,
    db: AsyncSession = Depends(get_database),
    chart_service: ChartService = Depends(get_chart_service),
):
    """Generate a forex chart and return as image."""
    try:
        chart_buffer = await chart_service.generate_chart_image(db, chart_request)
        if not chart_buffer:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate chart")

        return StreamingResponse(
            BytesIO(chart_buffer),
            media_type="image/png",
            headers={"Content-Disposition": f"attachment; filename=forex_chart_{chart_request.currency}.png"}
        )
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ChartGenerationError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/currencies")
async def get_supported_currencies(
    chart_service: ChartService = Depends(get_chart_service),
):
    """Get list of supported currencies for charting."""
    try:
        currencies = await chart_service.get_supported_currencies()
        return {"currencies": currencies}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
