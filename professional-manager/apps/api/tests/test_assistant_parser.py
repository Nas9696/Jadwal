from app.assistant_parser import DeterministicArabicRuleParser, Resolution


class StubResolver:
    def teacher(self, mention: str) -> Resolution:
        return Resolution("resolved", "teacher-1", mention)

    def subject(self, mention: str) -> Resolution:
        return Resolution("resolved", "subject-1", mention)

    def assignment(self, mention: str) -> Resolution:
        identifier = "assignment-2" if "النشاط" in mention else "assignment-1"
        return Resolution("resolved", identifier, mention)

    def last_period_number(self) -> int:
        return 8


def test_required_arabic_patterns_map_to_registry_rules() -> None:
    parser = DeterministicArabicRuleParser()
    resolver = StubResolver()
    cases = [
        ("يفضل أن تكون الرياضيات في أول ثلاث حصص", "subject_preferred_time", "soft"),
        ("لا تجعل للمعلم علي أكثر من ٤ حصص في اليوم", "teacher_max_lessons_per_day", "hard"),
        ("وزع رياضيات أول أ على أربعة أيام على الأقل", "assignment_min_days", "hard"),
        ("اجعل حصتي العلوم متتاليتين", "assignment_require_consecutive_block", "hard"),
        ("اجعل إسناد الرياضيات قبل إسناد النشاط", "assignment_before_assignment", "hard"),
    ]
    for source, expected_type, expected_severity in cases:
        parsed = parser.parse(source, resolver)  # type: ignore[arg-type]
        assert parsed["status"] == "ready", (source, parsed)
        assert parsed["proposals"][0]["rule_type"] == expected_type
        assert parsed["proposals"][0]["severity"] == expected_severity


def test_western_arabic_digits_soft_wording_and_multiple_explicit_rules() -> None:
    parser = DeterministicArabicRuleParser()
    resolver = StubResolver()
    western = parser.parse("حاول ألا تجعل للمعلم علي أكثر من 4 حصص في اليوم", resolver)  # type: ignore[arg-type]
    arabic = parser.parse("حاول ألا تجعل للمعلم علي أكثر من ٤ حصص في اليوم", resolver)  # type: ignore[arg-type]
    assert western["proposals"][0]["parameters"]["maximum"] == 4
    assert arabic["proposals"][0]["parameters"]["maximum"] == 4
    assert western["proposals"][0]["severity"] == "soft"
    multiple = parser.parse("لا تضع أحمد الأحد الأولى ولا الثلاثاء الأخيرة", resolver)  # type: ignore[arg-type]
    assert multiple["status"] == "ready"
    assert [item["parameters"]["period_numbers"] for item in multiple["proposals"]] == [[1], [8]]
