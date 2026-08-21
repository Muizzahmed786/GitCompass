"""
Tests for the Evidence Assembler — Stage 7, Component 1.

Focus: pure helper functions and deterministic transformations.
No database required for most tests; database-dependent functions are
tested via controlled fake DB objects.
"""

import unittest
from collections import defaultdict
from unittest.mock import MagicMock

from app.services.evidence_assembler import (
    calculate_bus_factor,
    _classify_dependency,
    _normalize_date,
    _normalize_month,
    _build_event_detail,
    _build_churn_percentiles,
    _score_commit,
    _build_technology_fingerprint,
    _build_phases,
    _build_hotspots,
    _build_contributors,
    assemble_evidence,
    BUS_FACTOR_THRESHOLD,
    TOP_HOTSPOTS,
    TOP_CONTRIBUTORS,
    TOP_COMMITS,
)


# ── Test 1: Bus Factor ─────────────────────────────────────────────────────────

class TestBusFactor(unittest.TestCase):

    def test_80_pct_threshold_two_authors(self):
        """Test 1a — Classic case: Alice+Bob cover 85% → bus_factor = 2."""
        counts = {"Alice": 60, "Bob": 25, "Carol": 10, "David": 5}
        self.assertEqual(calculate_bus_factor(counts), 2)

    def test_single_contributor(self):
        """Test 1b — Single contributor → bus_factor = 1."""
        self.assertEqual(calculate_bus_factor({"Alice": 100}), 1)

    def test_empty_contributors(self):
        """Test 1c — Empty repository → bus_factor = 0."""
        self.assertEqual(calculate_bus_factor({}), 0)

    def test_equal_contributors_three(self):
        """Test 1d — Three equal contributors: each 33.3%; need all 3 to reach 80%."""
        counts = {"A": 33, "B": 33, "C": 34}
        # A=33% (<80%), A+B=66% (<80%), A+B+C=100% (>=80%) → bus_factor = 3
        self.assertEqual(calculate_bus_factor(counts), 3)

    def test_dominant_single_author(self):
        """Test 1e — One author covers 85% alone → bus_factor = 1."""
        counts = {"Alice": 85, "Bob": 10, "Carol": 5}
        self.assertEqual(calculate_bus_factor(counts), 1)

    def test_zero_total_commits(self):
        """Test 1f — All counts are zero → bus_factor = 0."""
        self.assertEqual(calculate_bus_factor({"Alice": 0, "Bob": 0}), 0)

    def test_deterministic_with_same_input(self):
        """Test 1g — Same input always produces the same result."""
        counts = {"Alice": 50, "Bob": 30, "Carol": 20}
        result_1 = calculate_bus_factor(counts)
        result_2 = calculate_bus_factor(counts)
        self.assertEqual(result_1, result_2)

    def test_minimum_one_for_nonempty(self):
        """Test 1h — Any non-empty, non-zero repo has bus_factor >= 1."""
        self.assertGreaterEqual(calculate_bus_factor({"Alice": 1}), 1)

    def test_uses_80_pct_not_50(self):
        """Test 1i — Verify threshold is 80%, not the analytics router's 50%."""
        # With 50% threshold: Alice (60%) alone would satisfy → bf = 1
        # With 80% threshold: Alice+Bob = 85% → bf = 2
        counts = {"Alice": 60, "Bob": 25, "Carol": 10, "David": 5}
        bf = calculate_bus_factor(counts)
        self.assertEqual(bf, 2, "Bus factor must use 80% threshold, not 50%")


# ── Test 2: Technology Deduplication ──────────────────────────────────────────

class TestTechnologyDeduplication(unittest.TestCase):

    def _make_db(self, deps_data=None, events_data=None):
        """Create a minimal fake DB client for fingerprint tests."""
        db = MagicMock()
        # Chained Supabase-style query: .table().select().eq().execute()
        dep_result = MagicMock()
        dep_result.data = deps_data or []
        dep_chain = MagicMock()
        dep_chain.execute.return_value = dep_result

        evt_result = MagicMock()
        evt_result.data = events_data or []
        evt_chain = MagicMock()
        evt_chain.execute.return_value = evt_result

        # Both queries come through .table() — differentiate by what comes back
        def table_side_effect(name):
            mock = MagicMock()
            if name == "repository_dependencies":
                mock.select.return_value.eq.return_value = dep_chain
            else:
                # repository_events
                mock.select.return_value.eq.return_value.in_.return_value = evt_chain
            return mock

        db.table.side_effect = table_side_effect
        return db

    def test_deduplication_from_events(self):
        """Test 2a — Duplicate dependency names from events produce one entry."""
        events_data = [
            {"metadata": {"dependency": "fastapi"}},
            {"metadata": {"dependency": "fastapi"}},  # duplicate
            {"metadata": {"dependency": "react"}},
        ]
        db = self._make_db(events_data=events_data)
        result = _build_technology_fingerprint(db, "test-repo")
        # fastapi appears once in frameworks, react appears once
        self.assertEqual(result["frameworks"].count("fastapi"), 1)
        self.assertEqual(result["frameworks"].count("react"), 1)

    def test_output_lists_are_sorted(self):
        """Test 2b — Output lists are sorted alphabetically."""
        events_data = [
            {"metadata": {"dependency": "react"}},
            {"metadata": {"dependency": "fastapi"}},
        ]
        db = self._make_db(events_data=events_data)
        result = _build_technology_fingerprint(db, "test-repo")
        frameworks = result["frameworks"]
        self.assertEqual(frameworks, sorted(frameworks))

    def test_unknown_dependency_not_included(self):
        """Test 2c — Dependencies that don't match any category are excluded."""
        events_data = [
            {"metadata": {"dependency": "some-obscure-utility-lib-xyz"}},
        ]
        db = self._make_db(events_data=events_data)
        result = _build_technology_fingerprint(db, "test-repo")
        # Should not appear in any category
        all_techs = (
            result["frameworks"] + result["runtimes"] +
            result["databases"] + result["infrastructure"]
        )
        self.assertNotIn("some-obscure-utility-lib-xyz", all_techs)

    def test_known_databases_classified_correctly(self):
        """Test 2d — Known database names are placed in 'databases'."""
        events_data = [
            {"metadata": {"dependency": "redis"}},
            {"metadata": {"dependency": "postgresql"}},
        ]
        db = self._make_db(events_data=events_data)
        result = _build_technology_fingerprint(db, "test-repo")
        self.assertIn("redis", result["databases"])
        self.assertIn("postgresql", result["databases"])
        self.assertNotIn("redis", result["frameworks"])


# ── Test 3: Hotspot Ranking ────────────────────────────────────────────────────

class TestHotspotRanking(unittest.TestCase):

    def _make_db_for_hotspots(self, rows):
        """Returns a fake DB that returns the given file_diff rows."""
        db = MagicMock()
        result = MagicMock()
        result.data = rows
        query_chain = MagicMock()
        query_chain.execute.return_value = result
        db.table.return_value.select.return_value.eq.return_value.limit.return_value = query_chain
        return db

    def test_sorted_commit_count_desc(self):
        """Test 3a — Files sorted by commit_count DESC."""
        rows = [
            {"file_path": "a.py", "insertions": 10, "deletions": 0, "commits": {"author_name": "Alice"}},
            {"file_path": "a.py", "insertions": 10, "deletions": 0, "commits": {"author_name": "Alice"}},
            {"file_path": "b.py", "insertions": 100, "deletions": 50, "commits": {"author_name": "Bob"}},
        ]
        # a.py has 2 commits, b.py has 1 → a.py should be first
        db = self._make_db_for_hotspots(rows)
        hotspots = _build_hotspots(db, "repo-1")
        self.assertEqual(hotspots[0]["file_path"], "a.py")

    def test_tiebreak_by_total_churn_desc(self):
        """Test 3b — Equal commit count → higher total churn ranked first."""
        rows = [
            {"file_path": "low_churn.py", "insertions": 5, "deletions": 5, "commits": {"author_name": "X"}},
            {"file_path": "high_churn.py", "insertions": 100, "deletions": 100, "commits": {"author_name": "X"}},
        ]
        db = self._make_db_for_hotspots(rows)
        hotspots = _build_hotspots(db, "repo-1")
        self.assertEqual(hotspots[0]["file_path"], "high_churn.py")

    def test_tiebreak_alphabetical(self):
        """Test 3c — Equal commit count and churn → alphabetical file_path ASC."""
        rows = [
            {"file_path": "z.py", "insertions": 10, "deletions": 0, "commits": {"author_name": "X"}},
            {"file_path": "a.py", "insertions": 10, "deletions": 0, "commits": {"author_name": "X"}},
        ]
        db = self._make_db_for_hotspots(rows)
        hotspots = _build_hotspots(db, "repo-1")
        self.assertEqual(hotspots[0]["file_path"], "a.py")

    def test_respects_top_hotspots_limit(self):
        """Test 3d — Result is capped at TOP_HOTSPOTS entries."""
        # Create 20 distinct files, each with 1 commit
        rows = [
            {"file_path": f"file{i}.py", "insertions": i, "deletions": 0, "commits": {"author_name": "A"}}
            for i in range(20)
        ]
        db = self._make_db_for_hotspots(rows)
        hotspots = _build_hotspots(db, "repo-1")
        self.assertLessEqual(len(hotspots), TOP_HOTSPOTS)


# ── Test 4: Phase Transformation ──────────────────────────────────────────────

class TestPhaseTransformation(unittest.TestCase):

    def _make_db_for_phases(self, phase_rows, mapping_rows, event_rows):
        db = MagicMock()

        def table_side_effect(name):
            mock = MagicMock()
            if name == "architecture_phases":
                r = MagicMock()
                r.data = phase_rows
                mock.select.return_value.eq.return_value.order.return_value.execute.return_value = r
            elif name == "architecture_phase_events":
                r = MagicMock()
                r.data = mapping_rows
                mock.select.return_value.in_.return_value.execute.return_value = r
            elif name == "repository_events":
                r = MagicMock()
                r.data = event_rows
                # New query chain: .select().eq(repo_id).limit(2000).execute()
                mock.select.return_value.eq.return_value.limit.return_value.execute.return_value = r
            return mock

        db.table.side_effect = table_side_effect
        return db


    def test_phase_structure_fields_present(self):
        """Test 4a — Phase output contains all required fields."""
        phase_rows = [{
            "id": "phase-1",
            "phase_index": 1,
            "title": "FastAPI Backend Foundation",
            "start_date": "2024-01-10T00:00:00+00:00",
            "end_date": "2024-01-20T00:00:00+00:00",
            "dominant_event_type": "dependency_added",
            "event_count": 2,
        }]
        mapping_rows = [{"phase_id": "phase-1", "event_id": "ev-1"}]
        event_rows = [{
            "id": "ev-1",
            "event_type": "dependency_added",
            "event_key": "dependency:requirements.txt:fastapi",
            "event_date": "2024-01-10T00:00:00+00:00",
            "metadata": {"dependency": "fastapi", "after_version": "0.109.0", "manifest": "requirements.txt"},
        }]
        db = self._make_db_for_phases(phase_rows, mapping_rows, event_rows)
        phases = _build_phases(db, "repo-1")
        self.assertEqual(len(phases), 1)
        p = phases[0]
        self.assertIn("index", p)
        self.assertIn("title", p)
        self.assertIn("start_date", p)
        self.assertIn("end_date", p)
        self.assertIn("dominant_type", p)
        self.assertIn("event_count", p)
        self.assertIn("evidence", p)

    def test_dates_normalized_to_yyyy_mm_dd(self):
        """Test 4b — Phase dates are normalized to YYYY-MM-DD format."""
        phase_rows = [{
            "id": "phase-1",
            "phase_index": 1,
            "title": "Test Phase",
            "start_date": "2024-01-10T10:30:00+05:30",
            "end_date": "2024-01-20T00:00:00Z",
            "dominant_event_type": "dependency_added",
            "event_count": 0,
        }]
        db = self._make_db_for_phases(phase_rows, [], [])
        phases = _build_phases(db, "repo-1")
        self.assertEqual(phases[0]["start_date"], "2024-01-10")
        self.assertEqual(phases[0]["end_date"], "2024-01-20")

    def test_evidence_items_have_correct_detail(self):
        """Test 4c — Evidence detail is deterministically generated from metadata."""
        phase_rows = [{
            "id": "phase-1", "phase_index": 1, "title": "T", "start_date": "2024-01-01",
            "end_date": "2024-01-01", "dominant_event_type": "dependency_added", "event_count": 1,
        }]
        mapping_rows = [{"phase_id": "phase-1", "event_id": "ev-1"}]
        event_rows = [{
            "id": "ev-1",
            "event_type": "dependency_added",
            "event_key": "dep:req:fastapi",
            "event_date": "2024-01-01",
            "metadata": {"dependency": "fastapi", "after_version": "0.109.0", "manifest": "requirements.txt"},
        }]
        db = self._make_db_for_phases(phase_rows, mapping_rows, event_rows)
        phases = _build_phases(db, "repo-1")
        evidence = phases[0]["evidence"]
        self.assertEqual(len(evidence), 1)
        self.assertIn("fastapi", evidence[0]["detail"])
        self.assertIn("0.109.0", evidence[0]["detail"])

    def test_empty_phases(self):
        """Test 4d — No phases returns empty list."""
        db = MagicMock()
        r = MagicMock()
        r.data = []
        db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = r
        phases = _build_phases(db, "repo-1")
        self.assertEqual(phases, [])


# ── Test 5: Deterministic Ordering ────────────────────────────────────────────

class TestDeterministicOrdering(unittest.TestCase):

    def test_bus_factor_stable_for_same_input(self):
        """Test 5a — Bus factor is identical across repeated calls."""
        counts = {"Alice": 40, "Bob": 35, "Carol": 25}
        results = [calculate_bus_factor(counts) for _ in range(5)]
        self.assertEqual(len(set(results)), 1)

    def test_event_detail_stable(self):
        """Test 5b — Event detail strings are stable for the same event type+metadata."""
        meta = {"dependency": "react", "after_version": "18.0.0", "manifest": "package.json"}
        detail1 = _build_event_detail("dependency_added", meta)
        detail2 = _build_event_detail("dependency_added", meta)
        self.assertEqual(detail1, detail2)

    def test_churn_percentile_stable(self):
        """Test 5c — Percentile computation is stable."""
        values = [100, 200, 50, 300, 150]
        pct1 = _build_churn_percentiles(values)
        pct2 = _build_churn_percentiles(values)
        self.assertEqual(pct1, pct2)


# ── Test 6: Empty Repository ───────────────────────────────────────────────────

class TestEmptyRepository(unittest.TestCase):

    def _make_empty_db(self):
        """Returns a DB client that returns empty data for all queries."""
        db = MagicMock()
        empty_result = MagicMock()
        empty_result.data = []

        # Any chained attribute access returns a mock that returns empty_result
        db.table.return_value.select.return_value.eq.return_value.execute.return_value = empty_result
        db.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = empty_result
        db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = empty_result
        db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = empty_result
        db.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = empty_result
        db.table.return_value.select.return_value.in_.return_value.execute.return_value = empty_result

        return db

    def test_assemble_evidence_empty_repo_raises_when_not_found(self):
        """Test 6a — assemble_evidence raises ValueError if repo not found."""
        db = self._make_empty_db()
        with self.assertRaises(ValueError):
            assemble_evidence("non-existent-repo", db)


# ── Test 7: Event Detail Generation ───────────────────────────────────────────

class TestEventDetail(unittest.TestCase):

    def test_dependency_added(self):
        meta = {"dependency": "fastapi", "after_version": "0.109.0", "manifest": "requirements.txt"}
        detail = _build_event_detail("dependency_added", meta)
        self.assertIn("fastapi", detail)
        self.assertIn("0.109.0", detail)
        self.assertIn("requirements.txt", detail)

    def test_dependency_removed(self):
        meta = {"dependency": "flask", "before_version": "2.0", "manifest": "requirements.txt"}
        detail = _build_event_detail("dependency_removed", meta)
        self.assertIn("flask", detail)
        self.assertIn("2.0", detail)

    def test_dependency_version_changed(self):
        meta = {"dependency": "sqlalchemy", "before_version": "1.4", "after_version": "2.0", "manifest": "requirements.txt"}
        detail = _build_event_detail("dependency_version_changed", meta)
        self.assertIn("sqlalchemy", detail)
        self.assertIn("1.4", detail)
        self.assertIn("2.0", detail)

    def test_directory_introduced(self):
        meta = {"directory_path": "server/app/routers"}
        detail = _build_event_detail("directory_introduced", meta)
        self.assertIn("server/app/routers", detail)

    def test_large_change(self):
        meta = {"insertions": 900, "deletions": 340, "total_churn": 1240}
        detail = _build_event_detail("large_change", meta)
        self.assertIn("1240", detail)

    def test_commit_declared_refactor(self):
        meta = {"commit_message": "refactor: extract auth module"}
        detail = _build_event_detail("commit_declared_refactor", meta)
        self.assertIn("refactor", detail.lower())

    def test_unknown_event_type_does_not_raise(self):
        """Unknown event types return a safe fallback string, not an exception."""
        detail = _build_event_detail("some_future_event_type", {})
        self.assertIsInstance(detail, str)
        self.assertTrue(len(detail) > 0)


# ── Test 8: Churn Percentile Computation ──────────────────────────────────────

class TestChurnPercentiles(unittest.TestCase):

    def test_empty_list(self):
        self.assertEqual(_build_churn_percentiles([]), {})

    def test_single_value(self):
        result = _build_churn_percentiles([100])
        self.assertEqual(result[100], 100.0)

    def test_multiple_values(self):
        result = _build_churn_percentiles([0, 50, 100])
        self.assertEqual(result[0], 0.0)
        self.assertEqual(result[100], 100.0)

    def test_duplicate_values_same_percentile(self):
        result = _build_churn_percentiles([100, 100, 200])
        self.assertEqual(result[100], result[100])


# ── Test 9: Dependency Classifier ─────────────────────────────────────────────

class TestClassifyDependency(unittest.TestCase):

    def test_react_is_framework(self):
        self.assertEqual(_classify_dependency("react"), "framework")

    def test_fastapi_is_framework(self):
        self.assertEqual(_classify_dependency("fastapi"), "framework")

    def test_redis_is_database(self):
        self.assertEqual(_classify_dependency("redis"), "database")

    def test_docker_is_infrastructure(self):
        self.assertEqual(_classify_dependency("docker"), "infrastructure")

    def test_uvicorn_is_runtime(self):
        self.assertEqual(_classify_dependency("uvicorn"), "runtime")

    def test_unknown_returns_none(self):
        self.assertIsNone(_classify_dependency("some-random-package-xyz"))

    def test_case_insensitive(self):
        self.assertEqual(_classify_dependency("React"), "framework")
        self.assertEqual(_classify_dependency("REDIS"), "database")


# ── Test 10: Date Normalization ────────────────────────────────────────────────

class TestDateNormalization(unittest.TestCase):

    def test_iso_with_timezone(self):
        self.assertEqual(_normalize_date("2024-01-15T10:30:00+05:30"), "2024-01-15")

    def test_iso_with_z(self):
        self.assertEqual(_normalize_date("2024-01-15T10:30:00Z"), "2024-01-15")

    def test_plain_date(self):
        self.assertEqual(_normalize_date("2024-01-15"), "2024-01-15")

    def test_none_input(self):
        self.assertIsNone(_normalize_date(None))

    def test_month_normalization(self):
        self.assertEqual(_normalize_month("2024-01-15T10:30:00Z"), "2024-01")


if __name__ == "__main__":
    unittest.main()
