from typing import Optional
import sqlite3
import statistics
import time

class LearningPath:
    """
    Simple learning path manager that records quiz results and suggests next topics / difficulty
    Backed by the DB wrapper (lightweight) — we pass db in app usage.
    """
    def __init__(self, db=None):
        self.db = db

    def record_quiz_result(self, user: str, topic: str, score: int, total: int):
        # store simple record in DB wrapper
        if self.db:
            self.db.add_quiz_result(user, topic, score, total)

    def adapt_difficulty(self, user: str, requested_level: str) -> str:
        # Basic heuristic: if user is performing well, bump difficulty, else lower
        recent = self.db.get_recent_quiz_scores(user, limit=5) if self.db else []
        if not recent:
            return requested_level
        avg = sum([r['score']/max(1,r['total']) for r in recent]) / len(recent)
        if avg > 0.85:
            # increase requested one level
            if requested_level == "Easy": return "Medium"
            if requested_level == "Medium": return "Hard"
            return "Hard"
        elif avg < 0.5:
            if requested_level == "Hard": return "Medium"
            if requested_level == "Medium": return "Easy"
            return "Easy"
        return requested_level

    def suggest_next_topic(self, user: str) -> Optional[str]:
        # Very simple: look at weakest topic from history
        hist = self.db.get_all_quiz_history(user) if self.db else []
        if not hist:
            return None
        # compute average correctness per topic
        scores = {}
        counts = {}
        for r in hist:
            t = r['topic']
            scores[t] = scores.get(t, 0) + r['score']
            counts[t] = counts.get(t, 0) + r['total']
        ratios = {t: scores[t] / counts[t] for t in scores}
        worst = min(ratios, key=ratios.get)
        return worst
