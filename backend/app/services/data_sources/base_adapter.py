"""
base_adapter.py
---------------
Abstract base class and contract for all FieldIQ dataset adapters.
Guarantees strict provenance tracking, schema normalization,
reproducibility, and adherence to the Real Data Principle.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import pandas as pd

from backend.app.services.data_sources.provenance import SourceProvenanceRecord


class BaseDatasetAdapter(ABC):
    """Abstract interface for external cricket dataset ingestion and normalization."""

    def __init__(self, dataset_id: str, dataset_version: str):
        self.dataset_id = dataset_id
        self.dataset_version = dataset_version

    @property
    @abstractmethod
    def provenance(self) -> SourceProvenanceRecord:
        """Returns authoritative provenance metadata for this data source."""
        pass

    @abstractmethod
    def inspect_schema(self, raw_path: str) -> Dict[str, Any]:
        """Inspects raw files and returns column metadata, types, and null counts."""
        pass

    @abstractmethod
    def normalize_to_canonical(
        self,
        raw_path: str,
        limit_matches: Optional[int] = None,
        filter_criteria: Optional[Dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """
        Parses raw data into FieldIQ's canonical delivery schema:
        [DatasetId, DatasetVersion, Batter, BowlerName, GameId, MatchDate,
         Competition, MatchFormat, Innings, Over, BallInOver, RunsBatter,
         Extras, RunsTotal, ExtraType, Wicket, WicketMethod, WhoOut,
         BattingTeam, BowlingTeam, Venue, Target, Zone, ShotDirection, Distance]
        """
        pass

    @abstractmethod
    def validate(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Runs cricket validation checks (runs, wickets, bounds, formats)."""
        pass
