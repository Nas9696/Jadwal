const STORAGE_KEY = 'smartExamSchedule.v2';
const ministryLogo = 'https://upload.wikimedia.org/wikipedia/ar/8/82/Logo_of_Ministry_of_Education_%28Saudi_Arabia%29.svg';
const daysSequence = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس'];
const materialVisuals = {
    'رياضيات': { emoji: '➗', icon: 'calculator', color: '#2563eb' },
    'لغتي': { emoji: '📖', icon: 'book-open-text', color: '#dc2626' },
    'علوم': { emoji: '🔬', icon: 'microscope', color: '#059669' },
    'إسلامية': { emoji: '🕌', icon: 'landmark', color: '#047857' },
    'إنجليزي': { emoji: '🔤', icon: 'languages', color: '#7c3aed' },
    'رقمية': { emoji: '💻', icon: 'monitor', color: '#0891b2' },
    'مهارات حياتية': { emoji: '🌱', icon: 'heart-handshake', color: '#65a30d', short: 'م. حياتية' },
    'اجتماعيات': { emoji: '🌍', icon: 'globe-2', color: '#ca8a04' },
    'فنية': { emoji: '🎨', icon: 'palette', color: '#db2777' },
    'فيزياء': { emoji: '⚛️', icon: 'atom', color: '#4f46e5' },
    'كيمياء': { emoji: '🧪', icon: 'flask-conical', color: '#0d9488' },
    'أحياء': { emoji: '🧬', icon: 'dna', color: '#16a34a' },
    'كفايات': { emoji: '✍️', icon: 'pen-line', color: '#9333ea' },
    'إجازة': { emoji: '☕', icon: 'coffee', color: '#64748b' },
    'مركزي': { emoji: '🏛️', icon: 'landmark', color: '#b45309' }
};
const HOLIDAY_SUBJECT = 'إجازة';
const CENTRAL_SUBJECT = 'مركزي';
const REST_SUBJECT = 'راحة';
Object.assign(materialVisuals, {
    'رياضيات': { emoji: '🧮', icon: 'calculator', color: '#2563eb' },
    'لغتي': { emoji: '📚', icon: 'book-open-text', color: '#dc2626' },
    'علوم': { emoji: '🧪', icon: 'flask-conical', color: '#059669' },
    'إسلامية': { emoji: '🕌', icon: 'landmark', color: '#047857' },
    'إنجليزي': { emoji: '🔤', icon: 'languages', color: '#7c3aed' },
    'رقمية': { emoji: '💻', icon: 'monitor-smartphone', color: '#0891b2' },
    'تقنية رقمية': { emoji: '💻', icon: 'monitor-smartphone', color: '#0891b2' },
    'م. حياتية': { emoji: '🤝', icon: 'heart-handshake', color: '#65a30d' },
    'مهارات حياتية': { emoji: '🤝', icon: 'heart-handshake', color: '#65a30d', short: 'م. حياتية' },
    'اجتماعيات': { emoji: '🗺️', icon: 'map', color: '#ca8a04' },
    'فنية': { emoji: '🎨', icon: 'palette', color: '#db2777' },
    'بدنية': { emoji: '🏃', icon: 'dumbbell', color: '#ea580c' },
    'فيزياء': { emoji: '⚛️', icon: 'atom', color: '#4f46e5' },
    'كيمياء': { emoji: '⚗️', icon: 'flask-conical', color: '#0d9488' },
    'أحياء': { emoji: '🧬', icon: 'dna', color: '#16a34a' },
    'كفايات': { emoji: '✍️', icon: 'pen-line', color: '#9333ea' },
    'تفكير ناقد': { emoji: '🧠', icon: 'brain', color: '#7c2d12' },
    'نشاط': { emoji: '✨', icon: 'sparkles', color: '#0f766e' },
    'إجازة': { emoji: '☕', icon: 'coffee', color: '#64748b' },
    'راحة': { emoji: '🛋️', icon: 'armchair', color: '#475569' },
    'مركزي': { emoji: '🏛️', icon: 'landmark', color: '#b45309' }
});
const classTemplates = {
    elementary: {
        elementary6: ['الصف الأول', 'الصف الثاني', 'الصف الثالث', 'الصف الرابع', 'الصف الخامس', 'الصف السادس'],
        elementary3: ['الصف الرابع', 'الصف الخامس', 'الصف السادس']
    },
    intermediate: {
        intermediate3: ['الأول متوسط', 'الثاني متوسط', 'الثالث متوسط']
    },
    secondary: {
        secondaryNew: ['أول ثانوي (المشترك)', 'ثاني ثانوي (العام)', 'ثالث ثانوي (العام)'],
        secondaryLevels: ['الأول ثانوي', 'الثاني ثانوي', 'الثالث ثانوي']
    },
    early_childhood: {
        early3: ['الصف الأول', 'الصف الثاني', 'الصف الثالث']
    }
};
const classTemplateLabels = {
    elementary6: 'الابتدائية كاملة (١-٦)',
    elementary3: 'الابتدائية العليا (٤-٦)',
    intermediate3: 'المتوسطة (١-٣)',
    secondaryNew: 'ثانوي (عام ومشترك)',
    secondaryLevels: 'ثانوي (مستويات)',
    early3: 'الطفولة المبكرة (١-٣)'
};

const stageClassesText = {
    early_childhood: ['أول - ثاني - ثالث', 'أول', 'ثاني', 'ثالث'],
    elementary: ['رابع - خامس - سادس', 'رابع', 'خامس', 'سادس'],
    intermediate: ['أول - ثاني - ثالث', 'أول', 'ثاني', 'ثالث'],
    secondary: ['أول ثانوي (المشترك)']
};

const defaultState = {
    currentStage: 'early_childhood',
    classNames: ['الصف الأول', 'الصف الثاني', 'الصف الثالث'],
    materials: {
        early_childhood: ['رياضيات', 'إنجليزي', 'لغتي', 'علوم', 'إسلامية', 'م. حياتية', 'بدنية', 'فنية', 'نشاط'],
        elementary: ['رياضيات', 'إنجليزي', 'لغتي', 'علوم', 'إسلامية', 'اجتماعيات', 'رقمية', 'م. حياتية', 'بدنية', 'فنية'],
        intermediate: ['رياضيات', 'إنجليزي', 'لغتي', 'علوم', 'إسلامية', 'اجتماعيات', 'رقمية', 'تفكير ناقد', 'م. حياتية', 'بدنية', 'فنية'],
        secondary: ['رياضيات', 'إنجليزي', 'فيزياء', 'كيمياء', 'أحياء', 'علم الأرض', 'كفايات', 'علم البيئة', 'تقنية رقمية', 'اجتماعيات', 'معرفة مالية', 'بدنية', 'تربية مهنية', 'نشاط', 'لياقة وثقافة', 'فنون', 'م. حياتية', 'مواطنة رقمية', 'دراسات أدبية', 'إسلامية', 'علم نفس', 'جغرافيا']
    },
    materialColors: { early_childhood: {}, elementary: {}, intermediate: {}, secondary: {} },
    classColors: ['#ecfdf5', '#eff6ff', '#fff7ed', '#fdf2f8', '#f5f3ff', '#f0fdf4'],
    rowColors: [],
    tableRows: [],
    tableRows2: [],
    instructions: [
        'جميع الاختبارات اثناء اليوم الدراسي.',
        'على كل طالب احضار ادواته.',
        'يمنع إحضار الجوال أو الساعات الذكية بكافة أنواعها.'
    ],
    fields: {
        h_r1: 'المملكة العربية السعودية',
        h_r2: 'وزارة التعليم',
        h_r3: 'الإدارة العامة للتعليم بمنطقة نجران',
        h_l1: 'اختبارات الفترة الثانية',
        h_l2: 'الفصل الدراسي الثاني',
        h_l3: 'العام الدراسي 1447 هـ',
        school_name_input: 'مدرسة محمد بن القاسم',
        main_title_input: 'جدول اختبارات الفترة الثانية لمرحلة الطفولة المبكرة',
        principal_input: 'أ. ناصر مسعود آل مستنير',
        logo_url_input: ministryLogo,
        logo_data_url: '',
        days_count: '5',
        start_day: '23',
        start_month: '11',
        start_day_name: 'الأحد',
        header_right_align: 'right',
        header_left_align: 'left',
        header_right_size: '11',
        header_left_size: '11',
        main_title_size: '20',
        principal_size: '14',
        class_template: 'early3',
        print_orientation: 'landscape',
        use_class_colors: 'true',
        use_row_colors: 'false',
        use_material_colors: 'true',
        use_arabic_numerals: 'true',
        table_mode: 'ministerial',
        table_theme: 'purple',
        week_number: 'الأسبوع الرابع عشر',
        show_week_box: 'true',
        font_family: 'Cairo',
        week2_enabled: 'false',
        merge_weeks: 'false',
        week2_number: 'الأسبوع الخامس عشر',
        week2_days_count: '5',
        week2_start_day: '30',
        week2_start_month: '11',
        gender_mode: 'male',
        principal_label_input: 'مدير المدرسة'
    }
};

let state = deepClone(defaultState);
let saveTimer = null;
let previewFitTimer = null;

function deepClone(value) {
    return JSON.parse(JSON.stringify(value));
}

function byId(id) {
    return document.getElementById(id);
}

function setText(id, value) {
    const el = byId(id);
    if (!el) return;
    const text = isEnabled('use_arabic_numerals') ? toArabicDigits(value) : value || '';
    el.innerHTML = text; // Use innerHTML to ensure consistent rendering
}

function toArabicDigits(str) {
    if (str === null || str === undefined) return '';
    str = String(str);
    const arabic = ['٠', '١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩'];
    const res = str.replace(/[0-9]/g, w => arabic[+w]);
    return res;
}

function updateDashboardNumerals() {
    if (!isEnabled('use_arabic_numerals')) return;
    document.querySelectorAll('.compact-label, .section-title, .control-title').forEach(el => {
        el.textContent = toArabicDigits(el.textContent);
    });
}

function showToast(message) {
    const toast = byId('toast');
    toast.textContent = message;
    toast.classList.add('show');
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => toast.classList.remove('show'), 1800);
}

function clampNumber(value, min, max, fallback) {
    const n = parseArabicNum(value);
    if (Number.isNaN(n) || n === 0 && value !== '0' && value !== 0) return fallback;
    return Math.min(Math.max(n, min), max);
}

function normalizeSubjectList(value, keepEmpty = false) {
    if (Array.isArray(value)) return keepEmpty ? value : value.filter(Boolean);
    return value ? [value] : [];
}

function formatSubjectList(value) {
    const subjects = normalizeSubjectList(value);
    return subjects.length ? subjects.join(' + ') : '-';
}

function isEnabled(field) {
    return state.fields[field] === 'true';
}

function defaultColor(index) {
    const colors = ['#ecfdf5', '#eff6ff', '#fff7ed', '#fdf2f8', '#f5f3ff', '#f0fdfa', '#fefce8', '#f1f5f9'];
    return colors[index % colors.length];
}

function getMaterialVisual(subject) {
    return materialVisuals[subject] || { emoji: '📌', icon: 'sparkles', color: '#475569' };
}

function isCentralSubject(subject) {
    return String(subject || '').includes('مركزي');
}

function createMaterialIcon(subject, extraClass = '') {
    const visual = getMaterialVisual(subject);
    const icon = document.createElement('span');
    icon.className = `material-icon ${extraClass}`.trim();
    icon.style.color = visual.color;
    icon.textContent = visual.emoji || '📌';
    return icon;
}

function padArabic(text, width) {
    const value = String(text || '');
    return value + ' '.repeat(Math.max(1, width - value.length));
}

function parseArabicNum(str) {
    if (!str && str !== 0) return 0;
    const englishDigits = String(str).replace(/[٠١٢٣٤٥٦٧٨٩]/g, d => '٠١٢٣٤٥٦٧٨٩'.indexOf(d));
    return parseInt(englishDigits, 10) || 0;
}

function getHijriMonthLength(year, month) {
    if (year === 1447 && month === 12) return 29;
    if (findGregorianForHijri(year, month, 30)) return 30;
    return 29;
}

function convertNumberInputs() {
    document.querySelectorAll('input[type="number"]').forEach(input => {
        // Build the wrapper
        const wrapper = document.createElement('div');
        wrapper.className = 'flex items-center border border-emerald-200 rounded-lg overflow-hidden bg-white shadow-sm';
        input.parentNode.replaceChild(wrapper, input);

        input.type = 'text';
        input.inputMode = 'numeric';
        input.className = 'w-full text-center font-black text-sm outline-none bg-transparent py-1.5';

        const min = input.hasAttribute('min') ? parseInt(input.getAttribute('min')) : -999;
        const max = input.hasAttribute('max') ? parseInt(input.getAttribute('max')) : 999;

        const btnMinus = document.createElement('button');
        btnMinus.type = 'button';
        btnMinus.className = 'w-8 h-8 flex items-center justify-center bg-slate-50 hover:bg-slate-100 text-slate-700 font-bold border-l border-emerald-100 active:bg-slate-200';
        btnMinus.textContent = '-';
        btnMinus.onclick = () => {
            let val = parseArabicNum(input.value);
            if (val > min) val--;
            input.value = toArabicDigits(val);
            input.dispatchEvent(new Event('input'));
        };

        const btnPlus = document.createElement('button');
        btnPlus.type = 'button';
        btnPlus.className = 'w-8 h-8 flex items-center justify-center bg-slate-50 hover:bg-slate-100 text-slate-700 font-bold border-r border-emerald-100 active:bg-slate-200';
        btnPlus.textContent = '+';
        btnPlus.onclick = () => {
            let val = parseArabicNum(input.value);
            if (val < max) val++;
            input.value = toArabicDigits(val);
            input.dispatchEvent(new Event('input'));
        };

        input.addEventListener('blur', () => {
            let val = parseArabicNum(input.value);
            if (val < min) val = min;
            if (val > max) val = max;
            input.value = toArabicDigits(val);
            input.dispatchEvent(new Event('input'));
        });

        wrapper.appendChild(btnPlus);
        wrapper.appendChild(input);
        wrapper.appendChild(btnMinus);

        // initial formatting
        if (input.value) input.value = toArabicDigits(input.value);
    });
}

function attachInputs() {
    convertNumberInputs();
    Object.keys(defaultState.fields).forEach(id => {
        const el = byId(id);
        if (!el) return;
        if (el.type === 'checkbox') {
            el.addEventListener('change', () => {
                state.fields[id] = el.checked ? 'true' : 'false';
                if (id === 'week2_enabled') initTable(true);
                updateAll();
                queueSave();
            });
            return;
        }

        const eventType = (el.tagName === 'SELECT' || el.type === 'checkbox') ? 'change' : 'input';
        el.addEventListener(eventType, () => {
            const oldValue = state.fields[id];
            state.fields[id] = el.value;

            if (id === 'gender_mode' && oldValue !== el.value) {
                const isFemale = el.value === 'female';
                const maleLabel = 'مدير المدرسة';
                const femaleLabel = 'مديرة المدرسة';
                
                // Only auto-update if the user hasn't already customized it to something unique
                if (state.fields.principal_label_input === maleLabel && isFemale) {
                    state.fields.principal_label_input = femaleLabel;
                    if (byId('principal_label_input')) byId('principal_label_input').value = femaleLabel;
                } else if (state.fields.principal_label_input === femaleLabel && !isFemale) {
                    state.fields.principal_label_input = maleLabel;
                    if (byId('principal_label_input')) byId('principal_label_input').value = maleLabel;
                }
            }
            if (id === 'logo_url_input') state.fields.logo_data_url = '';
            if (['days_count', 'start_day', 'start_month', 'week2_days_count', 'week2_start_day', 'week2_start_month'].includes(id)) {
                normalizeDateInputs(false);
                initTable();
            }
            updateAll();
            queueSave();
        });
    });

    byId('logo_file_input').addEventListener('change', event => {
        const file = event.target.files && event.target.files[0];
        if (!file) return;
        if (!file.type.startsWith('image/')) {
            showToast('اختر ملف صورة فقط');
            event.target.value = '';
            return;
        }
        const reader = new FileReader();
        reader.onload = () => {
            state.fields.logo_data_url = reader.result;
            updateAll();
            queueSave();
            showToast('تم إرفاق الشعار');
        };
        reader.readAsDataURL(file);
    });

    byId('backup_file_input').addEventListener('change', importBackup);

    byId('stageSelect').addEventListener('change', changeStage);
    byId('class_template_select').addEventListener('change', applyClassTemplate);
    byId('new_material').addEventListener('keydown', event => {
        if (event.key === 'Enter') addMaterial();
    });
    byId('new_class_name').addEventListener('keydown', event => {
        if (event.key === 'Enter') addClassColumn();
    });
}

function normalizeDateInputs(commitDisplay = true) {
    const scheduleYear = getScheduleHijriYear();
    state.fields.days_count = String(clampNumber(parseArabicNum(byId('days_count').value), 1, 12, 5));
    state.fields.start_month = String(clampNumber(parseArabicNum(byId('start_month').value), 1, 12, 1));
    const startMonthLength = getHijriMonthLength(scheduleYear, parseArabicNum(state.fields.start_month));
    const requestedStartDay = parseArabicNum(byId('start_day').value);
    state.fields.start_day = String(clampNumber(requestedStartDay, 1, startMonthLength, 1));
    if (commitDisplay) {
        byId('days_count').value = toArabicDigits(state.fields.days_count);
        byId('start_day').value = toArabicDigits(state.fields.start_day);
        byId('start_month').value = toArabicDigits(state.fields.start_month);
    } else if (requestedStartDay > startMonthLength) {
        byId('start_day').value = toArabicDigits(state.fields.start_day);
    }

    if (byId('week2_days_count')) {
        state.fields.week2_days_count = String(clampNumber(parseArabicNum(byId('week2_days_count').value), 1, 12, 5));
        state.fields.week2_start_month = String(clampNumber(parseArabicNum(byId('week2_start_month').value), 1, 12, 1));
        const week2MonthLength = getHijriMonthLength(scheduleYear, parseArabicNum(state.fields.week2_start_month));
        const requestedWeek2StartDay = parseArabicNum(byId('week2_start_day').value);
        state.fields.week2_start_day = String(clampNumber(requestedWeek2StartDay, 1, week2MonthLength, 1));
        if (commitDisplay) {
            byId('week2_days_count').value = toArabicDigits(state.fields.week2_days_count);
            byId('week2_start_day').value = toArabicDigits(state.fields.week2_start_day);
            byId('week2_start_month').value = toArabicDigits(state.fields.week2_start_month);
        } else if (requestedWeek2StartDay > week2MonthLength) {
            byId('week2_start_day').value = toArabicDigits(state.fields.week2_start_day);
        }
    }
}

function loadState() {
    try {
        const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
        if (!saved) return;
        state = mergeLoadedState(saved);
    } catch {
        state = deepClone(defaultState);
    }
}

function applyStateToInputs() {
    Object.entries(state.fields).forEach(([id, value]) => {
        if (!byId(id)) return;
        if (byId(id).type === 'checkbox') {
            byId(id).checked = value === 'true';
        } else {
            const isNumeric = byId(id).inputMode === 'numeric';
            byId(id).value = isNumeric ? toArabicDigits(value) : value;
        }
    });
    byId('stageSelect').value = state.currentStage;
    renderClassTemplateOptions();
}

function saveState(manual = false) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    if (manual) showToast('تم حفظ البيانات بنجاح');
}

const materialSortOrder = [
    'رياضيات', 'لغتي', 'إنجليزي', 'علوم', 'إسلامية',
    'فيزياء', 'كيمياء', 'أحياء', 'علم الأرض', 'علم البيئة',
    'اجتماعيات', 'جغرافيا', 'علم نفس',
    'رقمية', 'تقنية رقمية', 'مواطنة رقمية',
    'كفايات', 'تفكير ناقد', 'دراسات أدبية',
    'م. حياتية', 'مهارات حياتية', 'معرفة مالية', 'تربية مهنية',
    'بدنية', 'لياقة وثقافة', 'فنية', 'فنون', 'نشاط',
    HOLIDAY_SUBJECT, REST_SUBJECT, CENTRAL_SUBJECT
];

function sortMaterialsList(materials) {
    const order = new Map(materialSortOrder.map((name, index) => [name, index]));
    return [...new Set(materials)].sort((a, b) => {
        const aOrder = order.has(a) ? order.get(a) : 999;
        const bOrder = order.has(b) ? order.get(b) : 999;
        if (aOrder !== bOrder) return aOrder - bOrder;
        return String(a).localeCompare(String(b), 'ar');
    });
}

function mergeLoadedState(loaded) {
    const merged = {
        ...deepClone(defaultState),
        ...loaded,
        fields: { ...defaultState.fields, ...(loaded.fields || {}) },
        materials: { ...defaultState.materials, ...(loaded.materials || {}) },
        materialColors: { ...defaultState.materialColors, ...(loaded.materialColors || {}) },
        classColors: Array.isArray(loaded.classColors) ? loaded.classColors : deepClone(defaultState.classColors),
        rowColors: Array.isArray(loaded.rowColors) ? loaded.rowColors : [],
        instructions: Array.isArray(loaded.instructions) ? loaded.instructions : deepClone(defaultState.instructions),
        tableRows: Array.isArray(loaded.tableRows) ? loaded.tableRows : [],
        tableRows2: Array.isArray(loaded.tableRows2) ? loaded.tableRows2 : []
    };

    // Migrate old long names to short names
    const migrations = {
        'القرآن والدراسات الإسلامية': 'إسلامية',
        'اللغة العربية': 'لغتي',
        'التربية الفنية': 'فنية',
        'مهارات حياتية وأسرية': 'م. حياتية',
        'التربية البدنية والدفاع عن النفس': 'بدنية',
        'الدراسات الاجتماعية': 'اجتماعيات',
        'المهارات الرقمية': 'رقمية',
        'اللغة الإنجليزية': 'إنجليزي',
        'الكفايات اللغوية': 'كفايات',
        'التقنية الرقمية': 'تقنية رقمية',
        'التربية المهنية': 'تربية مهنية',
        'المعرفة المالية': 'معرفة مالية',
        'الدراسات الأدبية': 'دراسات أدبية',
        'علوم الأرض والفضاء': 'علم الأرض'
    };

    Object.keys(merged.materials).forEach(stage => {
        merged.materials[stage] = merged.materials[stage].map(m => migrations[m] || m);
        // Remove duplicates
        merged.materials[stage] = sortMaterialsList(merged.materials[stage]);
    });

    // Update subjects in rows
    merged.tableRows.forEach(row => {
        if (row.material && migrations[row.material]) row.material = migrations[row.material];
        if (row.subjects) {
            row.subjects = row.subjects.map(list => list.map(s => migrations[s] || s));
        }
    });
    merged.tableRows2.forEach(row => {
        if (row.material && migrations[row.material]) row.material = migrations[row.material];
        if (row.subjects) {
            row.subjects = row.subjects.map(list => list.map(s => migrations[s] || s));
        }
    });

    // Ensure no default materials are lost
    Object.keys(defaultState.materials).forEach(stage => {
        if (!merged.materials[stage]) merged.materials[stage] = [];
        defaultState.materials[stage].forEach(mat => {
            if (!merged.materials[stage].includes(mat)) {
                merged.materials[stage].push(mat);
            }
        });
        merged.materials[stage] = sortMaterialsList(merged.materials[stage]);
    });

    return merged;
}

function refreshAppFromState() {
    applyStateToInputs();
    normalizeDateInputs();
    if (!state.tableRows.length) initTable();
    renderClassEditor();
    renderMaterialsBank();
    renderInstructionsEditor();
    renderInstructionsDisplay();
    renderRowColorsEditor();
    updateAll();
    saveState(false);
}

function exportBackup() {
    saveState(false);
    const payload = {
        app: 'smart-exam-schedule',
        version: 3,
        exportedAt: new Date().toISOString(),
        state
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    const school = (state.fields.school_name_input || 'exam-schedule').replace(/[^\u0600-\u06FF\w-]+/g, '-');
    link.href = url;
    link.download = `${school}-backup.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    showToast('تم تصدير نسخة البيانات');
}

function importBackup(event) {
    const file = event.target.files && event.target.files[0];
    event.target.value = '';
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
        try {
            const parsed = JSON.parse(reader.result);
            const loadedState = parsed.state || parsed;
            if (!loadedState || typeof loadedState !== 'object') throw new Error('Invalid backup');
            state = mergeLoadedState(loadedState);
            refreshAppFromState();
            showToast('تم استيراد النسخة بنجاح');
        } catch {
            showToast('ملف النسخة غير صالح');
        }
    };
    reader.readAsText(file);
}

function updateAll() {
    updateHeaderBlock('header_right',
        [state.fields.h_r1, state.fields.h_r2, state.fields.h_r3, state.fields.school_name_input],
        state.fields.header_right_align, state.fields.header_right_size);
    updateHeaderBlock('header_left',
        [state.fields.h_l1, state.fields.h_l2, state.fields.h_l3],
        state.fields.header_left_align, state.fields.header_left_size);

    setText('main_title_display', state.fields.main_title_input);
    const isFemale = state.fields.gender_mode === 'female';
    setText('principal_label', state.fields.principal_label_input);
    
    // Update instructions gender if they are default
    const defaultMaleInst = 'على كل طالب احضار ادواته.';
    const defaultFemaleInst = 'على كل طالبة احضار ادواتها.';
    let changed = false;
    state.instructions = state.instructions.map(inst => {
        if (inst === defaultMaleInst && isFemale) { changed = true; return defaultFemaleInst; }
        if (inst === defaultFemaleInst && !isFemale) { changed = true; return defaultMaleInst; }
        return inst;
    });
    if (changed) renderInstructionsEditor();
    renderInstructionsDisplay();

    setText('principal_display', state.fields.principal_input);

    const mainTitleEl = byId('main_title_display');
    if (mainTitleEl) mainTitleEl.style.fontSize = `${clampNumber(state.fields.main_title_size, 14, 40, 20)}px`;
    const principalEl = byId('principal_display');
    if (principalEl) principalEl.style.fontSize = `${clampNumber(state.fields.principal_size, 10, 28, 14)}px`;

    const logo = byId('logoImg');
    if (logo) {
        logo.src = state.fields.logo_data_url || state.fields.logo_url_input || ministryLogo;
        logo.onerror = () => { logo.src = ministryLogo; };
    }

    const printArea = byId('printArea');
    if (printArea && state.fields.font_family) {
        printArea.style.fontFamily = `'${state.fields.font_family}', sans-serif`;
    }
    const printRoot = document.querySelector('.print-root');
    if (printRoot && state.fields.font_family) {
        printRoot.style.fontFamily = `'${state.fields.font_family}', sans-serif`;
    }

    const w2s = byId('week2_settings');
    if (w2s) w2s.classList.toggle('hidden', !isEnabled('week2_enabled'));

    renderTablesContainer();
    renderInstructionsDisplay();
    renderRowColorsEditor();
    updatePrintStyle();

    const container = byId('printArea');
    if (container) {
        container.classList.remove('theme-purple', 'theme-ocean', 'theme-modern');
        if (state.fields.table_theme !== 'emerald') {
            container.classList.add(`theme-${state.fields.table_theme}`);
        }
    }
    if (window.lucide) lucide.createIcons();
    fitPreviewToViewport();
}

function renderTablesContainer() {
    const container = byId('tables_container');
    if (!container) return;
    container.innerHTML = '';
    container.className = 'tables-container px-4 md:px-8';

    const isMinisterial = state.fields.table_mode === 'ministerial';

    if (isMinisterial) {
        if (isEnabled('merge_weeks') && isEnabled('week2_enabled')) {
            // أسابيع متصلة في جدول واحد
            if (isEnabled('show_week_box')) {
                const wb1 = document.createElement('div');
                wb1.className = 'text-center mb-4';
                const week1Text = isEnabled('use_arabic_numerals') ? toArabicDigits(state.fields.week_number) : state.fields.week_number;
                const week2Text = isEnabled('use_arabic_numerals') ? toArabicDigits(state.fields.week2_number) : state.fields.week2_number;
                wb1.innerHTML = `<div class="inline-block bg-[#2a8da8] text-white px-10 py-2 rounded-lg font-black text-base shadow">${week1Text} و ${week2Text}</div>`;
                container.appendChild(wb1);
            }
            const mergedRows = [...state.tableRows, ...state.tableRows2];
            const t1 = buildMinisterialTable(mergedRows);
            container.appendChild(t1);
        } else {
            // أسابيع منفصلة
            if (isEnabled('show_week_box')) {
                const wb1 = document.createElement('div');
                wb1.className = 'text-center mb-4';
                wb1.innerHTML = `<div class="inline-block bg-[#2a8da8] text-white px-10 py-2 rounded-lg font-black text-base shadow">${isEnabled('use_arabic_numerals') ? toArabicDigits(state.fields.week_number) : state.fields.week_number}</div>`;
                container.appendChild(wb1);
            }
            const t1 = buildMinisterialTable(state.tableRows);
            container.appendChild(t1);

            if (isEnabled('week2_enabled') && state.tableRows2.length) {
                const sep = document.createElement('div');
                sep.className = 'my-2';
                container.appendChild(sep);

                if (isEnabled('show_week_box')) {
                    const wb2 = document.createElement('div');
                    wb2.className = 'text-center mb-4';
                    wb2.innerHTML = `<div class="inline-block bg-[#2a8da8] text-white px-10 py-2 rounded-lg font-black text-base shadow">${isEnabled('use_arabic_numerals') ? toArabicDigits(state.fields.week2_number) : state.fields.week2_number}</div>`;
                    container.appendChild(wb2);
                }
                const t2 = buildMinisterialTable(state.tableRows2, true);
                container.appendChild(t2);
            }
        }
    } else {
        if (isEnabled('show_week_box')) {
            const wb = document.createElement('div');
            wb.className = 'text-center mb-4';
            wb.innerHTML = `<div class="inline-block bg-[#2a8da8] text-white px-10 py-2 rounded-lg font-black text-base shadow">${isEnabled('use_arabic_numerals') ? toArabicDigits(state.fields.week_number) : state.fields.week_number}</div>`;
            container.appendChild(wb);
        }
        // Traditional table
        const tableWrap = document.createElement('div');
        tableWrap.className = 'table-scroll w-full overflow-x-hidden print:overflow-visible hide-scrollbar';
        const table = document.createElement('table');
        table.className = 'schedule-table w-full border-collapse border-2 border-slate-900 text-center min-w-0 print:min-w-0 md:min-w-full';
        const thead = document.createElement('thead');
        thead.id = 'table_head';
        thead.className = 'bg-emerald-900 text-white';
        const tbody = document.createElement('tbody');
        tbody.id = 'table_body';
        table.appendChild(thead);
        table.appendChild(tbody);
        tableWrap.appendChild(table);
        container.appendChild(tableWrap);
        renderTableMultiColumn(thead, tbody);
        if (window.lucide) lucide.createIcons();
    }
}

function buildMinisterialTable(rows, isWeek2) {
    const wrapper = document.createElement('div');
    wrapper.className = 'table-scroll w-full overflow-x-hidden print:overflow-visible hide-scrollbar';
    const table = document.createElement('table');
    table.className = 'schedule-table schedule-table--printable w-full border-collapse border-2 border-slate-900 text-center min-w-0';

    const thead = document.createElement('thead');
    thead.className = 'bg-emerald-900 text-white';
    const headerRow = document.createElement('tr');
    ['اليوم', 'التاريخ', 'الصفوف', 'نوع الاختبار', 'المادة'].forEach(label => {
        const th = document.createElement('th');
        th.className = 'p-3 border-2 border-slate-900';
        th.textContent = label;
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    const classesDefault = (stageClassesText[state.currentStage] || [])[0] || '';

    rows.forEach((row, rIdx) => {
        const tr = document.createElement('tr');
        tr.className = rIdx % 2 === 0 ? 'bg-white' : 'bg-slate-50';

        const dayTd = document.createElement('td');
        dayTd.className = 'p-2 border border-slate-900 font-black text-sm';
        
        const dayWrap = document.createElement('div');
        dayWrap.className = 'flex flex-col items-center gap-1';
        
        const dayText = document.createElement('span');
        dayText.textContent = row.day;
        dayWrap.appendChild(dayText);

        const bulkBtn = document.createElement('button');
        bulkBtn.type = 'button';
        bulkBtn.className = 'bulk-apply-btn no-print w-7 h-7 bg-slate-500 text-white rounded-full shadow-sm hover:bg-slate-600 transition-colors flex items-center justify-center mt-1';
        bulkBtn.innerHTML = '<i data-lucide="plus" class="w-3.5 h-3.5"></i>';
        bulkBtn.title = 'تعبئة اليوم من قائمة المواد';
        bulkBtn.onclick = (event) => showBulkMaterialSelector(rIdx, event.currentTarget, true, rows);
        dayWrap.appendChild(bulkBtn);

        dayTd.appendChild(dayWrap);
        tr.appendChild(dayTd);

        const dateTd = document.createElement('td');
        dateTd.className = 'p-2 border border-slate-900 text-xs font-bold';
        const arabicDate = isEnabled('use_arabic_numerals');
        const dateVal = arabicDate ? toArabicDigits(row.date) : row.date;
        dateTd.innerHTML = renderDateHtml(dateVal, arabicDate);
        tr.appendChild(dateTd);

        const classesTd = document.createElement('td');
        classesTd.className = 'p-1 border border-slate-900';

        const classSelect = document.createElement('select');
        classSelect.className = 'list-mode-input cell-tools font-black text-sm';

        const stageOpts = stageClassesText[state.currentStage] || [state.classNames.join(' - ')];
        const classOptions = [...stageOpts];

        let hasSelected = false;
        classOptions.forEach(optVal => {
            const o = document.createElement('option');
            o.value = optVal; o.textContent = optVal;
            if (row.classes === optVal) {
                o.selected = true;
                hasSelected = true;
            }
            classSelect.appendChild(o);
        });

        if (!hasSelected && row.classes) {
            const o = document.createElement('option');
            o.value = row.classes; o.textContent = row.classes;
            o.selected = true;
            classSelect.appendChild(o);
        }

        if (!row.classes || !classOptions.includes(row.classes)) {
            row.classes = classOptions[0] || '';
            if (classSelect.options.length > 0) classSelect.options[0].selected = true;
        }

        classSelect.addEventListener('change', () => {
            row.classes = classSelect.value;
            classPrint.textContent = classSelect.value;
            queueSave();
        });

        const classPrint = document.createElement('span');
        classPrint.className = 'print-list-text';
        classPrint.textContent = row.classes;

        classesTd.appendChild(classSelect);
        classesTd.appendChild(classPrint);
        tr.appendChild(classesTd);

        const typeTd = document.createElement('td');
        typeTd.className = 'p-1 border border-slate-900';
        const typeSelect = document.createElement('select');
        typeSelect.className = 'list-mode-input cell-tools';
        ['تكويني', 'اختبار الفترة', 'تكويني -فتري', 'تكويني- فتري', 'نهائي', HOLIDAY_SUBJECT, REST_SUBJECT].forEach(v => {
            const o = document.createElement('option');
            o.value = v; o.textContent = v;
            o.selected = v === row.test_type;
            typeSelect.appendChild(o);
        });
        typeSelect.addEventListener('change', () => { row.test_type = typeSelect.value; queueSave(); });
        const typePrint = document.createElement('span');
        typePrint.className = 'print-list-text';
        typePrint.textContent = row.test_type || '-';
        typeTd.appendChild(typeSelect);
        typeTd.appendChild(typePrint);
        tr.appendChild(typeTd);

        const matTd = document.createElement('td');
        matTd.className = 'p-2 border border-slate-900 text-center';
        const matSelect = document.createElement('select');
        matSelect.className = 'list-mode-input cell-tools';
        const emptyOpt = document.createElement('option');
        emptyOpt.value = ''; emptyOpt.textContent = '- اختر المادة -';
        matSelect.appendChild(emptyOpt);
        state.materials[state.currentStage].forEach(m => {
            const o = document.createElement('option');
            o.value = m; o.textContent = m;
            o.selected = m === row.material;
            matSelect.appendChild(o);
        });
        const centralOpt = document.createElement('option');
        centralOpt.value = CENTRAL_SUBJECT;
        centralOpt.textContent = CENTRAL_SUBJECT;
        centralOpt.selected = row.material === CENTRAL_SUBJECT;
        matSelect.appendChild(centralOpt);

        const holidayOpt = document.createElement('option');
        holidayOpt.value = HOLIDAY_SUBJECT;
        holidayOpt.textContent = HOLIDAY_SUBJECT;
        holidayOpt.selected = row.material === HOLIDAY_SUBJECT;
        matSelect.appendChild(holidayOpt);

        const restOpt = document.createElement('option');
        restOpt.value = REST_SUBJECT;
        restOpt.textContent = REST_SUBJECT;
        restOpt.selected = row.material === REST_SUBJECT;
        matSelect.appendChild(restOpt);

        const updateMatColor = () => {
            matTd.classList.toggle('central-ministerial-cell', isCentralSubject(row.material));
            if (isEnabled('use_material_colors') && row.material) {
                const mColor = state.materialColors[state.currentStage]?.[row.material];
                if (mColor) { matTd.style.backgroundColor = mColor; return; }
            }
            if (isCentralSubject(row.material)) {
                matTd.style.backgroundColor = '#fffbeb';
                matTd.style.webkitPrintColorAdjust = 'exact';
                matTd.style.printColorAdjust = 'exact';
                return;
            }
            if (row.material) {
                const matColors = ['#e8f5e9', '#e3f2fd', '#fff3e0', '#fce4ec', '#f3e5f5', '#e0f7fa', '#fff8e1', '#f1f8e9', '#e8eaf6'];
                const matIdx = state.materials[state.currentStage].indexOf(row.material);
                matTd.style.backgroundColor = (matIdx >= 0) ? matColors[matIdx % matColors.length] : 'transparent';
            } else {
                matTd.style.backgroundColor = 'transparent';
            }
        };

        matSelect.addEventListener('change', () => {
            row.material = matSelect.value;
            matPrint.textContent = matSelect.value || '-';
            matPrint.classList.toggle('central-subject-print', isCentralSubject(row.material));
            updateMatColor();
            queueSave();
        });
        const matPrint = document.createElement('span');
        matPrint.className = 'print-list-text font-black text-sm text-center';
        if (isCentralSubject(row.material)) matPrint.classList.add('central-subject-print');
        matPrint.style.color = '#000';
        matPrint.textContent = row.material || '-';
        updateMatColor();
        matTd.appendChild(matSelect);
        matTd.appendChild(matPrint);
        tr.appendChild(matTd);

        tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    wrapper.appendChild(table);
    return wrapper;
}

function queueSave() {
    window.clearTimeout(saveTimer);
    saveTimer = window.setTimeout(() => saveState(false), 250);
}

function switchTab(tab) {
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    const tabEl = byId(tab + '-tab');
    const btnEl = byId('btn-' + tab);
    if (tabEl) tabEl.classList.add('active');
    if (btnEl) btnEl.classList.add('active');
    if (tab === 'preview') {
        updateAll();
        window.requestAnimationFrame(fitPreviewToViewport);
    }
    if (window.lucide) lucide.createIcons();
}

function updateHeaderBlock(id, lines, align, fontSize) {
    const block = byId(id);
    if (!block) return;
    block.innerHTML = '';
    block.style.textAlign = align || 'inherit';
    block.style.fontSize = `${clampNumber(fontSize, 8, 22, 11)}px`;
    lines.forEach(line => {
        const p = document.createElement('p');
        p.textContent = line || '';
        block.appendChild(p);
    });
}

function getScheduleHijriYear() {
    const yearText = `${state.fields.h_l3 || ''} ${state.fields.week_number || ''}`;
    const match = yearText.replace(/[٠-٩]/g, d => '٠١٢٣٤٥٦٧٨٩'.indexOf(d)).match(/\d{4}/);
    return match ? parseInt(match[0], 10) : 1447;
}

function getHijriPartsFromDate(date) {
    try {
        const parts = new Intl.DateTimeFormat('en-u-ca-islamic-umalqura', {
            day: 'numeric',
            month: 'numeric',
            year: 'numeric',
            timeZone: 'Asia/Riyadh'
        }).formatToParts(date);
        const pick = type => parseInt(parts.find(part => part.type === type)?.value, 10);
        const year = pick('year');
        const month = pick('month');
        const day = pick('day');
        if (year && month && day) return { year, month, day };
    } catch {
        return null;
    }
    return null;
}

function findGregorianForHijri(year, month, day) {
    const islamicEpoch = Date.UTC(622, 6, 19);
    const approxDays = Math.floor(((year - 1) * 354.367) + ((month - 1) * 29.53) + day);
    const approx = islamicEpoch + (approxDays * 24 * 60 * 60 * 1000);
    const start = approx - (45 * 24 * 60 * 60 * 1000);
    const end = approx + (45 * 24 * 60 * 60 * 1000);
    for (let time = start; time <= end; time += 24 * 60 * 60 * 1000) {
        const date = new Date(time);
        const parts = getHijriPartsFromDate(date);
        if (parts && parts.year === year && parts.month === month && parts.day === day) {
            return date;
        }
    }
    return null;
}

function isTabularHijriLeapYear(year) {
    return ((11 * year) + 14) % 30 < 11;
}

function getFallbackHijriMonthLength(year, month) {
    if (year === 1447 && month === 12) return 29;
    if (month === 12) return isTabularHijriLeapYear(year) ? 30 : 29;
    return month % 2 === 1 ? 30 : 29;
}

function addFallbackHijriDays(parts, days) {
    let { year, month, day } = parts;
    for (let i = 0; i < days; i++) {
        day += 1;
        if (day > getFallbackHijriMonthLength(year, month)) {
            day = 1;
            month += 1;
            if (month > 12) {
                month = 1;
                year += 1;
            }
        }
    }
    return { year, month, day };
}

function formatHijriDate(parts) {
    return `${String(parts.day).padStart(2, '0')}/${String(parts.month).padStart(2, '0')}/${parts.year} هـ`;
}

function formatDateForDisplay(dateText) {
    return String(dateText || '')
        .replace(/\s*\/\s*/g, '/')
        .replace(/\s*هـ\s*$/u, ' هـ')
        .trim();
}

function renderDateHtml(dateText, arabicMode = false) {
    const cleanDate = String(dateText || '')
        .replace(/\s*\/\s*/g, '/')
        .trim()
        .split(/\s+/)[0] || '';
    const parts = cleanDate.split('/');
    const displayDate = arabicMode && parts.length === 3
        ? `${parts[2]}/${parts[1]}/${parts[0]}`
        : cleanDate;
    const dir = arabicMode ? 'rtl' : 'ltr';
    return `<span class="date-print date-print--${dir}" dir="${dir}"><span class="date-number">${displayDate}</span><span class="date-suffix">هـ</span></span>`;
}

function initTable(keepSubjects = false) {
    state.tableRows = buildWeekRows(
        state.fields.days_count, state.fields.start_day, state.fields.start_month,
        state.fields.start_day_name, keepSubjects ? state.tableRows : []);

    if (isEnabled('week2_enabled')) {
        state.tableRows2 = buildWeekRows(
            state.fields.week2_days_count, state.fields.week2_start_day, state.fields.week2_start_month,
            state.fields.start_day_name, keepSubjects ? state.tableRows2 : []);
    }

    const totalDays = state.tableRows.length + (state.tableRows2 || []).length;
    state.rowColors = Array.from({ length: totalDays }, (_, idx) => state.rowColors[idx] || '#ffffff');
    renderTable();
    queueSave();
}

function buildWeekRows(daysCountRaw, startDayRaw, startMonthRaw, startDayName, oldRows) {
    const count = clampNumber(daysCountRaw, 1, 10, 5);
    const startDay = clampNumber(startDayRaw, 1, 30, 1);
    const startMonth = clampNumber(startMonthRaw, 1, 12, 1);
    const startYear = getScheduleHijriYear();
    const startIdx = Math.max(0, daysSequence.indexOf(startDayName));
    const classesDefault = (stageClassesText[state.currentStage] || [])[0] || '';

    const rows = [];
    let currentGregorian = findGregorianForHijri(startYear, startMonth, startDay);
    let currentHijri = currentGregorian ? getHijriPartsFromDate(currentGregorian) : { year: startYear, month: startMonth, day: startDay };

    for (let i = 0; i < count; i++) {
        const oldRow = oldRows[i] || {};
        const dayName = daysSequence[(startIdx + i) % 5];
        rows.push({
            day: dayName,
            date: formatHijriDate(currentHijri),
            subjects: Array.from({ length: state.classNames.length }, (_, idx) => normalizeSubjectList(oldRow.subjects?.[idx], true)),
            classes: oldRow.classes || classesDefault,
            test_type: oldRow.test_type || 'تكويني',
            material: oldRow.material || ''
        });
        const daysToAdd = dayName === 'الخميس' ? 3 : 1;
        if (currentGregorian) {
            currentGregorian = new Date(currentGregorian.getTime() + (daysToAdd * 24 * 60 * 60 * 1000));
            currentHijri = getHijriPartsFromDate(currentGregorian) || addFallbackHijriDays(currentHijri, daysToAdd);
        } else {
            currentHijri = addFallbackHijriDays(currentHijri, daysToAdd);
        }
    }
    return rows;
}

function changeStage() {
    state.currentStage = byId('stageSelect').value;
    const titles = {
        early_childhood: 'جدول اختبارات الفترة الثانية لمرحلة الطفولة المبكرة',
        elementary: 'جدول اختبارات الفترة الثانية للمرحلة الابتدائية',
        intermediate: 'جدول اختبارات الفترة الثانية للمرحلة المتوسطة',
        secondary: 'جدول اختبارات الفترة الثانية للمرحلة الثانوية'
    };

    state.fields.main_title_input = titles[state.currentStage] || '';
    const titleInput = byId('main_title_input');
    if (titleInput) titleInput.value = state.fields.main_title_input;

    const modeSelect = byId('table_mode');
    if (modeSelect) modeSelect.value = state.fields.table_mode;
    const themeSelect = byId('table_theme');
    if (themeSelect) themeSelect.value = state.fields.table_theme;

    renderClassTemplateOptions(true);
    applyClassTemplate();
    renderMaterialsBank();
    initTable();
    updateAll();
}

function renderClassTemplateOptions(resetToDefault = false) {
    const select = byId('class_template_select');
    if (!select) return;
    const templates = classTemplates[state.currentStage] || {};
    select.innerHTML = '';

    Object.keys(templates).forEach(key => {
        const option = document.createElement('option');
        option.value = key;
        option.textContent = classTemplateLabels[key] || key;
        select.appendChild(option);
    });

    const customOption = document.createElement('option');
    customOption.value = 'custom';
    customOption.textContent = 'مخصص - حسب الفصول المدخلة';
    select.appendChild(customOption);

    const firstKey = Object.keys(templates)[0] || '';
    if (resetToDefault || (!templates[state.fields.class_template] && state.fields.class_template !== 'custom')) {
        state.fields.class_template = firstKey;
    }
    select.value = state.fields.class_template;
}

function applyClassTemplate() {
    const templateKey = byId('class_template_select').value;
    if (templateKey === 'custom') {
        state.fields.class_template = 'custom';
        queueSave();
        return;
    }
    const template = classTemplates[state.currentStage]?.[templateKey];
    if (!template) return;
    state.fields.class_template = templateKey;
    state.classNames = [...template];
    state.classColors = state.classNames.map((_, index) => state.classColors[index] || defaultColor(index));
    renderClassEditor();
    initTable();
    updateAll();
    queueSave();
}

function renderClassEditor() {
    const container = byId('class_names_editor');
    container.innerHTML = '';
    state.classNames.forEach((name, i) => {
        const wrap = document.createElement('div');
        wrap.className = 'flex items-center gap-1';

        const input = document.createElement('input');
        input.type = 'text';
        input.value = name;
        input.className = 'field min-w-0 flex-1 font-bold bg-white text-center';
        input.addEventListener('input', () => {
            state.classNames[i] = input.value;
            initTable(true);
            updateAll();
            queueSave();
        });

        const color = document.createElement('input');
        color.type = 'color';
        color.value = state.classColors[i] || defaultColor(i);
        color.className = 'w-9 h-[34px] rounded border border-slate-200 bg-white p-1 flex-shrink-0';
        color.title = 'لون عمود الفصل';
        color.addEventListener('input', () => {
            state.classColors[i] = color.value;
            renderTable();
            queueSave();
        });

        const deleteBtn = document.createElement('button');
        deleteBtn.type = 'button';
        deleteBtn.className = 'icon-btn text-red-600 hover:bg-red-50 border border-red-100 flex-shrink-0';
        deleteBtn.title = 'حذف الفصل';
        deleteBtn.innerHTML = '<i data-lucide="trash-2" class="w-4 h-4"></i>';
        deleteBtn.addEventListener('click', () => deleteClassColumn(i));

        wrap.appendChild(input);
        wrap.appendChild(color);
        wrap.appendChild(deleteBtn);
        container.appendChild(wrap);
    });
    if (window.lucide) lucide.createIcons();
}

function addClassColumn() {
    const input = byId('new_class_name');
    const name = input.value.trim();
    if (!name) return;
    state.classNames.push(name);
    state.classColors.push(defaultColor(state.classColors.length));
    state.tableRows.forEach(row => row.subjects.push([]));
    input.value = '';
    state.fields.class_template = 'custom';
    renderClassEditor();
    renderTable();
    updatePrintStyle();
    queueSave();
    showToast('تمت إضافة الفصل');
}

function deleteClassColumn(index) {
    if (state.classNames.length <= 1) {
        showToast('يجب أن يبقى فصل واحد على الأقل');
        return;
    }
    if (!confirm('هل تريد حذف هذا الفصل من الجدول؟')) return;
    state.classNames.splice(index, 1);
    state.classColors.splice(index, 1);
    state.tableRows.forEach(row => row.subjects.splice(index, 1));
    state.fields.class_template = 'custom';
    renderClassEditor();
    renderTable();
    updatePrintStyle();
    queueSave();
    showToast('تم حذف الفصل');
}

function renderMaterialsBank() {
    const container = byId('materials_tags');
    container.innerHTML = '';
    state.materials[state.currentStage].forEach((material, i) => {
        const tag = document.createElement('span');
        tag.className = 'bg-emerald-50 border border-emerald-100 text-emerald-800 px-2.5 py-1 rounded-full text-[11px] font-bold flex items-center gap-1.5 shadow-sm';

        const color = document.createElement('input');
        color.type = 'color';
        color.value = state.materialColors[state.currentStage]?.[material] || defaultColor(i);
        color.className = 'w-6 h-6 rounded-full border border-emerald-100 bg-white p-0.5';
        color.title = 'لون المادة';
        color.addEventListener('input', () => {
            if (!state.materialColors[state.currentStage]) state.materialColors[state.currentStage] = {};
            state.materialColors[state.currentStage][material] = color.value;
            renderTable();
            queueSave();
        });

        const text = document.createElement('span');
        text.textContent = material;

        const btn = document.createElement('button');
        btn.className = 'icon-btn text-red-600 hover:bg-red-50';
        btn.type = 'button';
        btn.title = 'حذف المادة';
        btn.innerHTML = '<i data-lucide="x" class="w-4 h-4"></i>';
        btn.addEventListener('click', () => deleteMaterial(i));

        tag.appendChild(color);
        tag.appendChild(text);
        tag.appendChild(btn);
        container.appendChild(tag);
    });
    if (window.lucide) lucide.createIcons();
}

function renderInstructionsEditor() {
    const container = byId('instructions_editor');
    if (!container) return;
    container.innerHTML = '';

    state.instructions.forEach((instruction, index) => {
        const row = document.createElement('div');
        row.className = 'flex items-center gap-2';

        const input = document.createElement('input');
        input.type = 'text';
        input.value = instruction;
        input.className = 'field flex-1 font-bold';
        input.placeholder = 'اكتب ملاحظة أو تعليمات...';
        input.addEventListener('input', () => {
            state.instructions[index] = input.value;
            renderInstructionsDisplay();
            queueSave();
        });

        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'icon-btn text-red-600 hover:bg-red-50 border border-red-100 flex-shrink-0';
        btn.title = 'حذف الملاحظة';
        btn.innerHTML = '<i data-lucide="trash-2" class="w-4 h-4"></i>';
        btn.addEventListener('click', () => deleteInstruction(index));

        row.appendChild(input);
        row.appendChild(btn);
        container.appendChild(row);
    });

    if (!state.instructions.length) {
        const empty = document.createElement('p');
        empty.className = 'text-[11px] text-slate-400 font-bold';
        empty.textContent = 'لا توجد ملاحظات حاليا. اضغط إضافة لإنشاء ملاحظة جديدة.';
        container.appendChild(empty);
    }

    if (window.lucide) lucide.createIcons();
}

function renderInstructionsDisplay() {
    const list = byId('instructions_display');
    if (!list) return;
    list.innerHTML = '';

    state.instructions
        .map(item => item.trim())
        .filter(Boolean)
        .forEach(instruction => {
            const li = document.createElement('li');
            li.className = 'flex items-center gap-2';

            const dot = document.createElement('span');
            dot.className = 'w-1.5 h-1.5 bg-emerald-600 rounded-full flex-shrink-0';

            const text = document.createElement('span');
            text.textContent = instruction;

            li.appendChild(dot);
            li.appendChild(text);
            list.appendChild(li);
        });
}

function renderRowColorsEditor() {
    const container = byId('row_colors_editor');
    if (!container) return;
    container.innerHTML = '';

    state.tableRows.forEach((row, index) => {
        const wrap = document.createElement('div');
        wrap.className = 'flex items-center gap-2 compact-box';

        const color = document.createElement('input');
        color.type = 'color';
        color.value = state.rowColors[index] || '#ffffff';
        color.className = 'w-8 h-7 rounded border border-slate-200 bg-white p-1 flex-shrink-0';
        color.addEventListener('input', () => {
            state.rowColors[index] = color.value;
            renderTable();
            queueSave();
        });

        const label = document.createElement('span');
        label.className = 'text-[11px] font-black text-slate-700 truncate';
        label.textContent = `${row.day} - ${row.date}`;

        wrap.appendChild(color);
        wrap.appendChild(label);
        container.appendChild(wrap);
    });
}

function addInstruction() {
    state.instructions.push('ملاحظة جديدة');
    renderInstructionsEditor();
    renderInstructionsDisplay();
    queueSave();
}

function deleteInstruction(index) {
    if (!confirm('هل تريد حذف هذه الملاحظة؟')) return;
    state.instructions.splice(index, 1);
    renderInstructionsEditor();
    renderInstructionsDisplay();
    queueSave();
    showToast('تم حذف الملاحظة');
}

function addMaterial() {
    const input = byId('new_material');
    const val = input.value.trim();
    if (!val) return;
    if (state.materials[state.currentStage].includes(val)) {
        showToast('هذه المادة موجودة بالفعل');
        return;
    }
    state.materials[state.currentStage].push(val);
    state.materials[state.currentStage] = sortMaterialsList(state.materials[state.currentStage]);
    input.value = '';
    renderMaterialsBank();
    renderTable();
    queueSave();
    showToast('تمت إضافة المادة');
}

function deleteMaterial(i) {
    if (!confirm('هل تريد حذف هذه المادة من بنك المواد؟')) return;
    const deleted = state.materials[state.currentStage][i];
    state.materials[state.currentStage].splice(i, 1);
    state.tableRows.forEach(row => {
        row.subjects = row.subjects.map(subjects => normalizeSubjectList(subjects).filter(subject => subject !== deleted));
    });
    renderMaterialsBank();
    renderTable();
    queueSave();
    showToast('تم حذف المادة');
}

function renderTable() {
    const head = byId('table_head');
    const body = byId('table_body');
    head.innerHTML = '';
    body.innerHTML = '';

    const isListMode = state.fields.table_mode === 'list-mode';

    if (isListMode) {
        renderTableListMode(head, body);
    } else {
        renderTableMultiColumn(head, body);
    }
    if (window.lucide) lucide.createIcons();
    renderTablesContainer();
    fitPreviewToViewport();
}

function renderTableMultiColumn(head, body) {
    const headerRow = document.createElement('tr');
    ['اليوم', 'التاريخ', ...state.classNames].forEach((label, index) => {
        const th = document.createElement('th');
        th.className = 'p-3 border-2 border-slate-900';
        th.textContent = label;
        if (label.length > 15) {
            th.style.fontSize = '12px';
        } else if (label.length > 12) {
            th.style.fontSize = '13px';
        }
        if (index >= 2 && isEnabled('use_class_colors')) {
            th.style.backgroundColor = state.classColors[index - 2] || defaultColor(index - 2);
            th.style.color = '#0f172a';
            th.style.webkitPrintColorAdjust = 'exact';
            th.style.printColorAdjust = 'exact';
        }
        headerRow.appendChild(th);
    });
    head.appendChild(headerRow);

    state.tableRows.forEach((row, rIdx) => {
        const tr = document.createElement('tr');
        tr.className = rIdx % 2 === 0 ? 'bg-white' : 'bg-emerald-50/20';

        const dayCell = document.createElement('td');
        dayCell.className = 'p-2 border-2 border-slate-900 font-black text-sm';
        if (isEnabled('use_row_colors') && state.rowColors[rIdx]) {
            dayCell.style.backgroundColor = state.rowColors[rIdx];
            dayCell.style.webkitPrintColorAdjust = 'exact';
            dayCell.style.printColorAdjust = 'exact';
        }

        const dayWrap = document.createElement('div');
        dayWrap.className = 'flex flex-col items-center gap-1';
        
        const dayText = document.createElement('span');
        dayText.textContent = row.day;
        dayWrap.appendChild(dayText);

        const bulkBtn = document.createElement('button');
        bulkBtn.type = 'button';
        bulkBtn.className = 'bulk-apply-btn no-print w-7 h-7 bg-slate-500 text-white rounded-full shadow-sm hover:bg-slate-600 transition-colors flex items-center justify-center mt-1';
        bulkBtn.innerHTML = '<i data-lucide="plus" class="w-3.5 h-3.5"></i>';
        bulkBtn.title = 'تعبئة اليوم من قائمة المواد';
        bulkBtn.onclick = (event) => showBulkMaterialSelector(rIdx, event.currentTarget);
        dayWrap.appendChild(bulkBtn);

        dayCell.appendChild(dayWrap);
        tr.appendChild(dayCell);

        const dateCell = document.createElement('td');
        dateCell.className = 'p-2 border-2 border-slate-900 text-xs font-bold';
        const arabicDate = isEnabled('use_arabic_numerals');
        const dateText = arabicDate ? toArabicDigits(row.date) : row.date;
        dateCell.innerHTML = renderDateHtml(dateText, arabicDate);
        if (isEnabled('use_row_colors') && state.rowColors[rIdx]) {
            dateCell.style.backgroundColor = state.rowColors[rIdx];
            dateCell.style.webkitPrintColorAdjust = 'exact';
            dateCell.style.printColorAdjust = 'exact';
        }
        tr.appendChild(dateCell);

        row.subjects.forEach((sub, sIdx) => {
            const td = document.createElement('td');
            td.className = 'p-1 border-2 border-slate-900';
            const subjects = normalizeSubjectList(sub, true);
            state.tableRows[rIdx].subjects[sIdx] = subjects;
            if (isEnabled('use_row_colors') && state.rowColors[rIdx]) {
                td.style.backgroundColor = state.rowColors[rIdx];
                td.style.webkitPrintColorAdjust = 'exact';
                td.style.printColorAdjust = 'exact';
            }
            if (isEnabled('use_class_colors') && state.classColors[sIdx]) {
                td.style.backgroundColor = state.classColors[sIdx];
                td.style.webkitPrintColorAdjust = 'exact';
                td.style.printColorAdjust = 'exact';
            }

            const stack = document.createElement('div');
            stack.className = 'subject-stack cell-tools';

            subjects.forEach((subject, subjectIdx) => {
                stack.appendChild(createSubjectSelect(rIdx, sIdx, subjectIdx, subject));
            });

            const tools = document.createElement('div');
            tools.className = 'subject-actions';

            const addBtn = document.createElement('button');
            addBtn.type = 'button';
            addBtn.className = 'add-subject-btn';
            addBtn.innerHTML = '<i data-lucide="plus" class="w-3.5 h-3.5"></i>';
            addBtn.title = 'إضافة مادة';
            addBtn.addEventListener('click', () => addSubjectSlot(rIdx, sIdx));

            const centralBtn = document.createElement('button');
            centralBtn.type = 'button';
            centralBtn.className = 'central-subject-btn';
            centralBtn.innerHTML = '<i data-lucide="landmark" class="w-3.5 h-3.5"></i>';
            centralBtn.title = 'إضافة اختبار مركزي';
            centralBtn.addEventListener('click', () => addCentralSubjectSlot(rIdx, sIdx));

            tools.appendChild(addBtn);
            tools.appendChild(centralBtn);
            stack.appendChild(tools);

            const printSpan = document.createElement('span');
            printSpan.className = 'print-subject';
            const printSubjects = normalizeSubjectList(subjects);
            if (!printSubjects.length) {
                const emptyLine = document.createElement('span');
                emptyLine.className = 'print-subject-line';
                emptyLine.textContent = '-';
                printSpan.appendChild(emptyLine);
            } else {
                printSubjects.forEach(subject => {
                    const line = document.createElement('span');
                    line.className = 'print-subject-line';
                    if (isCentralSubject(subject)) line.classList.add('central-subject-print');
                    const icon = createMaterialIcon(subject, 'print-material-icon');
                    const text = document.createElement('span');
                    const visual = getMaterialVisual(subject);
                    text.textContent = visual.short || subject;
                    line.appendChild(icon);
                    line.appendChild(text);
                    if (isEnabled('use_material_colors')) {
                        const color = state.materialColors[state.currentStage]?.[subject];
                        if (color) {
                            line.style.backgroundColor = color;
                            line.style.webkitPrintColorAdjust = 'exact';
                            line.style.printColorAdjust = 'exact';
                        }
                    }
                    printSpan.appendChild(line);
                });
            }

            td.appendChild(stack);
            td.appendChild(printSpan);
            tr.appendChild(td);
        });
        body.appendChild(tr);
    });
}

function renderTableListMode(head, body) {
    const headerRow = document.createElement('tr');
    ['اليوم', 'التاريخ', 'الصفوف', 'نوع الاختبار', 'المادة'].forEach(label => {
        const th = document.createElement('th');
        th.className = 'p-3 border-2 border-slate-900';
        th.textContent = label;
        headerRow.appendChild(th);
    });
    head.appendChild(headerRow);

    state.tableRows.forEach((row, rIdx) => {
        const tr = document.createElement('tr');
        tr.className = rIdx % 2 === 0 ? 'bg-white' : 'bg-emerald-50/20';

        const dayCell = createBasicCell(row.day, 'font-black text-sm');

        const arabicDate = isEnabled('use_arabic_numerals');
        const dateText = arabicDate ? toArabicDigits(row.date) : row.date;
        const dateCell = document.createElement('td');
        dateCell.className = 'p-2 border-2 border-slate-900 text-xs font-bold';
        dateCell.innerHTML = renderDateHtml(dateText, arabicDate);

        const classesCell = createInputCell(rIdx, 'classes', 'أدخل الصفوف...');
        const typeCell = createListTypeCell(rIdx);
        const materialCell = createListMaterialCell(rIdx);

        tr.appendChild(dayCell);
        tr.appendChild(dateCell);
        tr.appendChild(classesCell);
        tr.appendChild(typeCell);
        tr.appendChild(materialCell);
        body.appendChild(tr);
    });
}

function createListTypeCell(rowIndex) {
    const td = document.createElement('td');
    td.className = 'p-1 border-2 border-slate-900';

    const select = document.createElement('select');
    select.className = 'list-mode-input cell-tools';

    const options = ['تكويني', 'اختبار الفترة', 'تكويني - فتري', 'نهائي'];
    options.forEach(optVal => {
        const opt = document.createElement('option');
        opt.value = optVal;
        opt.textContent = optVal;
        opt.selected = optVal === state.tableRows[rowIndex].test_type;
        select.appendChild(opt);
    });

    select.addEventListener('change', () => {
        state.tableRows[rowIndex].test_type = select.value;
        queueSave();
        byId(`print_test_type_${rowIndex}`).textContent = select.value;
    });

    const printText = document.createElement('span');
    printText.id = `print_test_type_${rowIndex}`;
    printText.className = 'print-list-text';
    printText.textContent = state.tableRows[rowIndex].test_type || '-';

    td.appendChild(select);
    td.appendChild(printText);
    return td;
}

function createBasicCell(text, className) {
    const td = document.createElement('td');
    td.className = `p-2 border-2 border-slate-900 ${className}`;
    td.textContent = text;
    return td;
}

function createInputCell(rowIndex, field, placeholder) {
    const td = document.createElement('td');
    td.className = 'p-1 border-2 border-slate-900';

    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'list-mode-input';
    input.placeholder = placeholder;
    input.value = state.tableRows[rowIndex][field] || '';
    input.addEventListener('input', () => {
        state.tableRows[rowIndex][field] = input.value;
        queueSave();
        byId(`print_${field}_${rowIndex}`).textContent = input.value;
    });

    const printText = document.createElement('span');
    printText.id = `print_${field}_${rowIndex}`;
    printText.className = 'print-list-text';
    printText.textContent = input.value || '-';

    td.appendChild(input);
    td.appendChild(printText);
    return td;
}

function createListMaterialCell(rowIndex) {
    const td = document.createElement('td');
    td.className = 'p-1 border-2 border-slate-900';

    const select = document.createElement('select');
    select.className = 'list-mode-input cell-tools';

    const empty = document.createElement('option');
    empty.value = '';
    empty.textContent = '- اختر المادة -';
    select.appendChild(empty);

    state.materials[state.currentStage].forEach(material => {
        const opt = document.createElement('option');
        opt.value = material;
        opt.textContent = material;
        opt.selected = material === state.tableRows[rowIndex].material;
        select.appendChild(opt);
    });

    [CENTRAL_SUBJECT, HOLIDAY_SUBJECT, REST_SUBJECT].forEach(material => {
        const opt = document.createElement('option');
        opt.value = material;
        opt.textContent = material;
        opt.selected = material === state.tableRows[rowIndex].material;
        select.appendChild(opt);
    });

    select.addEventListener('change', () => {
        state.tableRows[rowIndex].material = select.value;
        queueSave();
        const printEl = byId(`print_material_${rowIndex}`);
        printEl.textContent = select.value || '-';
        printEl.classList.toggle('central-subject-print', isCentralSubject(select.value));
    });

    const printText = document.createElement('span');
    printText.id = `print_material_${rowIndex}`;
    printText.className = 'print-list-text';
    if (isCentralSubject(state.tableRows[rowIndex].material)) printText.classList.add('central-subject-print');
    printText.textContent = state.tableRows[rowIndex].material || '-';

    td.appendChild(select);
    td.appendChild(printText);
    return td;
}

function createSubjectSelect(rowIndex, classIndex, subjectIndex, currentValue) {
    const row = document.createElement('div');
    row.className = 'subject-row';
    if (isCentralSubject(currentValue)) row.classList.add('central-subject-row');

    const iconSlot = document.createElement('span');
    iconSlot.className = 'subject-icon-slot';
    if (currentValue) {
        iconSlot.appendChild(createMaterialIcon(currentValue));
    }

    const select = document.createElement('select');
    select.className = 'subject-select';
    if (currentValue && isEnabled('use_material_colors')) {
        const materialColor = state.materialColors[state.currentStage]?.[currentValue];
        if (materialColor) select.style.backgroundColor = materialColor;
    }
    select.addEventListener('change', () => {
        const subjects = normalizeSubjectList(state.tableRows[rowIndex].subjects[classIndex], true);
        if (select.value) {
            subjects[subjectIndex] = select.value;
        } else {
            subjects.splice(subjectIndex, 1);
        }
        state.tableRows[rowIndex].subjects[classIndex] = subjects.filter(Boolean);
        renderTable();
        queueSave();
    });

    const empty = document.createElement('option');
    empty.value = '';
    empty.textContent = '-';
    select.appendChild(empty);

    state.materials[state.currentStage].forEach(material => {
        const option = document.createElement('option');
        option.value = material;
        option.textContent = material;
        option.selected = material === currentValue;
        select.appendChild(option);
    });

    const central = document.createElement('option');
    central.value = CENTRAL_SUBJECT;
    central.textContent = CENTRAL_SUBJECT;
    central.selected = currentValue === CENTRAL_SUBJECT;
    select.appendChild(central);

    const holiday = document.createElement('option');
    holiday.value = HOLIDAY_SUBJECT;
    holiday.textContent = HOLIDAY_SUBJECT;
    holiday.selected = currentValue === HOLIDAY_SUBJECT;
    select.appendChild(holiday);

    const rest = document.createElement('option');
    rest.value = REST_SUBJECT;
    rest.textContent = REST_SUBJECT;
    rest.selected = currentValue === REST_SUBJECT;
    select.appendChild(rest);

    const deleteBtn = document.createElement('button');
    deleteBtn.type = 'button';
    deleteBtn.className = 'delete-subject-btn cell-tools';
    deleteBtn.title = 'حذف هذه المادة من اليوم';
    deleteBtn.innerHTML = '<i data-lucide="x" class="w-3.5 h-3.5"></i>';
    deleteBtn.addEventListener('click', () => deleteSubjectSlot(rowIndex, classIndex, subjectIndex));

    row.appendChild(deleteBtn);
    row.appendChild(select);
    row.appendChild(iconSlot);
    return row;
}

function addSubjectSlot(rowIndex, classIndex) {
    const subjects = normalizeSubjectList(state.tableRows[rowIndex].subjects[classIndex], true);
    subjects.push('');
    state.tableRows[rowIndex].subjects[classIndex] = subjects;
    renderTable();
    queueSave();
}

function addCentralSubjectSlot(rowIndex, classIndex) {
    const subjects = normalizeSubjectList(state.tableRows[rowIndex].subjects[classIndex], true);
    if (!subjects.includes(CENTRAL_SUBJECT)) subjects.push(CENTRAL_SUBJECT);
    state.tableRows[rowIndex].subjects[classIndex] = subjects;
    renderTable();
    queueSave();
}

function applyHolidayToRow(rowIndex) {
    if (!state.tableRows[rowIndex]) return;
    state.tableRows[rowIndex].subjects = state.classNames.map(() => [HOLIDAY_SUBJECT]);
    renderTable();
    queueSave();
    showToast('تم تعبئة اليوم بإجازة');
}

function applyHolidayToMinisterialRow(rowIndex, rows) {
    const row = rows?.[rowIndex];
    if (!row) return;
    row.material = HOLIDAY_SUBJECT;
    row.test_type = HOLIDAY_SUBJECT;
    renderTable();
    queueSave();
    showToast('تم تعبئة اليوم بإجازة');
}

function deleteSubjectSlot(rowIndex, classIndex, subjectIndex) {
    const subjects = normalizeSubjectList(state.tableRows[rowIndex].subjects[classIndex], true);
    subjects.splice(subjectIndex, 1);
    state.tableRows[rowIndex].subjects[classIndex] = subjects;
    renderTable();
    queueSave();
}

function showBulkMaterialSelector(rowIndex, btnEl, isMinisterial = false, weekRows = null) {
    const materials = state.materials[state.currentStage];
    
    // Remove any existing menu
    const oldMenu = document.getElementById('bulk-material-menu');
    if (oldMenu) oldMenu.remove();

    const menu = document.createElement('div');
    menu.id = 'bulk-material-menu';
    menu.className = 'absolute z-[999] bg-white border border-slate-200 shadow-2xl rounded-xl p-3 flex flex-col gap-2 min-w-[180px] animate-in fade-in zoom-in duration-200';
    
    const rect = btnEl.getBoundingClientRect();
    let top = rect.bottom + window.scrollY + 5;
    let left = rect.left + window.scrollX;

    // Viewport boundary checks
    const menuWidth = 180;
    if (left + menuWidth > window.innerWidth) {
        left = window.innerWidth - menuWidth - 15;
    }
    if (left < 15) left = 15;

    menu.style.top = `${top}px`;
    menu.style.left = `${left}px`;
    menu.style.maxHeight = '300px'; // Support long lists on mobile
    menu.style.overflowY = 'auto';
    menu.style.scrollbarWidth = 'none'; // Hide scrollbar for cleaner look

    const title = document.createElement('div');
    title.className = 'text-[11px] font-black text-slate-400 mb-1 border-b pb-1 text-center';
    title.textContent = 'اختر المادة للكل';
    menu.appendChild(title);

    // Option: Clear
    const clearBtn = document.createElement('button');
    clearBtn.className = 'text-[12px] font-bold text-red-600 p-2 hover:bg-red-50 rounded text-right flex items-center gap-2';
    clearBtn.innerHTML = '<i data-lucide="eraser" class="w-4 h-4"></i> مسح الكل';
    clearBtn.onclick = (e) => {
        e.stopPropagation();
            if (isMinisterial && weekRows) {
                const row = weekRows[rowIndex];
                if (row) {
                    row.material = '';
                    row.test_type = (row.test_type === HOLIDAY_SUBJECT || row.test_type === REST_SUBJECT) ? '' : row.test_type;
                }
            } else {
                state.tableRows[rowIndex].subjects = state.classNames.map(() => []);
            }
        finishBulkApply(menu);
    };
    menu.appendChild(clearBtn);

    const menuItems = [
        { name: HOLIDAY_SUBJECT, icon: 'coffee', color: '#64748b', className: 'hover:bg-slate-50 hover:text-slate-700' },
        { name: REST_SUBJECT, icon: 'armchair', color: '#475569', className: 'hover:bg-slate-50 hover:text-slate-700' },
        { name: CENTRAL_SUBJECT, icon: 'landmark', color: '#d97706', className: 'hover:bg-amber-50 hover:text-amber-700' },
        ...materials.map(name => ({
            name,
            icon: '',
            color: state.materialColors[state.currentStage]?.[name] || '#10b981',
            className: 'hover:bg-emerald-50 hover:text-emerald-700'
        }))
    ];

    // List materials and special day values.
    menuItems.forEach(menuItem => {
        const m = menuItem.name;
        const itemBtn = document.createElement('button');
        itemBtn.className = `text-[12px] font-bold text-slate-700 p-2 rounded text-right flex items-center gap-2 transition-colors ${menuItem.className}`;
        const visual = menuItem.icon
            ? `<i data-lucide="${menuItem.icon}" class="w-4 h-4" style="color: ${menuItem.color}"></i>`
            : `<span class="w-3 h-3 rounded-full" style="background-color: ${menuItem.color}"></span>`;
        itemBtn.innerHTML = `${visual} ${m}`;
        itemBtn.onclick = (e) => {
            e.stopPropagation();
            if (isMinisterial && weekRows) {
                const row = weekRows[rowIndex];
                if (row) {
                    row.material = m;
                    if (m === HOLIDAY_SUBJECT || m === REST_SUBJECT) {
                        row.test_type = m;
                    } else if (row.test_type === HOLIDAY_SUBJECT || row.test_type === REST_SUBJECT) {
                        row.test_type = 'تكويني';
                    }
                }
            } else {
                state.tableRows[rowIndex].subjects = state.classNames.map(() => [m]);
            }
            finishBulkApply(menu);
        };
        menu.appendChild(itemBtn);
    });

    document.body.appendChild(menu);
    if (window.lucide) lucide.createIcons();

    // Close on outside click - increased timeout for mobile
    const closer = (e) => {
        if (!menu.contains(e.target) && !btnEl.contains(e.target)) {
            menu.remove();
            document.removeEventListener('click', closer);
            document.removeEventListener('touchstart', closer);
        }
    };
    setTimeout(() => {
        document.addEventListener('click', closer);
        document.addEventListener('touchstart', closer);
    }, 300);
}

function finishBulkApply(menu) {
    menu.remove();
    renderTable();
    queueSave();
    showToast('تم تحديث الصف بالكامل');
}

function resetScheduleOnly() {
    if (!confirm('هل تريد تفريغ مواد الجدول مع بقاء التواريخ والإعدادات؟')) return;
    state.tableRows.forEach(row => {
        row.subjects = Array.from({ length: state.classNames.length }, () => []);
    });
    renderTable();
    queueSave();
    showToast('تم تفريغ الجدول');
}

function restoreDefaults() {
    if (!confirm('سيتم حذف كل التعديلات المحفوظة واستعادة الإعدادات الافتراضية. هل أنت متأكد؟')) return;
    localStorage.removeItem(STORAGE_KEY);
    state = deepClone(defaultState);
    applyStateToInputs();
    initTable();
    renderClassEditor();
    renderMaterialsBank();
    renderInstructionsEditor();
    renderInstructionsDisplay();
    renderRowColorsEditor();
    updateAll();
    saveState(false);
    showToast('تمت استعادة الإعدادات الافتراضية');
}

function updatePrintStyle() {
    const orientation = state.fields.print_orientation === 'portrait' ? 'portrait' : 'landscape';
    const style = document.getElementById('dynamic_print_style') || document.createElement('style');
    style.id = 'dynamic_print_style';
    const pageSize = orientation === 'landscape' ? 'A4 landscape' : 'A4 portrait';
    style.textContent = `@page { size: ${pageSize}; margin: 4mm; }
@media print { body { overflow: visible !important; } }`;
    if (!style.parentNode) document.head.appendChild(style);
}

function autoFitPrint(forcedWidth) {
    const root = document.querySelector(".print-root");
    if (!root) return;
    root.classList.remove('compact-mode', 'dense-mode');
    root.style.transform = 'none';
    root.style.width = forcedWidth ? (forcedWidth + 'px') : '100%';
}

function fitPdfToOnePage(root, orientation, targetWidth) {
    if (!root) return 1;
    const pageHeightPx = orientation === 'portrait' ? 1123 : 794;
    const safeHeightPx = pageHeightPx - 36;

    root.style.zoom = '';
    root.style.width = `${targetWidth}px`;
    root.style.maxWidth = 'none';
    root.style.height = 'auto';
    root.style.minHeight = '0';
    root.getBoundingClientRect();

    const contentHeight = Math.max(root.scrollHeight, root.getBoundingClientRect().height);
    const scale = Math.max(0.72, Math.min(1, safeHeightPx / Math.max(1, contentHeight)));

    if (scale < 1) {
        root.style.width = `${Math.ceil(targetWidth / scale)}px`;
        root.style.zoom = String(scale);
    }

    return scale;
}

function fitPreviewToViewport() {
    const printArea = byId('printArea');
    const root = document.querySelector('.print-root');
    const previewTab = byId('preview-tab');
    if (!printArea || !root || !previewTab) return;

    if (document.body.classList.contains('is-printing') || window.matchMedia('print').matches) {
        root.style.transform = '';
        root.style.width = '';
        root.style.maxWidth = '';
        printArea.style.height = '';
        printArea.style.overflow = '';
        return;
    }

    if (!previewTab.classList.contains('active')) {
        root.style.transform = '';
        root.style.width = '';
        root.style.maxWidth = '';
        printArea.style.height = '';
        printArea.style.overflow = '';
        return;
    }

    const baseWidth = state.fields.print_orientation === 'portrait' ? 794 : 1123;
    const availableWidth = Math.max(320, (printArea.clientWidth || previewTab.clientWidth || baseWidth) - 16);
    const scale = Math.min(1, availableWidth / baseWidth);

    root.style.width = `${baseWidth}px`;
    root.style.maxWidth = 'none';
    root.style.transformOrigin = 'top center';
    root.style.transform = scale < 1 ? `scale(${scale})` : 'none';
    printArea.style.overflow = 'hidden';
    printArea.style.height = `${Math.ceil(root.scrollHeight * scale)}px`;
}

function printSchedule() {
    updateAll();
    saveState(false);
    document.body.classList.add('is-printing');
    window.print();
}

function isMobile() {
    return /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent);
}

function printOrExportPDF() {
    updateAll();
    updatePrintStyle();
    saveState(false);

    if (typeof html2pdf !== 'undefined') {
        const orientation = state.fields.print_orientation === 'portrait' ? 'portrait' : 'landscape';
        // A4 at 96 DPI: portrait=794px, landscape=1123px
        const targetWidth = orientation === 'portrait' ? 794 : 1123;

        _enterPrintMode(targetWidth);
        autoFitPrint(targetWidth);

        const el = document.querySelector('.print-root') || byId('printArea');
        const school = (state.fields.school_name_input || 'jadwal').replace(/[^\u0600-\u06FF\w-]+/g, '-');

        const opt = {
            margin: [4, 4, 4, 4],
            filename: `${school}-${new Date().toLocaleDateString('ar-SA').replace(/\//g, '-')}.pdf`,
            image: { type: 'jpeg', quality: 0.98 },
            html2canvas: {
                scale: 2,
                useCORS: true,
                logging: false,
                allowTaint: true,
                letterRendering: true,
                width: targetWidth,
                windowWidth: targetWidth,
                scrollX: 0,
                scrollY: 0,
                x: 0
            },
            jsPDF: {
                unit: 'mm',
                format: 'a4',
                orientation: orientation,
                compress: true
            },
            pagebreak: { mode: [] }
        };

        showToast('جاري تجهيز ملف PDF...');
        const waitForFonts = document.fonts?.ready || Promise.resolve();
        waitForFonts.then(() => setTimeout(() => {
            const fitScale = fitPdfToOnePage(el, orientation, targetWidth);
            opt.html2canvas.windowWidth = Math.ceil(targetWidth / fitScale);
            html2pdf().set(opt).from(el).save().then(() => {
                _exitPrintMode();
                showToast('تم تصدير ملف PDF بنجاح ✅');
            }).catch(err => {
                console.error('PDF Export Error:', err);
                _exitPrintMode();
                window.print();
            });
        }, 250));
    } else {
        window.print();
    }
}

function _enterPrintMode(targetWidth) {
    document.body.classList.add('is-printing');
    const el = byId('printArea');
    if (el && targetWidth) {
        el.style.width = targetWidth + 'px';
        el.style.margin = '0';
        el.style.maxWidth = 'none';
        el.style.minHeight = '0';
        el.style.height = 'auto';
    }
    const root = document.querySelector('.print-root');
    if (root) {
        root.style.width = targetWidth ? `${targetWidth}px` : '100%';
        root.style.maxWidth = 'none';
        root.style.minHeight = '0';
        root.style.height = 'auto';
        root.style.transform = 'none';
        root.style.zoom = '';
    }
}

function _exitPrintMode() {
    document.body.classList.remove('is-printing');
    const root = document.querySelector('.print-root');
    if (root) {
        root.classList.remove('compact-mode', 'dense-mode');
        root.style.transform = '';
        root.style.width = '';
        root.style.minHeight = '';
        root.style.height = '';
        root.style.zoom = '';
    }
    const el = byId('printArea');
    if (el) {
        el.style.width = '';
        el.style.margin = '';
        el.style.maxWidth = '';
        el.style.minHeight = '';
        el.style.height = '';
        el.style.border = '';
        el.style.boxShadow = '';
        el.style.borderRadius = '';
    }
    updateAll();
}



function stepNumber(id, delta) {
    const input = byId(id);
    if (!input) return;
    const min = parseInt(input.min, 10);
    const max = parseInt(input.max, 10);
    let val = parseInt(input.value, 10);
    if (isNaN(val)) val = parseInt(input.min, 10) || 0;
    val = Math.min(Math.max(val + delta, isNaN(min) ? -Infinity : min), isNaN(max) ? Infinity : max);
    input.value = val;
    // تشغيل حدث التغيير
    input.dispatchEvent(new Event('input', { bubbles: true }));
}

function shareWhatsApp() {
    const school = state.fields.school_name_input;
    const title = state.fields.main_title_input;
    const isArabic = isEnabled('use_arabic_numerals');
    const classWidth = Math.max(10, ...state.classNames.map(name => name.length));
    let msg = `📝 *${isArabic ? toArabicDigits(title) : title}*\n🏫 *${school}*\n\n`;

    const isMinisterial = state.fields.table_mode === 'ministerial';

    const renderTableToWhatsApp = (tableRows, weekTitle) => {
        if (!tableRows || !tableRows.length) return;
        if (weekTitle) {
            msg += `\n📅 *${weekTitle}*\n`;
        }
        tableRows.forEach(row => {
            msg += `━━━━━━━━━━━━━━\n`;
            msg += `📅 *اليوم:* ${row.day}\n`;
            msg += `🗓️ *التاريخ:* ${isArabic ? toArabicDigits(row.date) : row.date}\n\n`;

            if (isMinisterial) {
                if (row.material) {
                    const materialVisual = getMaterialVisual(row.material);
                    msg += `🏷️ ${row.classes || stageClassesText[state.currentStage] || ''} : ${materialVisual.emoji} ${row.material} (${row.test_type || ''})\n`;
                }
            } else {
                row.subjects.forEach((subject, i) => {
                    const subjects = normalizeSubjectList(subject);
                    if (!subjects.length) return;
                    const className = padArabic(state.classNames[i], classWidth);
                    const subjectsText = subjects.map(item => `${getMaterialVisual(item).emoji} ${item}`).join('  |  ');
                    msg += `🏷️ ${className} : ${subjectsText}\n`;
                });
            }
            msg += '\n';
        });
    };

    renderTableToWhatsApp(state.tableRows, isEnabled('show_week_box') ? (isEnabled('use_arabic_numerals') ? toArabicDigits(state.fields.week_number) : state.fields.week_number) : '');

    if (isEnabled('week2_enabled')) {
        renderTableToWhatsApp(state.tableRows2, isEnabled('show_week_box') ? (isEnabled('use_arabic_numerals') ? toArabicDigits(state.fields.week2_number) : state.fields.week2_number) : '');
    }

    msg += '━━━━━━━━━━━━━━\n';
    msg += '✨ _إعداد: ناصر آل مستنير_';
    window.open(`https://wa.me/?text=${encodeURIComponent(msg)}`, '_blank');
}

function boot() {
    loadState();
    attachInputs();
    refreshAppFromState();

    // Update footer with Arabic digits if enabled
    if (isEnabled('use_arabic_numerals')) {
        const footer = document.querySelector('div.fixed.bottom-0');
        if (footer) footer.textContent = toArabicDigits(footer.textContent);
    }

    window.addEventListener('beforeprint', () => {
        document.body.classList.add('is-printing');
        updateAll();
        updatePrintStyle();
        autoFitPrint();
    });

    window.addEventListener('afterprint', () => {
        document.body.classList.remove('is-printing');
        fitPreviewToViewport();
    });

    /* fallback للأندرويد و iOS */
    window.matchMedia("print").addEventListener("change", function (e) {
        if (e.matches) {
            document.body.classList.add('is-printing');
            updateAll();
            updatePrintStyle();
            autoFitPrint();
        } else {
            document.body.classList.remove('is-printing');
            fitPreviewToViewport();
        }
    });

    window.addEventListener('resize', () => {
        if (previewFitTimer) window.clearTimeout(previewFitTimer);
        previewFitTimer = window.setTimeout(fitPreviewToViewport, 100);
    });
}

boot();
