# -*- coding: utf-8 -*-
"""
M6: Mentor Feedback Collector (Spiral B - External Calibration)
Records feedback from mentors/users to calibrate the cognitive system.
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List


class MentorFeedbackCollector:
    """Collects and stores mentor feedback for calibration.

    Spiral B component: external feedback drives knowledge refinement.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path.home() / ".TuringClaw" / "cognitive" / "calibration"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.data_dir / "mentor_feedback.json"
        self._feedback: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        """Load existing feedback from file."""
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Handle both old format (dict with 'feedback_events') and new format (list)
                if isinstance(data, list):
                    self._feedback = data
                elif isinstance(data, dict) and 'feedback_events' in data:
                    self._feedback = data['feedback_events']
                else:
                    self._feedback = []
            except (json.JSONDecodeError, IOError):
                self._feedback = []
        else:
            self._feedback = []

    def _save(self):
        """Save feedback to file."""
        tmp = self.file_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._feedback, f, ensure_ascii=False, indent=2)
        tmp.replace(self.file_path)

    def add_feedback(self, topic: str, feedback: str, rating: int = 0,
                     context: Optional[str] = None) -> Dict[str, Any]:
        """Add a mentor feedback entry.

        Args:
            topic: What the feedback is about
            feedback: The feedback text
            rating: 0-5 rating (0=negative, 5=very positive)
            context: Optional context information

        Returns:
            The created feedback entry dict
        """
        entry = {
            "topic": topic,
            "feedback": feedback,
            "rating": max(0, min(5, rating)),
            "context": context or "",
            "timestamp": datetime.now().isoformat(),
        }
        self._feedback.append(entry)
        self._save()
        return entry

    def get_feedback(self, topic: Optional[str] = None,
                     limit: int = 50) -> List[Dict[str, Any]]:
        """Get feedback entries, optionally filtered by topic.

        Args:
            topic: Optional topic filter
            limit: Max entries to return

        Returns:
            List of feedback entries (most recent first)
        """
        if topic:
            filtered = [f for f in self._feedback if f.get("topic") == topic]
        else:
            filtered = list(self._feedback)
        return sorted(filtered, key=lambda x: x.get("timestamp", ""),
                      reverse=True)[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Get feedback statistics."""
        total = len(self._feedback)
        if total == 0:
            return {"total": 0, "avg_rating": 0.0, "topics": {}}
        avg_rating = sum(f.get("rating", 0) for f in self._feedback) / total
        topics: Dict[str, int] = {}
        for f in self._feedback:
            t = f.get("topic", "unknown")
            topics[t] = topics.get(t, 0) + 1
        return {"total": total, "avg_rating": round(avg_rating, 2), "topics": topics}

    def clear(self):
        """Clear all feedback."""
        self._feedback = []
        self._save()
