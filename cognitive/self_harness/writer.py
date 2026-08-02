# -*- coding: utf-8 -*-
"""
M6: Self-Harness Writer (Intersection Point)
Writes calibrated knowledge from both spirals into the architecture.
This is the convergence point where Spiral A (self-evolution) and
Spiral B (external calibration) merge into actionable knowledge.
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List


class SelfHarnessWriter:
    """Writes knowledge entries that merge self-evolution + external calibration.

    The writer is the intersection of the dual spiral:
    - Spiral A provides: tool stats, execution intuition, prompt patterns
    - Spiral B provides: mentor feedback, market validation, tacit distillation
    - Writer merges both into actionable knowledge entries
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path.home() / ".TuringClaw" / "cognitive" / "self_harness"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.data_dir / "knowledge_entries.json"
        self._entries: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        """Load existing entries from file."""
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self._entries = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._entries = []

    def _save(self):
        """Save entries to file."""
        tmp = self.file_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._entries, f, ensure_ascii=False, indent=2)
        tmp.replace(self.file_path)

    def write(self, title: str, content: str,
              source: str = "self_harness",
              spiral_a_data: Optional[Dict] = None,
              spiral_b_data: Optional[Dict] = None,
              confidence: float = 0.5,
              tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Write a knowledge entry.

        Args:
            title: Entry title
            content: Knowledge content
            source: Source identifier
            spiral_a_data: Data from Spiral A (self-evolution)
            spiral_b_data: Data from Spiral B (external calibration)
            confidence: 0.0-1.0 confidence level
            tags: Optional tags for categorization

        Returns:
            The created knowledge entry dict
        """
        entry = {
            "id": f"kh_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            "title": title,
            "content": content,
            "source": source,
            "spiral_a": spiral_a_data or {},
            "spiral_b": spiral_b_data or {},
            "confidence": max(0.0, min(1.0, confidence)),
            "tags": tags or [],
            "timestamp": datetime.now().isoformat(),
        }
        self._entries.append(entry)
        self._save()
        return entry

    def get_entries(self, tag: Optional[str] = None,
                    min_confidence: float = 0.0,
                    limit: int = 50) -> List[Dict[str, Any]]:
        """Get knowledge entries with optional filters."""
        filtered = [
            e for e in self._entries
            if e.get("confidence", 0) >= min_confidence
            and (tag is None or tag in e.get("tags", []))
        ]
        return sorted(filtered, key=lambda x: x.get("timestamp", ""),
                      reverse=True)[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        total = len(self._entries)
        if total == 0:
            return {"total": 0, "avg_confidence": 0.0, "tags": {}}
        avg_conf = sum(e.get("confidence", 0) for e in self._entries) / total
        tags: Dict[str, int] = {}
        for e in self._entries:
            for t in e.get("tags", []):
                tags[t] = tags.get(t, 0) + 1
        return {
            "total": total,
            "avg_confidence": round(avg_conf, 3),
            "tags": tags,
        }

    def add_entry(self, title: str, content: str, **kwargs) -> Dict[str, Any]:
        """Alias for write()."""
        return self.write(title, content, **kwargs)

    def record(self, title: str, content: str, **kwargs) -> Dict[str, Any]:
        """Alias for write()."""
        return self.write(title, content, **kwargs)

    def clear(self):
        """Clear all entries."""
        self._entries = []
        self._save()
