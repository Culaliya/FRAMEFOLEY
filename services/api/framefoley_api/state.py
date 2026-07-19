"""Validated project state transitions."""

from __future__ import annotations

from framefoley_api.errors import PublicError
from framefoley_api.models import FrameFoleyProject, ProjectPhase, ProjectState

ALLOWED_TRANSITIONS: dict[ProjectState, set[ProjectState]] = {
    ProjectState.CREATED: {ProjectState.SOURCE_UPLOADING, ProjectState.SOURCE_READY},
    ProjectState.SOURCE_UPLOADING: {ProjectState.SOURCE_READY, ProjectState.SOURCE_FAILED},
    ProjectState.SOURCE_FAILED: {ProjectState.SOURCE_UPLOADING},
    ProjectState.SOURCE_READY: {ProjectState.CUEING},
    ProjectState.CUEING: {ProjectState.GENERATION_QUEUED},
    ProjectState.GENERATION_QUEUED: {ProjectState.GENERATING, ProjectState.GENERATION_FAILED},
    ProjectState.GENERATING: {
        ProjectState.AUDITION_READY,
        ProjectState.GENERATION_PARTIAL,
        ProjectState.GENERATION_FAILED,
    },
    ProjectState.GENERATION_PARTIAL: {ProjectState.GENERATING, ProjectState.AUDITION_READY},
    ProjectState.GENERATION_FAILED: {ProjectState.GENERATION_QUEUED},
    ProjectState.AUDITION_READY: {ProjectState.APPROVALS_COMPLETE},
    ProjectState.APPROVALS_COMPLETE: {ProjectState.RENDERING},
    ProjectState.RENDERING: {ProjectState.RENDER_READY, ProjectState.RENDER_FAILED},
    ProjectState.RENDER_FAILED: {ProjectState.RENDERING},
    ProjectState.RENDER_READY: {ProjectState.EXPORTING},
    ProjectState.EXPORTING: {ProjectState.COMPLETE, ProjectState.EXPORT_FAILED},
    ProjectState.EXPORT_FAILED: {ProjectState.EXPORTING},
    ProjectState.COMPLETE: set(),
}

PHASE_FOR_STATE: dict[ProjectState, ProjectPhase] = {
    ProjectState.CREATED: ProjectPhase.SOURCE,
    ProjectState.SOURCE_UPLOADING: ProjectPhase.SOURCE,
    ProjectState.SOURCE_FAILED: ProjectPhase.SOURCE,
    ProjectState.SOURCE_READY: ProjectPhase.CUE,
    ProjectState.CUEING: ProjectPhase.CUE,
    ProjectState.GENERATION_QUEUED: ProjectPhase.GENERATE,
    ProjectState.GENERATING: ProjectPhase.GENERATE,
    ProjectState.GENERATION_PARTIAL: ProjectPhase.GENERATE,
    ProjectState.GENERATION_FAILED: ProjectPhase.GENERATE,
    ProjectState.AUDITION_READY: ProjectPhase.AUDITION,
    ProjectState.APPROVALS_COMPLETE: ProjectPhase.RENDER,
    ProjectState.RENDERING: ProjectPhase.RENDER,
    ProjectState.RENDER_FAILED: ProjectPhase.RENDER,
    ProjectState.RENDER_READY: ProjectPhase.EXPORT,
    ProjectState.EXPORTING: ProjectPhase.EXPORT,
    ProjectState.EXPORT_FAILED: ProjectPhase.EXPORT,
    ProjectState.COMPLETE: ProjectPhase.COMPLETE,
}


def transition(project: FrameFoleyProject, target: ProjectState) -> None:
    current = ProjectState(project.state)
    if target not in ALLOWED_TRANSITIONS[current]:
        raise PublicError(
            "PROJECT_STATE_INVALID",
            f"Project cannot transition from {current.value} to {target.value}.",
            status_code=409,
        )
    project.state = target
    project.phase = PHASE_FOR_STATE[target]
