"""End-to-end integration tests for the CLI pipeline and the REST API.

The tests in this package exercise Task 01 (CLI) and Task 02 (API), which are
built on separate branches. Until those branches merge, each module guards its
import with ``pytest.importorskip`` so the suite stays green.
"""
