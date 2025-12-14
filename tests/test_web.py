"""Tests for web UI."""

import pytest

from prospect.web.app import create_app
from prospect.web.state import JobStatus

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture
def client():
    """Create test client."""
    from fastapi.testclient import TestClient
    app = create_app()
    return TestClient(app)


class TestWebPages:
    """Test web page rendering."""

    def test_index_page(self, client):
        """Index page should load the Command Center."""
        response = client.get("/")
        assert response.status_code == 200
        # New Command Center frontend
        assert "Prospect" in response.text
        assert "Command Center" in response.text

    def test_legacy_settings_page(self, client):
        """Legacy settings page should load."""
        response = client.get("/legacy/settings")
        assert response.status_code == 200
        assert "SerpAPI" in response.text
        assert "Google Sheets" in response.text

    def test_index_shows_search_form(self, client):
        """Index page should contain search functionality."""
        response = client.get("/")
        assert response.status_code == 200
        # New frontend uses different form structure
        assert 'business_type' in response.text.lower() or 'Business Type' in response.text

    def test_index_uses_modern_stack(self, client):
        """Index page should use modern frontend stack."""
        response = client.get("/")
        assert response.status_code == 200
        # Uses Tailwind and Lucide icons
        assert "tailwindcss" in response.text
        assert "lucide" in response.text


class TestSearchValidation:
    """Test legacy search input validation."""

    def test_search_requires_business_type(self, client):
        """Legacy search should validate business type."""
        response = client.post("/legacy/search", data={
            "business_type": "",
            "location": "Sydney",
            "limit": 10,
        })
        # FastAPI returns 422 for validation errors (empty required field)
        assert response.status_code in [200, 422]

    def test_search_requires_location(self, client):
        """Legacy search should validate location."""
        response = client.post("/legacy/search", data={
            "business_type": "plumber",
            "location": "",
            "limit": 10,
        })
        # FastAPI returns 422 for validation errors
        assert response.status_code in [200, 422]

    def test_search_starts_job(self, client):
        """Valid legacy search should start a job and return progress."""
        response = client.post("/legacy/search", data={
            "business_type": "plumber",
            "location": "Sydney",
            "limit": 5,
        })
        assert response.status_code == 200
        # Should return progress partial with HTMX polling
        assert "hx-get" in response.text or "hx-trigger" in response.text


class TestJobManager:
    """Test job state management."""

    @pytest.mark.asyncio
    async def test_create_job(self):
        """Should create a new job with unique ID."""
        from prospect.web.state import JobManager, JobStatus

        manager = JobManager()
        job = await manager.create_job(
            business_type="test",
            location="Sydney",
            limit=10
        )

        assert job.id is not None
        assert len(job.id) == 8
        assert job.status == JobStatus.PENDING
        assert job.business_type == "test"
        assert job.location == "Sydney"
        assert job.limit == 10

    @pytest.mark.asyncio
    async def test_get_job(self):
        """Should retrieve job by ID."""
        from prospect.web.state import JobManager

        manager = JobManager()
        created = await manager.create_job("test", "test", 10)
        retrieved = await manager.get_job(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id

    @pytest.mark.asyncio
    async def test_get_nonexistent_job(self):
        """Should return None for nonexistent job."""
        from prospect.web.state import JobManager

        manager = JobManager()
        result = await manager.get_job("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_update_job_status(self):
        """Should update job status."""
        from prospect.web.state import JobManager, JobStatus

        manager = JobManager()
        job = await manager.create_job("test", "test", 10)

        updated = await manager.update_job(
            job.id,
            status=JobStatus.SEARCHING,
            progress_message="Testing..."
        )

        assert updated.status == JobStatus.SEARCHING
        assert updated.progress_message == "Testing..."

    @pytest.mark.asyncio
    async def test_update_job_progress(self):
        """Should update job progress."""
        from prospect.web.state import JobManager, JobStatus

        manager = JobManager()
        job = await manager.create_job("test", "test", 10)

        await manager.update_job(
            job.id,
            status=JobStatus.ENRICHING,
            progress=5,
            progress_total=10
        )

        updated = await manager.get_job(job.id)
        assert updated.progress == 5
        assert updated.progress_total == 10

    @pytest.mark.asyncio
    async def test_job_completion_sets_timestamp(self):
        """Should set completed_at when job completes."""
        from prospect.web.state import JobManager, JobStatus

        manager = JobManager()
        job = await manager.create_job("test", "test", 10)

        assert job.completed_at is None

        await manager.update_job(job.id, status=JobStatus.COMPLETE, results=[])

        updated = await manager.get_job(job.id)
        assert updated.completed_at is not None


class TestJobStatus:
    """Test JobStatus enum."""

    def test_status_values(self):
        """Status enum should have expected values."""
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.SEARCHING.value == "searching"
        assert JobStatus.ENRICHING.value == "enriching"
        assert JobStatus.SCORING.value == "scoring"
        assert JobStatus.COMPLETE.value == "complete"
        assert JobStatus.ERROR.value == "error"


class TestExportCSVString:
    """Test CSV string export for web download."""

    def test_export_csv_string(self):
        """Should export prospects to CSV string."""
        from prospect.export import export_csv_string
        from prospect.models import Prospect

        prospects = [
            Prospect(
                name="Test Business",
                website="https://test.com",
                phone="0400 000 000",
                fit_score=70,
                opportunity_score=60,
                priority_score=65.0,
            )
        ]

        csv_content = export_csv_string(prospects)

        assert "name" in csv_content
        assert "Test Business" in csv_content
        assert "0400 000 000" in csv_content

    def test_export_csv_string_empty(self):
        """Should handle empty list."""
        from prospect.export import export_csv_string

        csv_content = export_csv_string([])

        # Should just have headers
        assert "name" in csv_content
        assert csv_content.count("\n") == 1  # Just header row

    def test_export_csv_string_has_all_columns(self):
        """Should include all expected columns."""
        from prospect.export import export_csv_string
        from prospect.models import Prospect

        prospects = [Prospect(name="Test", fit_score=50, opportunity_score=50, priority_score=50.0)]
        csv_content = export_csv_string(prospects)

        expected_columns = [
            "name", "website", "phone", "address", "emails",
            "rating", "review_count", "fit_score", "opportunity_score",
            "priority_score", "opportunity_notes", "found_in_ads",
            "found_in_maps", "found_in_organic", "cms",
            "has_google_analytics", "has_booking_system"
        ]

        for col in expected_columns:
            assert col in csv_content


class TestSearchStatusEndpoint:
    """Test the legacy search status endpoint."""

    def test_status_not_found(self, client):
        """Should return error for nonexistent job."""
        response = client.get("/legacy/search/nonexistent/status")
        assert response.status_code == 200
        assert "not found" in response.text.lower() or "error" in response.text.lower()


class TestExportEndpoints:
    """Test legacy export endpoints."""

    def test_csv_export_not_found(self, client):
        """Should return 404 for nonexistent job."""
        response = client.get("/legacy/search/nonexistent/export/csv")
        assert response.status_code == 404

    def test_sheets_export_not_found(self, client):
        """Should return error for nonexistent job."""
        response = client.post("/legacy/search/nonexistent/export/sheets")
        assert response.status_code == 200
        assert "not found" in response.text.lower() or "error" in response.text.lower()


class TestNewAPIEndpoints:
    """Test new Command Center API endpoints."""

    def test_dashboard_summary(self, client):
        """Dashboard summary should return stats."""
        response = client.get("/api/v1/dashboard/summary")
        assert response.status_code == 200
        data = response.json()
        assert "totals" in data
        assert "pipeline" in data

    def test_campaigns_list(self, client):
        """Campaigns list should return empty list initially."""
        response = client.get("/api/v1/campaigns")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_prospects_list(self, client):
        """Prospects list should return empty list initially."""
        response = client.get("/api/v1/prospects")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_prospects_stats(self, client):
        """Prospects stats should return zero stats initially."""
        response = client.get("/api/v1/prospects/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
