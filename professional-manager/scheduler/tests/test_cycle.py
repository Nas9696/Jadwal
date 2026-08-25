import pytest

from pm_scheduler.contracts import LocalTimeSlot, slots_overlap
from pm_scheduler.cycle import (
    ProjectCycleNormalizationError,
    derive_school_cycle_length,
    expand_project_slots,
    project_cycle_length,
)


def local_slot(school: str, local_week: int, suffix: str) -> LocalTimeSlot:
    return LocalTimeSlot(
        id=f"{school}-{suffix}",
        school_id=school,
        week_pattern_id=f"{school}-pattern-{local_week}",
        local_cycle_week_index=local_week,
        weekday_index=0,
        starts_at_minute=8 * 60,
        ends_at_minute=8 * 60 + 45,
        period=1,
    )


def test_explicit_phase_offset_aligns_local_week_to_project_week() -> None:
    slots = [local_slot("A", 0, "a"), local_slot("B", 0, "b0"), local_slot("B", 1, "b1")]
    length, phase_zero = expand_project_slots(slots, {"A": 1, "B": 2}, {"A": 0, "B": 0})
    assert length == 2
    assert [
        (x.local_cycle_week_index, x.project_cycle_week_index)
        for x in phase_zero
        if x.school_id == "B"
    ] == [(0, 0), (1, 1)]
    _, phase_one = expand_project_slots(slots, {"A": 1, "B": 2}, {"A": 0, "B": 1})
    assert [
        (x.local_cycle_week_index, x.project_cycle_week_index)
        for x in phase_one
        if x.school_id == "B"
    ] == [(0, 1), (1, 0)]


def test_phase_two_vs_three_has_global_cycle_six_and_rejects_invalid_phase() -> None:
    slots = [local_slot("A", 0, "a"), local_slot("B", 0, "b")]
    length, _ = expand_project_slots(slots, {"A": 2, "B": 3}, {"A": 1, "B": 2})
    assert length == 6
    with pytest.raises(ValueError, match="phase offset"):
        expand_project_slots(slots, {"A": 2, "B": 3}, {"A": 2, "B": 0})


def test_one_week_cycle_repeats_across_two_week_project() -> None:
    length, slots = expand_project_slots(
        [local_slot("school-a", 0, "a"), local_slot("school-b", 0, "a")],
        {"school-a": 1, "school-b": 2},
    )
    school_a_weeks = [
        slot.project_cycle_week_index for slot in slots if slot.school_id == "school-a"
    ]
    assert length == 2
    assert school_a_weeks == [0, 1]


def test_shared_teacher_can_collide_in_project_week_different_from_local_index() -> None:
    _, slots = expand_project_slots(
        [local_slot("school-a", 0, "a"), local_slot("school-b", 1, "b")],
        {"school-a": 1, "school-b": 2},
    )
    project_week_one = [slot for slot in slots if slot.project_cycle_week_index == 1]
    assert {slot.local_cycle_week_index for slot in project_week_one} == {0, 1}
    assert len(project_week_one) == 2
    assert slots_overlap(project_week_one[0], project_week_one[1])


def test_two_and_three_week_cycles_expand_to_six_weeks() -> None:
    length, slots = expand_project_slots(
        [
            local_slot("school-a", 0, "a"),
            local_slot("school-a", 1, "b"),
            local_slot("school-b", 0, "a"),
            local_slot("school-b", 1, "b"),
            local_slot("school-b", 2, "c"),
        ],
        {"school-a": 2, "school-b": 3},
    )
    assert length == 6
    assert [
        slot.project_cycle_week_index
        for slot in slots
        if slot.school_id == "school-a" and slot.local_cycle_week_index == 0
    ] == [0, 2, 4]
    assert [
        slot.project_cycle_week_index
        for slot in slots
        if slot.school_id == "school-b" and slot.local_cycle_week_index == 2
    ] == [2, 5]


def test_cycle_limit_returns_actionable_diagnostic_without_expansion() -> None:
    with pytest.raises(ProjectCycleNormalizationError) as error:
        project_cycle_length([5, 7])
    assert error.value.diagnostic.code == "project_cycle_limit_exceeded"
    assert error.value.diagnostic.project_cycle_length == 35
    assert error.value.diagnostic.maximum_cycle_length == 12
    assert error.value.diagnostic.suggested_remediation


def test_school_cycle_indexes_must_be_contiguous() -> None:
    assert derive_school_cycle_length([0, 1, 2]) == 3
    with pytest.raises(ValueError, match="contiguous"):
        derive_school_cycle_length([0, 2])
