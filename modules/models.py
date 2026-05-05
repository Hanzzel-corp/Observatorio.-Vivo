"""
P2 #23: Modelos Pydantic separados
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class SettingsModel(BaseModel):
    outbreak_threshold: Optional[float] = 45.0
    api_reset_token: Optional[str] = ""


class SignalOriginResponse(BaseModel):
    term: str
    signal_type: str
    explanation: str
    summary: Dict[str, Any]
    outbreak: Optional[Dict[str, Any]]
    sources_breakdown: Dict[str, int]
    regions_breakdown: Dict[str, int]
    first_signal: Optional[Dict[str, Any]]
    last_signal: Optional[Dict[str, Any]]
    evidence_titles: List[Dict[str, Any]]
    timeline: List[Dict[str, Any]]
    total_hits: int


# Clases que se usan en endpoints
class WatchIn(BaseModel):
    term: str


class AliasIn(BaseModel):
    alias: str
    canonical: str
    phenomenon: Optional[str] = None


class SettingsIn(BaseModel):
    outbreak_threshold: Optional[float] = None
    telegram_enabled: Optional[bool] = None
    telegram_bot_token: Optional[str] = None
