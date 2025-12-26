"""Research job database operations."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from supabase import Client

from .client import BaseSupabaseDB
from ..schemas.jobs import (
    JobStatus,
    JobStage,
    ResearchJob,
    JobStats,
    STAGE_PROGRESS,
)


class JobOperations(BaseSupabaseDB):
    """Database operations for async research jobs."""

    async def create_job(
        self,
        query: str,
        workspace_id: Optional[str] = None,
        template_type: str = "investigative",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> ResearchJob:
        """Create a new research job."""
        data = {
            "query": query,
            "workspace_id": workspace_id or self.workspace_id,
            "template_type": template_type,
            "parameters": parameters or {},
            "status": JobStatus.PENDING.value,
            "progress_pct": 0.0,
        }

        result = self.client.table("research_jobs").insert(data).execute()

        if result.data:
            return self._row_to_job(result.data[0])
        raise Exception("Failed to create research job")

    async def get_job(self, job_id: UUID) -> Optional[ResearchJob]:
        """Get a job by ID."""
        result = (
            self.client.table("research_jobs")
            .select("*")
            .eq("id", str(job_id))
            .execute()
        )

        if result.data:
            return self._row_to_job(result.data[0])
        return None

    async def get_job_raw(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        """Get raw job data as dict."""
        result = (
            self.client.table("research_jobs")
            .select("*")
            .eq("id", str(job_id))
            .execute()
        )

        return result.data[0] if result.data else None

    async def find_by_query_hash(
        self,
        query_hash: str,
        workspace_id: Optional[str] = None,
        statuses: Optional[List[JobStatus]] = None,
    ) -> Optional[ResearchJob]:
        """
        Find a job by normalized query hash.

        Args:
            query_hash: Hash of the normalized query
            workspace_id: Workspace to search in
            statuses: Optional list of statuses to filter (e.g., [PENDING, RUNNING])

        Returns:
            Most recent matching job or None
        """
        ws = workspace_id or self.workspace_id

        # First, get all jobs for this workspace and compute hash matches
        # Since we store raw query, we need to fetch and compare
        query = (
            self.client.table("research_jobs")
            .select("*")
            .eq("workspace_id", ws)
        )

        if statuses:
            query = query.in_("status", [s.value for s in statuses])

        result = query.order("created_at", desc=True).limit(100).execute()

        if not result.data:
            return None

        # Compare hashes
        for row in result.data:
            job_query = row.get("query", "")
            job_hash = self.hash_string(job_query.lower().strip())
            if job_hash == query_hash:
                return self._row_to_job(row)

        return None

    async def find_duplicate_jobs(
        self,
        query: str,
        workspace_id: Optional[str] = None,
        include_completed: bool = False,
    ) -> List[ResearchJob]:
        """
        Find jobs with identical or very similar queries.

        Args:
            query: Query string to search for
            workspace_id: Workspace to search in
            include_completed: Whether to include completed jobs

        Returns:
            List of matching jobs, most recent first
        """
        ws = workspace_id or self.workspace_id
        query_hash = self.hash_string(query.lower().strip())

        db_query = (
            self.client.table("research_jobs")
            .select("*")
            .eq("workspace_id", ws)
        )

        if not include_completed:
            db_query = db_query.in_("status", [
                JobStatus.PENDING.value,
                JobStatus.RUNNING.value
            ])

        result = db_query.order("created_at", desc=True).limit(50).execute()

        matches = []
        for row in result.data:
            job_query = row.get("query", "")
            job_hash = self.hash_string(job_query.lower().strip())
            if job_hash == query_hash:
                matches.append(self._row_to_job(row))

        return matches

    async def update_job_status(
        self,
        job_id: UUID,
        status: JobStatus,
        current_stage: Optional[str] = None,
        progress_pct: Optional[float] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update job status and optionally stage/progress."""
        data: Dict[str, Any] = {"status": status.value}

        if current_stage:
            data["current_stage"] = current_stage
        if progress_pct is not None:
            data["progress_pct"] = progress_pct
        if error_message:
            data["error_message"] = error_message

        # Set started_at when transitioning to running
        if status == JobStatus.RUNNING:
            data["started_at"] = datetime.utcnow().isoformat()

        # Set completed_at when transitioning to terminal states
        if status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            data["completed_at"] = datetime.utcnow().isoformat()

        self.client.table("research_jobs").update(data).eq(
            "id", str(job_id)
        ).execute()

    async def update_job_progress(
        self,
        job_id: UUID,
        stage: JobStage,
        progress_pct: Optional[float] = None,
    ) -> None:
        """Update job progress and stage."""
        # Use predefined progress if not specified
        pct = progress_pct if progress_pct is not None else STAGE_PROGRESS.get(stage, 0.0)

        self.client.table("research_jobs").update({
            "current_stage": stage.value,
            "progress_pct": pct,
        }).eq("id", str(job_id)).execute()

    async def complete_job(
        self,
        job_id: UUID,
        session_id: UUID,
        stats: Dict[str, Any],
    ) -> None:
        """Mark job as completed with stats."""
        self.client.table("research_jobs").update({
            "status": JobStatus.COMPLETED.value,
            "current_stage": JobStage.COMPLETED.value,
            "progress_pct": 100.0,
            "completed_at": datetime.utcnow().isoformat(),
            "session_id": str(session_id),
            "stats": stats,
        }).eq("id", str(job_id)).execute()

    async def fail_job(
        self,
        job_id: UUID,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Mark job as failed with error details."""
        data: Dict[str, Any] = {
            "status": JobStatus.FAILED.value,
            "completed_at": datetime.utcnow().isoformat(),
            "error_message": error_message,
        }
        if error_details:
            data["error_details"] = error_details

        self.client.table("research_jobs").update(data).eq(
            "id", str(job_id)
        ).execute()

    async def cancel_job(self, job_id: UUID) -> None:
        """Cancel a pending or running job."""
        self.client.table("research_jobs").update({
            "status": JobStatus.CANCELLED.value,
            "completed_at": datetime.utcnow().isoformat(),
        }).eq("id", str(job_id)).execute()

    async def set_topic_match(
        self,
        job_id: UUID,
        topic_id: Optional[UUID],
        confidence: float,
        reasoning: str,
    ) -> None:
        """Set topic matching result."""
        self.client.table("research_jobs").update({
            "matched_topic_id": str(topic_id) if topic_id else None,
            "topic_match_confidence": confidence,
            "topic_match_reasoning": reasoning,
        }).eq("id", str(job_id)).execute()

    async def list_jobs(
        self,
        workspace_id: Optional[str] = None,
        status: Optional[JobStatus] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[ResearchJob]:
        """List research jobs with filters."""
        query = self.client.table("research_jobs").select("*")

        ws = workspace_id or self.workspace_id
        query = query.eq("workspace_id", ws)

        if status:
            query = query.eq("status", status.value)

        result = (
            query.order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        return [self._row_to_job(row) for row in result.data]

    async def list_active_jobs(
        self,
        workspace_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ResearchJob]:
        """List active (pending/running) jobs."""
        query = self.client.table("research_jobs").select("*")

        ws = workspace_id or self.workspace_id
        query = query.eq("workspace_id", ws)
        query = query.in_("status", [JobStatus.PENDING.value, JobStatus.RUNNING.value])

        result = (
            query.order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        return [self._row_to_job(row) for row in result.data]

    async def delete_job(self, job_id: UUID) -> None:
        """Delete a job (soft delete not implemented - hard delete)."""
        self.client.table("research_jobs").delete().eq(
            "id", str(job_id)
        ).execute()

    def _row_to_job(self, row: Dict[str, Any]) -> ResearchJob:
        """Convert database row to ResearchJob."""
        return ResearchJob(
            id=row["id"],
            session_id=row.get("session_id"),
            query=row["query"],
            workspace_id=row["workspace_id"],
            template_type=row["template_type"],
            parameters=row.get("parameters", {}),
            status=JobStatus(row["status"]),
            current_stage=row.get("current_stage"),
            progress_pct=row.get("progress_pct", 0.0),
            started_at=row.get("started_at"),
            completed_at=row.get("completed_at"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            error_message=row.get("error_message"),
            error_details=row.get("error_details"),
            stats=row.get("stats"),
            matched_topic_id=row.get("matched_topic_id"),
            topic_match_confidence=row.get("topic_match_confidence"),
            topic_match_reasoning=row.get("topic_match_reasoning"),
        )
