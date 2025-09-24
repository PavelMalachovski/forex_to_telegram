"""Forex news data models."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator


class ForexNewsBase(BaseModel):
    """Base forex news model."""

    date: datetime = Field(description="Event date")
    time: str = Field(description="Event time")
    currency: str = Field(description="Currency code")
    event: str = Field(description="Event name")
    actual: Optional[str] = Field(default=None, description="Actual value")
    forecast: Optional[str] = Field(default=None, description="Forecast value")
    previous: Optional[str] = Field(default=None, description="Previous value")
    impact_level: str = Field(description="Impact level")
    analysis: Optional[str] = Field(default=None, description="Analysis text")

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


class ForexNewsCreate(ForexNewsBase):
    """Forex news creation model."""
    pass


class ForexNewsUpdate(BaseModel):
    """Forex news update model."""

    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None
    analysis: Optional[str] = None


class ForexNews(ForexNewsBase):
    """Forex news model."""

    id: int = Field(description="News ID")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
