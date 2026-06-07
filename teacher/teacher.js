const storage = new window.SmartStorage('teacher');
const notifier = new window.NotificationManager();
const engine = new window.ScheduleEngine();

const DAYS = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس'];
const SECTION_LETTERS = ['أ', 'ب', 'ج', 'د', 'هـ', 'و', 'ز', 'ح', 'ط', 'ي', 'ك', 'ل'];
const SECTION_PATTERNS = {
    slash: '1/1 - 1/2 - 1/3',
    spacedSlash: '1 / 1 - 1 / 2 - 1 / 3',
    dash: '1-1 - 1-2 - 1-3',
    gradeNumber: 'أول 1 - أول 2 - أول 3',
    gradeLetter: 'أول أ - أول ب - أول ج',
    numberLetter: '1 أ - 1 ب - 1 ج',
    custom: 'أسماء مخصصة'
};

const STAGES = {
    early: {
        label: 'الطفولة المبكرة',
        grades: ['الأول', 'الثاني', 'الثالث'],
        subjects: ['القرآن الكريم', 'لغتي', 'رياضيات', 'علوم', 'إنجليزي', 'مهارات حياتية', 'بدنية', 'فنية', 'نشاط']
    },
    elementary: {
        label: 'الابتدائية',
        grades: ['الأول', 'الثاني', 'الثالث', 'الرابع', 'الخامس', 'السادس'],
        subjects: ['القرآن الكريم', 'توحيد', 'فقه', 'لغتي', 'رياضيات', 'علوم', 'دراسات اجتماعية', 'إنجليزي', 'مهارات رقمية', 'بدنية', 'فنية']
    },
    intermediate: {
        label: 'المتوسطة',
        grades: ['الأول متوسط', 'الثاني متوسط', 'الثالث متوسط'],
        subjects: ['قرآن', 'تفسير', 'توحيد', 'حديث', 'فقه', 'لغتي الخالدة', 'رياضيات', 'علوم', 'دراسات اجتماعية', 'إنجليزي', 'مهارات رقمية', 'تفكير ناقد', 'بدنية', 'فنية']
    },
    secondary: {
        label: 'الثانوية',
        grades: ['الأول ثانوي', 'الثاني ثانوي', 'الثالث ثانوي'],
        subjects: ['كفايات', 'رياضيات', 'فيزياء', 'كيمياء', 'أحياء', 'علم البيئة', 'إنجليزي', 'تقنية رقمية', 'دراسات اجتماعية', 'مهارات حياتية', 'بدنية', 'فنون']
    }
};

const TIMING_PRESETS = {
    summer: { label: 'صيفي', start: '07:00', period: 45, breakAfter: 3, breakMinutes: 20, count: 7 },
    winter: { label: 'شتوي', start: '07:30', period: 45, breakAfter: 3, breakMinutes: 20, count: 7 },
    ramadan: { label: 'رمضاني', start: '09:00', period: 35, breakAfter: 3, breakMinutes: 10, count: 6 },
    custom: { label: 'مخصص', start: '07:00', period: 45, breakAfter: 3, breakMinutes: 20, count: 7 }
};

const defaultState = {
    stage: 'elementary',
    grade: 'الرابع',
    teacherName: '',
    room: '',
    sectionPattern: 'gradeLetter',
    sectionCount: 3,
    sectionCustom: '',
    timingMode: 'summer',
    timing: { ...TIMING_PRESETS.summer },
    schedule: [],
    settings: { soundEnabled: true },
    currentTab: 'grid'
};

let state = normalizeState(storage.get('state', null));

function normalizeState(saved) {
    const merged = { ...defaultState, ...(saved || {}) };
    merged.settings = { ...defaultState.settings, ...(merged.settings || {}) };
    merged.timing = { ...TIMING_PRESETS[merged.timingMode || 'summer'], ...(merged.timing || {}) };
    if (!STAGES[merged.stage]) merged.stage = 'elementary';
    if (!STAGES[merged.stage].grades.includes(merged.grade)) merged.grade = STAGES[merged.stage].grades[0];
    merged.sectionPattern = SECTION_PATTERNS[merged.sectionPattern] ? merged.sectionPattern : 'gradeLetter';
    merged.sectionCount = Math.min(Math.max(Number(merged.sectionCount || 3), 1), 12);
    merged.sectionCustom = merged.sectionCustom || '';
    merged.schedule = Array.isArray(merged.schedule) ? merged.schedule : [];
    return merged;
}

const byId = (id) => document.getElementById(id);

function saveState() {
    storage.set('state', state);
}

function stage() {
    return STAGES[state.stage] || STAGES.elementary;
}

function gradeMeta(grade = state.grade) {
    const numbers = {
        'الأول': '1', 'الثاني': '2', 'الثالث': '3', 'الرابع': '4', 'الخامس': '5', 'السادس': '6',
        'الأول متوسط': '1', 'الثاني متوسط': '2', 'الثالث متوسط': '3',
        'الأول ثانوي': '1', 'الثاني ثانوي': '2', 'الثالث ثانوي': '3'
    };
    const shortNames = {
        'الأول': 'أول', 'الثاني': 'ثاني', 'الثالث': 'ثالث', 'الرابع': 'رابع', 'الخامس': 'خامس', 'السادس': 'سادس',
        'الأول متوسط': 'أول متوسط', 'الثاني متوسط': 'ثاني متوسط', 'الثالث متوسط': 'ثالث متوسط',
        'الأول ثانوي': 'أول ثانوي', 'الثاني ثانوي': 'ثاني ثانوي', 'الثالث ثانوي': 'ثالث ثانوي'
    };
    return {
        number: numbers[grade] || String(Math.max(1, stage().grades.indexOf(grade) + 1)),
        shortName: shortNames[grade] || grade
    };
}

function buildSections() {
    const custom = String(state.sectionCustom || '')
        .split(/\r?\n|،|,/)
        .map(item => item.trim())
        .filter(Boolean);
    if (state.sectionPattern === 'custom' && custom.length) return custom;

    const count = Math.min(Math.max(Number(state.sectionCount || 3), 1), 12);
    const meta = gradeMeta();
    return Array.from({ length: count }, (_, index) => {
        const number = String(index + 1);
        const letter = SECTION_LETTERS[index] || number;
        if (state.sectionPattern === 'slash') return `${meta.number}/${number}`;
        if (state.sectionPattern === 'spacedSlash') return `${meta.number} / ${number}`;
        if (state.sectionPattern === 'dash') return `${meta.number}-${number}`;
        if (state.sectionPattern === 'gradeNumber') return `${meta.shortName} ${number}`;
        if (state.sectionPattern === 'numberLetter') return `${meta.number} ${letter}`;
        return `${meta.shortName} ${letter}`;
    });
}

function getTimingSlots() {
    const slots = [];
    let cursor = window.timeToMinutes(state.timing.start);
    for (let i = 1; i <= Number(state.timing.count || 7); i++) {
        const start = window.minutesToTime(cursor);
        const end = window.minutesToTime(cursor + Number(state.timing.period || 45));
        slots.push({ number: i, label: `الحصة ${i}`, start, end });
        cursor += Number(state.timing.period || 45);
        if (i === Number(state.timing.breakAfter || 0)) cursor += Number(state.timing.breakMinutes || 0);
    }
    return slots;
}

function fillSelect(id, items, selected) {
    const el = byId(id);
    if (!el) return;
    el.innerHTML = items.map(item => {
        const value = typeof item === 'string' ? item : item.value;
        const label = typeof item === 'string' ? item : item.label;
        return `<option value="${value}" ${value === selected ? 'selected' : ''}>${label}</option>`;
    }).join('');
}

function initControls() {
    fillSelect('stage-select', Object.entries(STAGES).map(([value, item]) => ({ value, label: item.label })), state.stage);
    fillSelect('grade-select', stage().grades, state.grade);
    fillSelect('subject-select', stage().subjects, stage().subjects[0]);
    fillSelect('period-select', getTimingSlots().map(s => ({ value: String(s.number), label: `${s.label} (${s.start} - ${s.end})` })), '1');
    fillSelect('timing-mode', Object.entries(TIMING_PRESETS).map(([value, item]) => ({ value, label: item.label })), state.timingMode);
    fillSelect('section-pattern', Object.entries(SECTION_PATTERNS).map(([value, label]) => ({ value, label })), state.sectionPattern);
    fillSelect('section-select', buildSections(), buildSections()[0]);

    byId('teacher-name').value = state.teacherName || '';
    byId('teacher-room').value = state.room || '';
    byId('section-count').value = state.sectionCount;
    byId('section-custom').value = state.sectionCustom;
    byId('timing-start').value = state.timing.start;
    byId('period-minutes').value = state.timing.period;
    byId('period-count').value = state.timing.count;
    byId('break-after').value = state.timing.breakAfter;
    byId('break-minutes').value = state.timing.breakMinutes;
    byId('sound-enabled').checked = !!state.settings.soundEnabled;
}

function bindControls() {
    byId('stage-select').addEventListener('change', (event) => {
        state.stage = event.target.value;
        state.grade = stage().grades[0];
        saveState();
        initControls();
        renderAll();
    });

    byId('grade-select').addEventListener('change', (event) => {
        state.grade = event.target.value;
        saveState();
        initControls();
        renderAll();
    });

    byId('section-pattern').addEventListener('change', (event) => {
        state.sectionPattern = event.target.value;
        saveState();
        initControls();
        renderAll();
    });

    byId('section-count').addEventListener('input', (event) => {
        state.sectionCount = Math.min(Math.max(Number(event.target.value || 1), 1), 12);
        saveState();
        fillSelect('section-select', buildSections(), buildSections()[0]);
        renderAll();
    });

    byId('section-custom').addEventListener('input', (event) => {
        state.sectionCustom = event.target.value;
        saveState();
        if (state.sectionPattern === 'custom') {
            fillSelect('section-select', buildSections(), buildSections()[0]);
            renderAll();
        }
    });

    byId('timing-mode').addEventListener('change', (event) => {
        state.timingMode = event.target.value;
        state.timing = { ...TIMING_PRESETS[state.timingMode] };
        saveState();
        initControls();
        renderAll();
    });

    ['teacher-name', 'teacher-room'].forEach(id => {
        byId(id).addEventListener('input', (event) => {
            if (id === 'teacher-name') state.teacherName = event.target.value;
            if (id === 'teacher-room') state.room = event.target.value;
            saveState();
            renderHeader();
        });
    });

    ['timing-start', 'period-minutes', 'period-count', 'break-after', 'break-minutes'].forEach(id => {
        byId(id).addEventListener('input', () => {
            state.timingMode = 'custom';
            state.timing = {
                label: 'مخصص',
                start: byId('timing-start').value || '07:00',
                period: Number(byId('period-minutes').value || 45),
                count: Number(byId('period-count').value || 7),
                breakAfter: Number(byId('break-after').value || 0),
                breakMinutes: Number(byId('break-minutes').value || 0)
            };
            saveState();
            initControls();
            renderAll();
        });
    });

    byId('sound-enabled').addEventListener('change', (event) => {
        state.settings.soundEnabled = event.target.checked;
        saveState();
    });

    byId('import-file').addEventListener('change', handleImport);
}

window.switchTab = (tab) => {
    state.currentTab = tab;
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(view => view.classList.remove('active'));
    byId(`btn-${tab}`).classList.add('active');
    byId(`view-${tab}`).classList.add('active');
    saveState();
    renderAll();
};

function renderHeader() {
    byId('header-stage').textContent = `${stage().label} - ${state.grade}`;
    byId('header-teacher').textContent = state.teacherName ? `المعلم: ${state.teacherName}` : 'أضف اسم المعلم من لوحة التحكم';
    byId('summary-stage').textContent = stage().label;
    byId('summary-grade').textContent = state.grade;
    byId('summary-lessons').textContent = window.toArabicDigits(state.schedule.length);
    byId('summary-timing').textContent = TIMING_PRESETS[state.timingMode]?.label || 'مخصص';
}

function renderTimingPreview() {
    const container = byId('timing-preview');
    container.innerHTML = getTimingSlots().map(slot => `
        <div class="period-chip">
            <strong>${slot.label}</strong>
            <span>${window.toArabicDigits(slot.start)} - ${window.toArabicDigits(slot.end)}</span>
        </div>
    `).join('');
}

function renderGrid() {
    const container = byId('weekly-grid-container');
    const slots = getTimingSlots();
    let html = '<table class="schedule-table"><thead><tr><th>اليوم</th>';
    slots.forEach(slot => html += `<th>${slot.label}<small>${window.toArabicDigits(slot.start)} - ${window.toArabicDigits(slot.end)}</small></th>`);
    html += '</tr></thead><tbody>';
    DAYS.forEach(day => {
        html += `<tr><th>${day}</th>`;
        slots.forEach(slot => {
            const lesson = state.schedule.find(item => item.day === day && Number(item.period) === slot.number);
            html += `<td>${lesson ? lessonCard(lesson) : `<button class="empty-slot" onclick="quickPrepare('${day}', ${slot.number})">إضافة</button>`}</td>`;
        });
        html += '</tr>';
    });
    html += '</tbody></table>';
    container.innerHTML = html;
    if (window.lucide) window.lucide.createIcons();
}

function lessonCard(lesson) {
    return `
        <div class="lesson-card">
            <strong>${lesson.subject}</strong>
            <span>${lesson.grade || state.grade}</span>
            <small>${window.toArabicDigits(lesson.start)} - ${window.toArabicDigits(lesson.end)}</small>
            <button onclick="deleteSession('${lesson.id}')" title="حذف"><i data-lucide="x"></i></button>
        </div>
    `;
}

function renderTimeline() {
    const today = DAYS[new Date().getDay()] || DAYS[0];
    const items = state.schedule
        .filter(item => item.day === today)
        .sort((a, b) => window.timeToMinutes(a.start) - window.timeToMinutes(b.start));

    const container = byId('timeline-container');
    if (!items.length) {
        container.innerHTML = '<div class="empty-state">لا توجد حصص مسجلة لهذا اليوم.</div>';
        return;
    }

    const now = window.getCurrentTimeMinutes();
    container.innerHTML = items.map(item => {
        const active = now >= window.timeToMinutes(item.start) && now < window.timeToMinutes(item.end);
        return `
            <div class="timeline-item ${active ? 'active' : ''}">
                <div class="timeline-time">${window.toArabicDigits(item.start)}</div>
                <div>
                    <strong>${item.subject}</strong>
                    <span>${item.grade || state.grade} ${item.room ? `- ${item.room}` : ''}</span>
                </div>
                <small>${window.toArabicDigits(item.end)}</small>
            </div>
        `;
    }).join('');
}

function renderSubjects() {
    byId('subject-list').innerHTML = stage().subjects.map(subject => `<span>${subject}</span>`).join('');
    const sectionList = byId('section-list');
    if (sectionList) sectionList.innerHTML = buildSections().map(item => `<span>${item}</span>`).join('');
}

function updateTimer() {
    const today = DAYS[new Date().getDay()] || DAYS[0];
    engine.setSchedule(state.schedule.filter(item => item.day === today));
    const status = engine.getStatus();
    byId('live-clock').textContent = new Date().toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' });

    if (status.current) {
        byId('current-task').textContent = status.current.subject;
        byId('next-task').textContent = status.next ? `القادم: ${status.next.subject}` : 'هذه آخر حصة اليوم';
        byId('countdown').textContent = window.formatDuration(status.remainingSeconds);
        const total = (window.timeToMinutes(status.current.end) - window.timeToMinutes(status.current.start)) * 60;
        byId('timer-progress').style.strokeDashoffset = Math.max(0, (status.remainingSeconds / total) * 377);
    } else if (status.next) {
        byId('current-task').textContent = 'انتظار الحصة';
        byId('next-task').textContent = `القادم: ${status.next.subject}`;
        byId('countdown').textContent = window.formatDuration(status.remainingSeconds);
        byId('timer-progress').style.strokeDashoffset = 377;
    } else {
        byId('current-task').textContent = 'خارج وقت الحصص';
        byId('next-task').textContent = 'لا توجد حصة قادمة اليوم';
        byId('countdown').textContent = '00:00';
        byId('timer-progress').style.strokeDashoffset = 377;
    }
}

window.quickPrepare = (day, period) => {
    window.switchTab('manage');
    byId('day-select').value = day;
    byId('period-select').value = String(period);
};

window.addSession = () => {
    const period = Number(byId('period-select').value);
    const slot = getTimingSlots().find(item => item.number === period);
    const customStart = byId('custom-start').value;
    const customEnd = byId('custom-end').value;
    const item = {
        id: Date.now().toString(),
        subject: byId('subject-select').value,
        grade: byId('section-select').value || byId('grade-select').value,
        day: byId('day-select').value,
        period,
        start: customStart || slot.start,
        end: customEnd || slot.end,
        room: byId('teacher-room').value || ''
    };

    if (!item.subject || !item.start || !item.end) {
        alert('أكمل المادة والتوقيت.');
        return;
    }

    state.schedule = state.schedule.filter(old => !(old.day === item.day && Number(old.period) === item.period));
    state.schedule.push(item);
    state.schedule.sort((a, b) => DAYS.indexOf(a.day) - DAYS.indexOf(b.day) || Number(a.period) - Number(b.period));
    saveState();
    byId('custom-start').value = '';
    byId('custom-end').value = '';
    renderAll();
};

window.generateWeek = () => {
    const subjects = stage().subjects;
    const slots = getTimingSlots();
    const sections = buildSections();
    const generated = [];
    DAYS.forEach((day, dayIndex) => {
        slots.forEach((slot, slotIndex) => {
            generated.push({
                id: `${Date.now()}-${dayIndex}-${slotIndex}`,
                subject: subjects[(dayIndex + slotIndex) % subjects.length],
                grade: sections[(dayIndex + slotIndex) % sections.length] || state.grade,
                day,
                period: slot.number,
                start: slot.start,
                end: slot.end,
                room: state.room || ''
            });
        });
    });
    state.schedule = generated;
    saveState();
    renderAll();
};

window.deleteSession = (id) => {
    state.schedule = state.schedule.filter(item => item.id !== id);
    saveState();
    renderAll();
};

window.clearSchedule = () => {
    if (!confirm('هل تريد تفريغ جدول المعلم فقط؟')) return;
    state.schedule = [];
    saveState();
    renderAll();
};

window.exportData = () => {
    const blob = new Blob([JSON.stringify(state, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `teacher_schedule_${new Date().toISOString().slice(0, 10)}.json`;
    link.click();
    URL.revokeObjectURL(url);
};

function handleImport(event) {
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
        try {
            state = normalizeState(JSON.parse(reader.result));
            saveState();
            initControls();
            renderAll();
            alert('تم استيراد البيانات بنجاح.');
        } catch {
            alert('تعذر قراءة ملف البيانات.');
        }
    };
    reader.readAsText(file);
}

window.clearData = () => {
    if (!confirm('هل تريد مسح جميع بيانات بوابة المعلم؟')) return;
    storage.clear();
    state = normalizeState(null);
    saveState();
    initControls();
    renderAll();
};

window.shareWhatsApp = () => {
    const lines = [`جدول ${state.teacherName || 'المعلم'} - ${stage().label}`, ''];
    DAYS.forEach(day => {
        const lessons = state.schedule.filter(item => item.day === day).sort((a, b) => Number(a.period) - Number(b.period));
        if (lessons.length) {
            lines.push(day);
            lessons.forEach(item => lines.push(`${item.period}. ${item.subject} - ${item.grade} (${item.start}-${item.end})`));
        }
    });
    window.open(`https://wa.me/?text=${encodeURIComponent(lines.join('\n'))}`, '_blank');
};

function renderAll() {
    renderHeader();
    renderTimingPreview();
    renderGrid();
    renderTimeline();
    renderSubjects();
    fillSelect('period-select', getTimingSlots().map(s => ({ value: String(s.number), label: `${s.label} (${s.start} - ${s.end})` })), byId('period-select')?.value || '1');
    fillSelect('subject-select', stage().subjects, byId('subject-select')?.value || stage().subjects[0]);
    fillSelect('section-select', buildSections(), byId('section-select')?.value || buildSections()[0]);
    if (window.lucide) window.lucide.createIcons();
}

function init() {
    initControls();
    bindControls();
    renderAll();
    setInterval(updateTimer, 1000);
    updateTimer();
    notifier.requestPermission();
}

init();
