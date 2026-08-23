from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field, ValidationError, model_validator


class EmptyParameters(BaseModel):
    pass


class TimeParameters(BaseModel):
    project_cycle_week_index: int | None = Field(default=None, ge=0)
    weekday_index: int | None = Field(default=None, ge=0, le=6)
    starts_at_minute: int | None = Field(default=None, ge=0, lt=1440)
    ends_at_minute: int | None = Field(default=None, gt=0, le=1440)
    slot_id: str | None = None

    @model_validator(mode="after")
    def valid_interval(self) -> "TimeParameters":
        if (
            self.starts_at_minute is not None
            and self.ends_at_minute is not None
            and self.starts_at_minute >= self.ends_at_minute
        ):
            raise ValueError("invalid_time_interval")
        return self


class LimitParameters(BaseModel):
    maximum: int = Field(ge=1, le=20)


class MinimumDaysParameters(BaseModel):
    minimum_days: int = Field(ge=1, le=7)


class BlockParameters(BaseModel):
    block_size: int = Field(ge=2, le=3)


class GapParameters(BaseModel):
    minimum_gap_minutes: int = Field(ge=1, le=720)


class ResourceTypeParameters(BaseModel):
    resource_type: str = Field(min_length=1, max_length=80)


@dataclass(frozen=True)
class RuleDefinition:
    target_keys: tuple[str, ...]
    severities: frozenset[str]
    label_ar: str
    category: str
    parameters_model: type[BaseModel]


def _rule(
    target: str | tuple[str, ...],
    severities: set[str],
    label: str,
    category: str,
    params: type[BaseModel] = EmptyParameters,
) -> RuleDefinition:
    return RuleDefinition(
        (target,) if isinstance(target, str) else target,
        frozenset(severities),
        label,
        category,
        params,
    )


RULE_REGISTRY: dict[str, RuleDefinition] = {
    "teacher_unavailable": _rule("teacher_id", {"hard"}, "عدم توفر المعلم", "availability", TimeParameters),
    "section_unavailable": _rule("section_id", {"hard"}, "عدم توفر الشعبة", "availability", TimeParameters),
    "resource_unavailable": _rule("resource_id", {"hard"}, "عدم توفر المورد", "availability", TimeParameters),
    "assignment_forbidden_time": _rule("assignment_id", {"hard"}, "وقت ممنوع للإسناد", "availability", TimeParameters),
    "assignment_required_time": _rule("assignment_id", {"hard"}, "وقت مطلوب للإسناد", "availability", TimeParameters),
    "teacher_preferred_time": _rule("teacher_id", {"soft"}, "وقت مفضل للمعلم", "availability", TimeParameters),
    "teacher_avoided_time": _rule("teacher_id", {"soft"}, "وقت غير مفضل للمعلم", "availability", TimeParameters),
    "assignment_preferred_time": _rule("assignment_id", {"soft"}, "وقت مفضل للإسناد", "availability", TimeParameters),
    "assignment_avoided_time": _rule("assignment_id", {"soft"}, "وقت غير مفضل للإسناد", "availability", TimeParameters),
    "subject_preferred_time": _rule("subject_id", {"soft"}, "وقت مفضل للمادة", "availability", TimeParameters),
    "subject_avoided_time": _rule("subject_id", {"soft"}, "وقت غير مفضل للمادة", "availability", TimeParameters),
    "assignment_max_per_day": _rule("assignment_id", {"hard", "soft"}, "الحد اليومي للإسناد", "distribution", LimitParameters),
    "assignment_min_days": _rule("assignment_id", {"hard", "soft"}, "الحد الأدنى لأيام التوزيع", "distribution", MinimumDaysParameters),
    "teacher_max_lessons_per_day": _rule("teacher_id", {"hard", "soft"}, "الحد اليومي للمعلم", "distribution", LimitParameters),
    "section_max_lessons_per_day": _rule("section_id", {"hard", "soft"}, "الحد اليومي للشعبة", "distribution", LimitParameters),
    "teacher_max_consecutive_lessons": _rule("teacher_id", {"hard", "soft"}, "أقصى حصص متتالية للمعلم", "consecutive", LimitParameters),
    "section_max_consecutive_lessons": _rule("section_id", {"hard", "soft"}, "أقصى حصص متتالية للشعبة", "consecutive", LimitParameters),
    "assignment_avoid_same_day_repeat": _rule("assignment_id", {"hard", "soft"}, "تجنب تكرار الإسناد في اليوم", "distribution", EmptyParameters),
    "assignment_require_consecutive_block": _rule("assignment_id", {"hard"}, "كتلة حصص متتالية", "consecutive", BlockParameters),
    "assignment_forbid_consecutive": _rule("assignment_id", {"hard", "soft"}, "منع الحصص المتتالية", "consecutive", EmptyParameters),
    "assignment_min_gap": _rule("assignment_id", {"hard", "soft"}, "فاصل أدنى بين حصص الإسناد", "consecutive", GapParameters),
    "assignments_same_time": _rule("assignment_ids", {"hard"}, "إسنادات في الوقت نفسه", "relationships"),
    "assignments_not_same_time": _rule("assignment_ids", {"hard"}, "إسنادات ليست في الوقت نفسه", "relationships"),
    "assignments_same_day": _rule("assignment_ids", {"hard", "soft"}, "إسنادات في اليوم نفسه", "relationships"),
    "assignments_different_day": _rule("assignment_ids", {"hard", "soft"}, "إسنادات في أيام مختلفة", "relationships"),
    "assignment_before_assignment": _rule("assignment_ids", {"hard", "soft"}, "إسناد قبل إسناد", "relationships"),
    "assignment_required_resource_type": _rule("assignment_id", {"hard"}, "نوع مورد إلزامي", "resources", ResourceTypeParameters),
    "assignment_preferred_resource": _rule(("assignment_id", "resource_id"), {"soft"}, "مورد مفضل", "resources"),
}


PROFILE_POLICIES: dict[str, dict[str, int]] = {
    "balanced": {"teacher_gaps": 8, "first_period_fairness": 5, "last_period_fairness": 5, "teaching_streaks": 7},
    "teacher_comfort": {"teacher_gaps": 18, "first_period_fairness": 10, "last_period_fairness": 12, "teaching_streaks": 16},
    "student_rhythm": {"teacher_gaps": 4, "first_period_fairness": 3, "last_period_fairness": 3, "teaching_streaks": 14},
    "administration_priorities": {"teacher_gaps": 4, "first_period_fairness": 4, "last_period_fairness": 4, "teaching_streaks": 5},
}

PROFILE_CATEGORY_MULTIPLIERS: dict[str, dict[str, int]] = {
    "balanced": {},
    "teacher_comfort": {"availability": 2, "consecutive": 2},
    "student_rhythm": {"distribution": 2, "consecutive": 2},
    "administration_priorities": {"relationships": 2, "resources": 2},
    "custom": {},
}


def effective_rule_weight(profile: str, rule_type: str, base_weight: int) -> int:
    definition = RULE_REGISTRY[rule_type]
    multiplier = PROFILE_CATEGORY_MULTIPLIERS[profile].get(definition.category, 1)
    return base_weight * multiplier


def validate_parameters(rule_type: str, parameters: dict[str, Any]) -> dict[str, Any]:
    definition = RULE_REGISTRY[rule_type]
    try:
        return definition.parameters_model.model_validate(parameters).model_dump(exclude_none=True)
    except ValidationError as exc:
        raise ValueError("invalid_rule_parameters") from exc
