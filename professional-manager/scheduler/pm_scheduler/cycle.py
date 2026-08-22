from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from math import lcm

from pm_scheduler.contracts import LocalTimeSlot, TimeSlot

DEFAULT_MAX_PROJECT_CYCLE_WEEKS = 12


@dataclass(frozen=True)
class CycleDiagnostic:
    code: str
    project_cycle_length: int
    maximum_cycle_length: int
    message: str
    suggested_remediation: str


class ProjectCycleNormalizationError(ValueError):
    def __init__(self, diagnostic: CycleDiagnostic) -> None:
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


def derive_school_cycle_length(local_cycle_indexes: Iterable[int]) -> int:
    indexes = sorted(set(local_cycle_indexes))
    if not indexes or indexes != list(range(len(indexes))):
        raise ValueError("school cycle indexes must be contiguous from 0")
    return len(indexes)


def project_cycle_length(
    school_cycle_lengths: Iterable[int],
    maximum_cycle_length: int = DEFAULT_MAX_PROJECT_CYCLE_WEEKS,
) -> int:
    lengths = list(school_cycle_lengths)
    if not lengths or any(length < 1 for length in lengths):
        raise ValueError("school cycle lengths must be positive")
    normalized_length = lcm(*lengths)
    if normalized_length > maximum_cycle_length:
        raise ProjectCycleNormalizationError(
            CycleDiagnostic(
                code="project_cycle_limit_exceeded",
                project_cycle_length=normalized_length,
                maximum_cycle_length=maximum_cycle_length,
                message=(
                    f"Normalized project cycle is {normalized_length} weeks; "
                    f"maximum is {maximum_cycle_length}"
                ),
                suggested_remediation=(
                    "Align school cycle lengths or raise the configured limit after review"
                ),
            )
        )
    return normalized_length


def expand_project_slots(
    local_slots: Iterable[LocalTimeSlot],
    school_cycle_lengths: Mapping[str, int],
    maximum_cycle_length: int = DEFAULT_MAX_PROJECT_CYCLE_WEEKS,
) -> tuple[int, list[TimeSlot]]:
    normalized_length = project_cycle_length(
        school_cycle_lengths.values(), maximum_cycle_length
    )
    expanded: list[TimeSlot] = []
    for local_slot in sorted(
        local_slots,
        key=lambda slot: (
            slot.school_id,
            slot.local_cycle_week_index,
            slot.weekday_index,
            slot.starts_at_minute,
            slot.id,
        ),
    ):
        try:
            local_cycle_length = school_cycle_lengths[local_slot.school_id]
        except KeyError as exc:
            raise ValueError(
                f"Missing cycle length for school {local_slot.school_id}"
            ) from exc
        if local_slot.local_cycle_week_index >= local_cycle_length:
            raise ValueError("local slot week index is outside its school cycle")
        for project_week in range(
            local_slot.local_cycle_week_index,
            normalized_length,
            local_cycle_length,
        ):
            expanded.append(
                TimeSlot(
                    **local_slot.model_dump(exclude={"id"}),
                    id=f"{local_slot.id}@project-week-{project_week}",
                    project_cycle_week_index=project_week,
                )
            )
    return normalized_length, expanded
