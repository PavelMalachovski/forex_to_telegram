"""Chart-related data models."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


class ChartData(BaseModel):
    """Chart data model."""

    timestamp: datetime = Field(description="Data timestamp")
    open: float = Field(description="Open price")
    high: float = Field(description="High price")
    low: float = Field(description="Low price")
    close: float = Field(description="Close price")
    volume: Optional[int] = Field(default=None, description="Volume")

    @validator("high")
    def validate_high(cls, v, values):
        """Validate high price."""
        if "low" in values and v < values["low"]:
            raise ValueError("High price must be >= low price")
        return v

    @validator("close")
    def validate_close(cls, v, values):
        """Validate close price."""
        if "low" in values and v < values["low"]:
            raise ValueError("Close price must be >= low price")
        if "high" in values and v > values["high"]:
            raise ValueError("Close price must be <= high price")
        return v


class ChartRequest(BaseModel):
    """Chart generation request model."""

    currency: str = Field(description="Currency code")
    event_time: datetime = Field(description="Event time")
    event_name: str = Field(description="Event name")
    impact_level: str = Field(default="medium", description="Impact level")
    window_hours: int = Field(default=2, description="Time window in hours")
    chart_type: str = Field(default="single", description="Chart type")

    @validator("currency")
    def validate_currency(cls, v):
        """Validate currency code."""
        valid_currencies = {
            "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD",
            "CNY", "INR", "BRL", "RUB", "KRW", "MXN", "SGD", "HKD",
            "XAU", "BTC", "ETH"
        }
        if v not in valid_currencies:
            raise ValueError(f"Invalid currency: {v}")
        return v

    @validator("impact_level")
    def validate_impact_level(cls, v):
        """Validate impact level."""
        valid_levels = {"high", "medium", "low"}
        if v not in valid_levels:
            raise ValueError(f"Invalid impact level: {v}")
        return v

    @validator("window_hours")
    def validate_window_hours(cls, v):
        """Validate window hours."""
        if v < 1 or v > 24:
            raise ValueError("Window hours must be between 1 and 24")
        return v

    @validator("chart_type")
    def validate_chart_type(cls, v):
        """Validate chart type."""
        valid_types = {"single", "multi", "cross_rate"}
        if v not in valid_types:
            raise ValueError(f"Invalid chart type: {v}")
        return v


class ChartResponse(BaseModel):
    """Chart generation response model."""

    success: bool = Field(description="Success status")
    chart_data: Optional[List[ChartData]] = Field(default=None, description="Chart data")
    chart_image: Optional[str] = Field(default=None, description="Base64 encoded chart image")
    error_message: Optional[str] = Field(default=None, description="Error message")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
