import unittest
from datetime import datetime, timezone
from app.services.phase_analyzer import (
    cluster_events_into_phases,
    generate_phase_title,
    calculate_phase_metadata,
    PHASE_GAP_DAYS
)

def create_event(date_str: str, event_type: str = "dependency_added", metadata: dict = None) -> dict:
    return {
        "id": "dummy",
        "event_date": datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc),
        "event_type": event_type,
        "metadata": metadata or {}
    }

class TestPhaseAnalyzer(unittest.TestCase):

    def test_single_phase(self):
        """Test 1 - Events close together should form a single phase."""
        events = [
            create_event("2026-01-01"),
            create_event("2026-01-05"),
            create_event("2026-01-12")
        ]
        phases = cluster_events_into_phases(events)
        self.assertEqual(len(phases), 1)
        self.assertEqual(len(phases[0]), 3)

    def test_14_day_boundary_exceeded(self):
        """Test 2 - Gap > 14 days should create a new phase."""
        events = [
            create_event("2026-01-01"),
            create_event("2026-01-10"),
            create_event("2026-01-25") # Gap between 10th and 25th is 15 days
        ]
        phases = cluster_events_into_phases(events)
        self.assertEqual(len(phases), 2)
        self.assertEqual(len(phases[0]), 2)
        self.assertEqual(len(phases[1]), 1)

    def test_exact_boundary(self):
        """Test 3 - Exact 14-day gap remains in the same phase."""
        events = [
            create_event("2026-01-01"),
            create_event("2026-01-15") # Gap is exactly 14 days
        ]
        phases = cluster_events_into_phases(events)
        self.assertEqual(len(phases), 1)
        self.assertEqual(len(phases[0]), 2)

    def test_irrelevant_events(self):
        """Test 4 - Irrelevant events (like ordinary commits) should be ignored for clustering."""
        events = [
            create_event("2026-01-01", "structure_created"),  # Actually "structure_created" isn't in SIGNIFICANT_EVENT_TYPES explicitly, wait!
            # Let's use valid ones from the analyzer
            create_event("2026-01-01", "directory_introduced"),
            create_event("2026-01-10", "ordinary_commit"),
            create_event("2026-01-20", "ordinary_commit"),
            create_event("2026-01-25", "dependency_added")
        ]
        # Gap between Jan 1 and Jan 25 is 24 days.
        # The ordinary commits in between should be ignored.
        phases = cluster_events_into_phases(events)
        self.assertEqual(len(phases), 2)
        self.assertEqual(phases[0][0]["event_type"], "directory_introduced")
        self.assertEqual(phases[1][0]["event_type"], "dependency_added")

    def test_empty_events(self):
        """Test 5 - Empty events return empty list."""
        phases = cluster_events_into_phases([])
        self.assertEqual(phases, [])

    def test_deterministic_titles(self):
        """Test 6 - Deterministic titles."""
        # 1. Recognized framework
        events_react = [create_event("2026-01-01", metadata={"dependency": "react"})]
        self.assertEqual(generate_phase_title(events_react, 1), "React Frontend Foundation")

        events_fastapi = [create_event("2026-01-01", metadata={"dependency": "fastapi"})]
        self.assertEqual(generate_phase_title(events_fastapi, 1), "FastAPI Backend Foundation")

        # 2. Dominant directory
        events_server = [
            create_event("2026-01-01", "directory_introduced", metadata={"path": "server/app"}),
            create_event("2026-01-02", "directory_introduced", metadata={"path": "server/models"})
        ]
        self.assertEqual(generate_phase_title(events_server, 1), "Backend Structure Expansion")

        # 3. Dominant event type
        events_refactor = [
            create_event("2026-01-01", "large_change"),
            create_event("2026-01-02", "large_change")
        ]
        self.assertEqual(generate_phase_title(events_refactor, 2), "Major Refactoring & Churn")

        # 4. Generic fallback
        events_generic = [create_event("2026-01-01", "dependency_added", metadata={"dependency": "some_unknown_lib"})]
        self.assertEqual(generate_phase_title(events_generic, 3), "Some_Unknown_Lib Integration")

if __name__ == "__main__":
    unittest.main()
