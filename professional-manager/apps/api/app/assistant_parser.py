from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Grade,
    PeriodTemplate,
    Resource,
    School,
    Section,
    SectionOffering,
    Stage,
    Subject,
    Teacher,
    TeacherSchoolMembership,
    TeachingAssignment,
    TeachingAssignmentSection,
    TeachingAssignmentTeacher,
    TimetableProject,
    TimetableProjectSchool,
)

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
DIACRITICS = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]")
DAY_INDEX = {
    "الاحد": 0,
    "الاثنين": 1,
    "الاثنان": 1,
    "الثلاثاء": 2,
    "الاربعاء": 3,
    "الخميس": 4,
    "الجمعة": 5,
    "السبت": 6,
}
NUMBER_WORDS = {
    "واحد": 1,
    "واحدة": 1,
    "يوم": 1,
    "يومين": 2,
    "اثنين": 2,
    "اثنتين": 2,
    "ثلاث": 3,
    "ثلاثة": 3,
    "اربعة": 4,
    "اربع": 4,
    "خمسة": 5,
    "خمس": 5,
    "ستة": 6,
    "ست": 6,
    "سبعة": 7,
    "سبع": 7,
}
ORDINALS = {
    "الاولي": 1,
    "الاول": 1,
    "الثانية": 2,
    "الثاني": 2,
    "الثالثة": 3,
    "الثالث": 3,
    "الرابعة": 4,
    "الرابع": 4,
    "الخامسة": 5,
    "الخامس": 5,
    "السادسة": 6,
    "السادس": 6,
    "السابعة": 7,
    "السابع": 7,
    "الثامنة": 8,
    "الثامن": 8,
}


def normalize_arabic(value: str) -> str:
    value = DIACRITICS.sub("", value.translate(ARABIC_DIGITS)).replace("ـ", "")
    # Preserve taa marbuta in proper names; broad letter folding can silently
    # turn distinct canonical entities into the same reference.
    value = value.translate(str.maketrans("أإآؤئى", "اااويي"))
    value = re.sub(r"[^\w\s-]", " ", value.lower())
    return re.sub(r"\s+", " ", value).strip()


@dataclass
class Resolution:
    status: str
    entity_id: str | None = None
    label: str | None = None
    choices: list[dict[str, str | None]] | None = None
    key: str | None = None


class ProjectEntityResolver:
    def __init__(
        self,
        db: Session,
        tenant_id: uuid.UUID,
        project: TimetableProject,
        resolutions: dict[str, str],
    ) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.project = project
        self.resolutions = resolutions
        self.scopes = list(
            db.scalars(
                select(TimetableProjectSchool).where(
                    TimetableProjectSchool.tenant_id == tenant_id,
                    TimetableProjectSchool.timetable_project_id == project.id,
                )
            )
        )
        self.school_ids = {scope.school_id for scope in self.scopes}
        self.term_by_school = {scope.school_id: scope.term_id for scope in self.scopes}
        self.school_names = {
            str(row.id): row.name_ar
            for row in db.scalars(select(School).where(School.id.in_(self.school_ids)))
        }

    def teacher(self, mention: str) -> Resolution:
        memberships = list(
            self.db.scalars(
                select(TeacherSchoolMembership).where(
                    TeacherSchoolMembership.tenant_id == self.tenant_id,
                    TeacherSchoolMembership.school_id.in_(self.school_ids),
                    TeacherSchoolMembership.is_active.is_(True),
                )
            )
        )
        ids = {row.teacher_id for row in memberships}
        rows = list(
            self.db.scalars(
                select(Teacher).where(
                    Teacher.tenant_id == self.tenant_id,
                    Teacher.id.in_(ids),
                    Teacher.is_active.is_(True),
                )
            )
        )
        return self._resolve("teacher", mention, rows, lambda row: row.name_ar, lambda row: [row.name_ar, row.canonical_code])

    def subject(self, mention: str) -> Resolution:
        rows = list(
            self.db.scalars(
                select(Subject).where(
                    Subject.tenant_id == self.tenant_id,
                    Subject.school_id.in_(self.school_ids),
                    Subject.is_active.is_(True),
                )
            )
        )
        return self._resolve("subject", mention, rows, lambda row: row.name_ar, lambda row: [row.name_ar, row.code])

    def resource(self, mention: str) -> Resolution:
        rows = list(
            self.db.scalars(
                select(Resource).where(
                    Resource.tenant_id == self.tenant_id,
                    Resource.school_id.in_(self.school_ids),
                    Resource.is_active.is_(True),
                )
            )
        )
        return self._resolve("resource", mention, rows, lambda row: row.name_ar, lambda row: [row.name_ar, row.code])

    def section(self, mention: str) -> Resolution:
        rows = list(
            self.db.execute(
                select(Section, Grade, Stage)
                .join(Grade, Grade.id == Section.grade_id)
                .join(Stage, Stage.id == Grade.stage_id)
                .where(
                    Section.tenant_id == self.tenant_id,
                    Stage.school_id.in_(self.school_ids),
                )
            )
        )
        wrappers = [
            _Entity(str(section.id), f"{grade.name_ar} {section.name_ar}", [section.name_ar, f"{grade.name_ar} {section.name_ar}"])
            for section, grade, _ in rows
        ]
        return self._resolve("section", mention, wrappers, lambda row: row.label, lambda row: row.aliases)

    def assignment(self, mention: str) -> Resolution:
        assignments = list(
            self.db.scalars(
                select(TeachingAssignment).where(
                    TeachingAssignment.tenant_id == self.tenant_id,
                    TeachingAssignment.school_id.in_(self.school_ids),
                )
            )
        )
        assignments = [
            row for row in assignments if self.term_by_school.get(row.school_id) == row.term_id
        ]
        wrappers: list[_Entity] = []
        for assignment in assignments:
            subject = self.db.get(Subject, assignment.subject_id)
            teacher_ids = list(
                self.db.scalars(
                    select(TeachingAssignmentTeacher.teacher_id).where(
                        TeachingAssignmentTeacher.teaching_assignment_id == assignment.id
                    )
                )
            )
            teachers = (
                list(self.db.scalars(select(Teacher).where(Teacher.id.in_(teacher_ids))))
                if teacher_ids
                else []
            )
            offering_ids = list(
                self.db.scalars(
                    select(TeachingAssignmentSection.section_offering_id).where(
                        TeachingAssignmentSection.teaching_assignment_id == assignment.id
                    )
                )
            )
            offerings = (
                list(
                    self.db.scalars(
                        select(SectionOffering).where(SectionOffering.id.in_(offering_ids))
                    )
                )
                if offering_ids
                else []
            )
            section_labels = []
            for offering in offerings:
                section = self.db.get(Section, offering.section_id)
                grade = self.db.get(Grade, section.grade_id) if section else None
                if section and grade:
                    section_labels.append(f"{grade.name_ar} {section.name_ar}")
            subject_label = subject.name_ar if subject else str(assignment.subject_id)
            label = " — ".join([subject_label, *section_labels, *[row.name_ar for row in teachers]])
            aliases = [subject_label, subject.code if subject else "", *section_labels, *[row.name_ar for row in teachers], label]
            wrappers.append(_Entity(str(assignment.id), label, aliases))
        return self._resolve("assignment", mention, wrappers, lambda row: row.label, lambda row: row.aliases, token_match=True)

    def last_period_number(self) -> int | None:
        rows = list(
            self.db.execute(
                select(PeriodTemplate.school_id, PeriodTemplate.period_number).where(
                    PeriodTemplate.tenant_id == self.tenant_id,
                    PeriodTemplate.school_id.in_(self.school_ids),
                    PeriodTemplate.schedulable.is_(True),
                    PeriodTemplate.period_number.is_not(None),
                )
            )
        )
        maxima = {
            max(int(number) for row_school, number in rows if row_school == school_id)
            for school_id in self.school_ids
            if any(row_school == school_id for row_school, _ in rows)
        }
        return next(iter(maxima)) if len(maxima) == 1 else None

    def _resolve(
        self,
        kind: str,
        mention: str,
        rows: list[Any],
        label: Any,
        aliases: Any,
        *,
        token_match: bool = False,
    ) -> Resolution:
        normalized = normalize_arabic(mention)
        key = f"{kind}:{normalized}"
        matches = []
        mention_forms = {normalized, normalized[2:] if normalized.startswith("ال") else normalized}
        for row in rows:
            normalized_aliases = [normalize_arabic(str(value)) for value in aliases(row) if value]
            alias_forms = {
                form
                for value in normalized_aliases
                for form in (value, value[2:] if value.startswith("ال") else value)
            }
            exact = bool(mention_forms & alias_forms)
            tokens = set(normalized.split())
            contains = token_match and tokens and any(tokens.issubset(set(value.split())) for value in normalized_aliases)
            if exact or contains:
                matches.append(row)
        selected = self.resolutions.get(key)
        if selected:
            chosen = next((row for row in matches if str(row.id) == selected), None)
            if chosen is None:
                return Resolution("invalid_resolution", key=key)
            return Resolution("resolved", str(chosen.id), str(label(chosen)), key=key)
        if len(matches) == 1:
            row = matches[0]
            return Resolution("resolved", str(row.id), str(label(row)), key=key)
        if not matches:
            return Resolution("unresolved", key=key)
        choices = [
            {
                "id": str(row.id),
                "label": str(label(row)),
                "context": self._entity_school_context(row),
            }
            for row in matches
        ]
        return Resolution("ambiguous", choices=choices, key=key)

    def _entity_school_context(self, row: Any) -> str | None:
        school_id = getattr(row, "school_id", None)
        return self.school_names.get(str(school_id)) if school_id else None


@dataclass
class _Entity:
    id: str
    label: str
    aliases: list[str]


class NaturalLanguageRuleParser(Protocol):
    provider_type: str

    def parse(self, source_text: str, resolver: ProjectEntityResolver) -> dict[str, Any]: ...


class DeterministicArabicRuleParser:
    provider_type = "deterministic_ar_v1"

    def parse(self, source_text: str, resolver: ProjectEntityResolver) -> dict[str, Any]:
        normalized = normalize_arabic(source_text)
        proposals: list[dict[str, Any]] = []
        clarifications: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []

        if self._teacher_unavailable(normalized, resolver, proposals, clarifications, warnings):
            return self._result(proposals, clarifications, warnings)
        if self._subject_preference(normalized, resolver, proposals, clarifications, warnings):
            return self._result(proposals, clarifications, warnings)
        if self._teacher_daily_max(normalized, resolver, proposals, clarifications, warnings):
            return self._result(proposals, clarifications, warnings)
        if self._minimum_days(normalized, resolver, proposals, clarifications, warnings):
            return self._result(proposals, clarifications, warnings)
        if self._consecutive(normalized, resolver, proposals, clarifications, warnings):
            return self._result(proposals, clarifications, warnings)
        if self._before(normalized, resolver, proposals, clarifications, warnings):
            return self._result(proposals, clarifications, warnings)
        return {"status": "unsupported", "proposals": [], "clarifications": [], "warnings": [{"code": "unsupported_rule_request", "message": "هذا الطلب غير مدعوم في سجل القواعد الحالي، ولم يُستبدل بقاعدة تقريبية."}]}

    def _teacher_unavailable(self, text: str, resolver: ProjectEntityResolver, proposals: list[dict[str, Any]], clarifications: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> bool:
        if not any(phrase in text for phrase in ("لا تضع", "ممنوع")):
            return False
        match = re.search(r"(?:للاستاذ|للمعلم|لمعلم|للمدرس|الاستاذ|المعلم|مدرس)\s+(.+?)\s+(?=الحصة|يوم|الاحد|الاثنين|الثلاثاء|الاربعاء|الخميس|الجمعة|السبت)", text)
        if not match:
            match = re.search(r"لا تضع\s+(.+?)\s+(?=يوم|الاحد|الاثنين|الثلاثاء|الاربعاء|الخميس|الجمعة|السبت)", text)
        if not match:
            return False
        teacher = self._resolve_or_explain(resolver.teacher(match.group(1)), "teacher", match.group(1), clarifications, warnings)
        periods = self._periods(text, resolver)
        days = [index for label, index in DAY_INDEX.items() if re.search(rf"\b{label}\b", text)]
        if teacher is None or not periods or not days:
            if teacher is not None and (not periods or not days):
                warnings.append({"code": "incomplete_time_reference", "message": "حدد اليوم ورقم الحصة بوضوح."})
            return True
        # A single sentence may explicitly list several day/period pairs. When
        # counts align, preserve them as independently selectable proposals.
        pairs = list(zip(days, periods, strict=True)) if len(days) == len(periods) else [(day, periods[0]) for day in days]
        for day, period in pairs:
            day_label = next(label for label, value in DAY_INDEX.items() if value == day)
            proposals.append(self._proposal("teacher_unavailable", "hard", {"teacher_id": teacher.entity_id}, {"weekday_index": day, "period_numbers": [period]}, {"teacher": teacher.label, "day": day_label, "period": period}, f"لا توضع حصص {teacher.label} في الحصة {period} يوم {day_label}.", ["hard:no-placement", "teacher-reference", "day-and-period"]))
        return True

    def _subject_preference(self, text: str, resolver: ProjectEntityResolver, proposals: list[dict[str, Any]], clarifications: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> bool:
        match = re.search(r"(?:يفضل|حاول|قدر الامكان)\s+(?:ان\s+)?(?:تكون\s+)?(.+?)\s+في\s+اول\s+(.+?)\s+حص", text)
        if not match:
            return False
        subject = self._resolve_or_explain(resolver.subject(match.group(1)), "subject", match.group(1), clarifications, warnings)
        count = self._number(match.group(2))
        if subject is not None and count is not None:
            proposals.append(self._proposal("subject_preferred_time", "soft", {"subject_id": subject.entity_id}, {"period_numbers": list(range(1, count + 1))}, {"subject": subject.label, "periods": list(range(1, count + 1))}, f"يفضل وضع {subject.label} في أول {count} حصص.", ["soft-wording", "subject-reference", "period-range"], weight=50))
        elif count is None:
            warnings.append({"code": "invalid_period_count", "message": "تعذر فهم عدد الحصص الأولى."})
        return True

    def _teacher_daily_max(self, text: str, resolver: ProjectEntityResolver, proposals: list[dict[str, Any]], clarifications: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> bool:
        match = re.search(r"(?:لا تجعل|بحد اقصي|حد اقصي).+?(?:للاستاذ|للمعلم|الاستاذ|المعلم|مدرس)\s+(.+?)\s+اكثر من\s+([\w]+)\s+حص", text)
        if not match:
            return False
        teacher = self._resolve_or_explain(resolver.teacher(match.group(1)), "teacher", match.group(1), clarifications, warnings)
        maximum = self._number(match.group(2))
        severity = "soft" if self._is_soft(text) else "hard"
        if teacher is not None and maximum is not None:
            proposals.append(self._proposal("teacher_max_lessons_per_day", severity, {"teacher_id": teacher.entity_id}, {"maximum": maximum}, {"teacher": teacher.label, "maximum": maximum}, f"بحد أقصى {maximum} حصص لـ{teacher.label} في اليوم.", [f"severity:{severity}", "teacher-reference", "daily-maximum"], weight=50 if severity == "soft" else None))
        return True

    def _minimum_days(self, text: str, resolver: ProjectEntityResolver, proposals: list[dict[str, Any]], clarifications: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> bool:
        match = re.search(r"وزع\s+(.+?)\s+علي\s+([\w]+)\s+ايام?\s+علي الاقل", text)
        if not match:
            return False
        assignment = self._resolve_or_explain(resolver.assignment(match.group(1)), "assignment", match.group(1), clarifications, warnings)
        minimum = self._number(match.group(2))
        severity = "soft" if self._is_soft(text) else "hard"
        if assignment is not None and minimum is not None:
            proposals.append(self._proposal("assignment_min_days", severity, {"assignment_id": assignment.entity_id}, {"minimum_days": minimum}, {"assignment": assignment.label, "minimum_days": minimum}, f"يوزع {assignment.label} على {minimum} أيام على الأقل.", [f"severity:{severity}", "assignment-reference", "minimum-days"], weight=50 if severity == "soft" else None))
        return True

    def _consecutive(self, text: str, resolver: ProjectEntityResolver, proposals: list[dict[str, Any]], clarifications: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> bool:
        match = re.search(r"(?:اجعل|ضع)\s+حصت(?:ي|ين)\s+(.+?)\s+متتاليت", text)
        if not match:
            return False
        assignment = self._resolve_or_explain(resolver.assignment(match.group(1)), "assignment", match.group(1), clarifications, warnings)
        if assignment is not None:
            proposals.append(self._proposal("assignment_require_consecutive_block", "hard", {"assignment_id": assignment.entity_id}, {"block_size": 2}, {"assignment": assignment.label, "block_size": 2}, f"تكون حصتا {assignment.label} متتاليتين.", ["hard:consecutive", "assignment-reference", "block-size:2"]))
        return True

    def _before(self, text: str, resolver: ProjectEntityResolver, proposals: list[dict[str, Any]], clarifications: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> bool:
        match = re.search(r"اجعل\s+اسناد\s+(.+?)\s+قبل\s+اسناد\s+(.+)$", text)
        if not match:
            return False
        left = self._resolve_or_explain(resolver.assignment(match.group(1)), "assignment", match.group(1), clarifications, warnings)
        right = self._resolve_or_explain(resolver.assignment(match.group(2)), "assignment", match.group(2), clarifications, warnings)
        severity = "soft" if self._is_soft(text) else "hard"
        if left is not None and right is not None:
            proposals.append(self._proposal("assignment_before_assignment", severity, {"assignment_ids": [left.entity_id, right.entity_id]}, {}, {"before": left.label, "after": right.label}, f"يكون إسناد {left.label} قبل إسناد {right.label}.", [f"severity:{severity}", "two-assignment-references", "ordering"], weight=50 if severity == "soft" else None))
        return True

    def _resolve_or_explain(self, result: Resolution, kind: str, mention: str, clarifications: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> Resolution | None:
        if result.status == "resolved":
            return result
        if result.status == "ambiguous":
            clarifications.append({"key": result.key, "reference_type": kind, "mention": mention, "question": f"أي {self._kind_label(kind)} تقصد بعبارة «{mention}»؟", "choices": result.choices or []})
        elif result.status == "invalid_resolution":
            warnings.append({"code": "invalid_clarification_choice", "reference_type": kind, "mention": mention})
        else:
            warnings.append({"code": "unresolved_reference", "reference_type": kind, "mention": mention, "message": f"لم يُعثر على {self._kind_label(kind)} مطابق داخل نطاق المشروع."})
        return None

    @staticmethod
    def _kind_label(kind: str) -> str:
        return {"teacher": "معلم", "subject": "مادة", "section": "شعبة", "assignment": "إسناد", "resource": "مورد"}.get(kind, kind)

    @staticmethod
    def _is_soft(text: str) -> bool:
        return any(value in text for value in ("يفضل", "حاول", "قدر الامكان"))

    @staticmethod
    def _number(value: str) -> int | None:
        normalized = normalize_arabic(value)
        if normalized.isdigit():
            return int(normalized)
        return NUMBER_WORDS.get(normalized)

    def _periods(self, text: str, resolver: ProjectEntityResolver) -> list[int]:
        values: list[tuple[int, int]] = []
        for word, value in ORDINALS.items():
            values.extend((match.start(), value) for match in re.finditer(rf"\b{word}\b", text))
        values.extend((match.start(), int(match.group(1))) for match in re.finditer(r"(?:الحصة|رقم)\s*(\d+)", text))
        last = resolver.last_period_number()
        if last is not None:
            values.extend((match.start(), last) for match in re.finditer(r"\bالاخيرة\b", text))
        return [value for _, value in sorted(values)]

    @staticmethod
    def _proposal(rule_type: str, severity: str, selector: dict[str, Any], parameters: dict[str, Any], labels: dict[str, Any], summary: str, evidence: list[str], weight: int | None = None) -> dict[str, Any]:
        return {"id": str(uuid.uuid4()), "rule_type": rule_type, "severity": severity, "weight": weight, "selector": selector, "parameters": parameters, "resolved_labels": labels, "arabic_summary": summary, "evidence": evidence}

    @staticmethod
    def _result(proposals: list[dict[str, Any]], clarifications: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> dict[str, Any]:
        status = "needs_clarification" if clarifications else "invalid" if warnings and not proposals else "ready"
        return {"status": status, "proposals": proposals, "clarifications": clarifications, "warnings": warnings}
