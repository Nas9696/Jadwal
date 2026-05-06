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
    'إجازة': { emoji: '☕', icon: 'coffee', color: '#64748b' }
};
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
        early_childhood: ['إسلامية', 'لغتي', 'رياضيات', 'علوم', 'إنجليزي', 'فنية', 'م. حياتية', 'بدنية', 'نشاط'],
        elementary: ['اجتماعيات', 'فنية', 'إسلامية', 'بدنية', 'م. حياتية', 'رقمية', 'رياضيات', 'إنجليزي', 'علوم', 'لغتي'],
        intermediate: ['اجتماعيات', 'إسلامية', 'بدنية', 'فنية', 'م. حياتية', 'رياضيات', 'رقمية', 'إنجليزي', 'تفكير ناقد', 'لغتي', 'علوم'],
        secondary: ['فيزياء', 'رياضيات', 'كفايات', 'علم البيئة', 'إنجليزي', 'تقنية رقمية', 'اجتماعيات', 'معرفة مالية', 'بدنية', 'تربية مهنية', 'نشاط', 'لياقة وثقافة', 'فنون', 'م. حياتية', 'مواطنة رقمية', 'دراسات أدبية', 'إسلامية', 'علم نفس', 'أحياء', 'جغرافيا', 'علم الأرض', 'كيمياء']
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
        week2_start_month: '11'
    }
};

let state = deepClone(defaultState);
let saveTimer = null;

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
    const n = parseInt(value, 10);
    if (Number.isNaN(n)) return fallback;
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

function createMaterialIcon(subject, extraClass = '') {
    const visual = getMaterialVisual(subject);
    const icon = document.createElement('span');
    icon.className = `material-icon ${extraClass}`.trim();
    icon.style.color = visual.color;
    icon.innerHTML = `<i data-lucide="${visual.icon}" class="w-4 h-4"></i>`;
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
        if(input.value) input.value = toArabicDigits(input.value);
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
                updateAll();
                queueSave();
            });
            return;
        }
        const eventType = (el.tagName === 'SELECT' || el.type === 'checkbox') ? 'change' : 'input';
        el.addEventListener(eventType, () => {
            state.fields[id] = el.value;
            if (id === 'logo_url_input') state.fields.logo_data_url = '';
            if (['days_count', 'start_day', 'start_month', 'week2_days_count', 'week2_start_day', 'week2_start_month'].includes(id)) {
                normalizeDateInputs();
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

function normalizeDateInputs() {
    state.fields.days_count = String(clampNumber(parseArabicNum(byId('days_count').value), 1, 12, 5));
    state.fields.start_day = String(clampNumber(parseArabicNum(byId('start_day').value), 1, 30, 1));
    state.fields.start_month = String(clampNumber(parseArabicNum(byId('start_month').value), 1, 12, 1));
    byId('days_count').value = toArabicDigits(state.fields.days_count);
    byId('start_day').value = toArabicDigits(state.fields.start_day);
    byId('start_month').value = toArabicDigits(state.fields.start_month);

    if (byId('week2_days_count')) {
        state.fields.week2_days_count = String(clampNumber(parseArabicNum(byId('week2_days_count').value), 1, 12, 5));
        state.fields.week2_start_day = String(clampNumber(parseArabicNum(byId('week2_start_day').value), 1, 30, 1));
        state.fields.week2_start_month = String(clampNumber(parseArabicNum(byId('week2_start_month').value), 1, 12, 1));
        byId('week2_days_count').value = toArabicDigits(state.fields.week2_days_count);
        byId('week2_start_day').value = toArabicDigits(state.fields.week2_start_day);
        byId('week2_start_month').value = toArabicDigits(state.fields.week2_start_month);
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
        merged.materials[stage] = [...new Set(merged.materials[stage])];
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
}

function renderTablesContainer() {
    const container = byId('tables_container');
    if (!container) return;
    container.innerHTML = '';

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
                sep.className = 'my-8';
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
        tableWrap.className = 'w-full overflow-x-auto print:overflow-visible pb-4 hide-scrollbar';
        const table = document.createElement('table');
        table.className = 'schedule-table w-full border-collapse border-2 border-slate-900 text-center min-w-[700px] print:min-w-0 md:min-w-full';
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
    wrapper.className = 'w-full overflow-x-auto print:overflow-visible pb-4 hide-scrollbar';
    const table = document.createElement('table');
    table.className = 'schedule-table w-full border-collapse border-2 border-slate-900 text-center min-w-[650px] print:min-w-0 md:min-w-full';

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
        dayTd.textContent = row.day;
        tr.appendChild(dayTd);

        const dateTd = document.createElement('td');
        dateTd.className = 'p-2 border border-slate-900 text-xs font-bold';
        dateTd.textContent = isEnabled('use_arabic_numerals') ? toArabicDigits(row.date) : row.date;
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
        ['تكويني', 'اختبار الفترة', 'تكويني -فتري', 'تكويني- فتري', 'نهائي'].forEach(v => {
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
        matTd.className = 'p-1 border border-slate-900';
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
        matSelect.addEventListener('change', () => {
            row.material = matSelect.value;
            matPrint.textContent = matSelect.value || '-';
            queueSave();
        });
        const matPrint = document.createElement('span');
        matPrint.className = 'print-list-text font-black text-sm';
        matPrint.style.color = '#000';
        matPrint.textContent = row.material || '-';
        if (row.material) {
            const matColors = ['#e8f5e9', '#e3f2fd', '#fff3e0', '#fce4ec', '#f3e5f5', '#e0f7fa', '#fff8e1', '#f1f8e9', '#e8eaf6'];
            const matIdx = state.materials[state.currentStage].indexOf(row.material);
            if (matIdx >= 0) matTd.style.backgroundColor = matColors[matIdx % matColors.length];
        }
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
    if (tab === 'preview') updateAll();
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
    const startIdx = Math.max(0, daysSequence.indexOf(startDayName));
    const classesDefault = (stageClassesText[state.currentStage] || [])[0] || '';

    const rows = [];
    let currentD = startDay;
    let currentM = startMonth;

    for (let i = 0; i < count; i++) {
        const oldRow = oldRows[i] || {};
        rows.push({
            day: daysSequence[(startIdx + i) % 5],
            date: `${String(currentD).padStart(2, '0')} / ${String(currentM).padStart(2, '0')} / 1447`,
            subjects: Array.from({ length: state.classNames.length }, (_, idx) => normalizeSubjectList(oldRow.subjects?.[idx], true)),
            classes: oldRow.classes || classesDefault,
            test_type: oldRow.test_type || 'تكويني',
            material: oldRow.material || ''
        });
        currentD += (daysSequence[(startIdx + i) % 5] === 'الخميس') ? 3 : 1;
        if (currentD > 30) { currentD -= 30; currentM++; if (currentM > 12) currentM = 1; }
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
        dayCell.textContent = row.day;
        if (isEnabled('use_row_colors') && state.rowColors[rIdx]) {
            dayCell.style.backgroundColor = state.rowColors[rIdx];
            dayCell.style.webkitPrintColorAdjust = 'exact';
            dayCell.style.printColorAdjust = 'exact';
        }
        tr.appendChild(dayCell);

        const dateCell = document.createElement('td');
        dateCell.className = 'p-2 border-2 border-slate-900 text-xs font-bold';
        const dateText = isEnabled('use_arabic_numerals') ? toArabicDigits(row.date) : row.date;
        dateCell.innerHTML = `<span dir="ltr">${dateText}</span>`;
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

            const addBtn = document.createElement('button');
            addBtn.type = 'button';
            addBtn.className = 'add-subject-btn';
            addBtn.innerHTML = '<i data-lucide="plus" class="w-3.5 h-3.5"></i><span>إضافة مادة</span>';
            addBtn.addEventListener('click', () => addSubjectSlot(rIdx, sIdx));
            stack.appendChild(addBtn);

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

        const dateText = isEnabled('use_arabic_numerals') ? toArabicDigits(row.date) : row.date;
        const dateCell = document.createElement('td');
        dateCell.className = 'p-2 border-2 border-slate-900 text-xs font-bold';
        dateCell.innerHTML = `<span dir="ltr">${dateText}</span>`;

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

    select.addEventListener('change', () => {
        state.tableRows[rowIndex].material = select.value;
        queueSave();
        byId(`print_material_${rowIndex}`).textContent = select.value || '-';
    });

    const printText = document.createElement('span');
    printText.id = `print_material_${rowIndex}`;
    printText.className = 'print-list-text';
    printText.textContent = state.tableRows[rowIndex].material || '-';

    td.appendChild(select);
    td.appendChild(printText);
    return td;
}

function createSubjectSelect(rowIndex, classIndex, subjectIndex, currentValue) {
    const row = document.createElement('div');
    row.className = 'subject-row';

    const iconSlot = document.createElement('span');
    iconSlot.className = 'subject-icon-slot';
    if (currentValue) {
        iconSlot.appendChild(createMaterialIcon(currentValue));
    }

    const select = document.createElement('select');
    select.className = 'subject-select min-w-0 flex-1 bg-white/70 border border-emerald-100 rounded font-black cursor-pointer outline-none';
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

    const holiday = document.createElement('option');
    holiday.value = 'إجازة';
    holiday.textContent = 'إجازة';
    holiday.selected = currentValue === 'إجازة';
    select.appendChild(holiday);

    const deleteBtn = document.createElement('button');
    deleteBtn.type = 'button';
    deleteBtn.className = 'icon-btn text-red-600 hover:bg-red-50 border border-red-100 cell-tools flex-shrink-0';
    deleteBtn.title = 'حذف هذه المادة من اليوم';
    deleteBtn.innerHTML = '<i data-lucide="x" class="w-3.5 h-3.5"></i>';
    deleteBtn.addEventListener('click', () => deleteSubjectSlot(rowIndex, classIndex, subjectIndex));

    row.appendChild(iconSlot);
    row.appendChild(select);
    row.appendChild(deleteBtn);
    return row;
}

function addSubjectSlot(rowIndex, classIndex) {
    const subjects = normalizeSubjectList(state.tableRows[rowIndex].subjects[classIndex], true);
    subjects.push('');
    state.tableRows[rowIndex].subjects[classIndex] = subjects;
    renderTable();
    queueSave();
}

function deleteSubjectSlot(rowIndex, classIndex, subjectIndex) {
    const subjects = normalizeSubjectList(state.tableRows[rowIndex].subjects[classIndex], true);
    subjects.splice(subjectIndex, 1);
    state.tableRows[rowIndex].subjects[classIndex] = subjects;
    renderTable();
    queueSave();
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
    const oldStyle = byId('dynamic_print_style');
    if (oldStyle) oldStyle.remove();

    const orientation = state.fields.print_orientation === 'portrait' ? 'portrait' : 'landscape';
    const cols = state.classNames.length + 2;
    const maxSubjects = Math.max(
        1,
        ...state.tableRows.flatMap(row => row.subjects.map(subjects => normalizeSubjectList(subjects).length || 1))
    );
    const baseFont = orientation === 'landscape' ? 9.2 : 8.3;
    const fontSize = Math.max(5.6, baseFont - Math.max(0, cols - 5) * 0.45 - Math.max(0, maxSubjects - 2) * 0.35);
    const padding = Math.max(1.8, 5 - Math.max(0, cols - 5) * 0.45 - Math.max(0, maxSubjects - 2) * 0.35);
    const headerFont = Math.max(7, fontSize + 0.8);
    const titleFont = Math.max(11, fontSize + 4.5);
    const footerMargin = orientation === 'landscape' ? 12 : 16;

    document.documentElement.style.setProperty('--print-font-size', `${fontSize.toFixed(1)}pt`);
    // Auto-shrink padding and font size if many rows to fit A4
    const rowCount = state.tableRows.length + (isEnabled('week2_enabled') ? state.tableRows2.length : 0);
    if (rowCount > 8) {
        padding = Math.max(1.5, padding - 1.5);
        headerFont = Math.max(7, headerFont - 1);
        titleFont = Math.max(12, titleFont - 2);
    } else if (rowCount > 5) {
        padding = Math.max(2.5, padding - 1);
    }

    document.documentElement.style.setProperty('--print-cell-padding', `${padding.toFixed(1)}px`);
    document.documentElement.style.setProperty('--print-header-font-size', `${headerFont.toFixed(1)}pt`);
    document.documentElement.style.setProperty('--print-title-font-size', `${titleFont.toFixed(1)}pt`);
    document.documentElement.style.setProperty('--print-footer-margin', `${footerMargin}px`);

    const style = document.createElement('style');
    style.id = 'dynamic_print_style';
    const pageSize = orientation === 'landscape' ? '297mm 210mm' : '210mm 297mm';
    const previewWidth = orientation === 'landscape' ? '297mm' : '210mm';
    const previewMinHeight = orientation === 'landscape' ? '210mm' : '297mm';
    style.textContent = `
                @page { size: ${pageSize}; margin: ${orientation === 'landscape' ? '5mm' : '6mm'}; }
                #printArea {
                    width: ${previewWidth};
                    max-width: 100%;
                    min-height: ${previewMinHeight};
                }
                .schedule-table th, .schedule-table td { padding: var(--print-cell-padding, 4px) !important; }
                @media print {
                    html, body, #printArea, .print-container {
                        writing-mode: horizontal-tb !important;
                        transform: none !important;
                        rotate: 0deg !important;
                        height: auto !important;
                    }
                    .print-container {
                        width: 100% !important;
                        max-width: 100% !important;
                        min-height: 0 !important;
                        height: auto !important;
                    }
                    .schedule-table th:first-child, .schedule-table td:first-child { width: ${orientation === 'landscape' ? '58px' : '44px'} !important; }
                    .schedule-table th:nth-child(2), .schedule-table td:nth-child(2) { width: ${orientation === 'landscape' ? '82px' : '66px'} !important; }
                    .schedule-table { min-width: 0 !important; border-collapse: collapse !important; }
                    @supports (size: 297mm 210mm) {
                        html, body { width: auto !important; height: auto !important; }
                    }
                }
            `;
    document.head.appendChild(style);
}

function printSchedule() {
    updateAll();
    updatePrintStyle();
    saveState(false);
    window.print();
}

function isMobile() {
    return /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent);
}

function printOrExportPDF() {
    updateAll();
    updatePrintStyle();
    saveState(false);

    // Always use html2pdf if available for better consistency across all devices (Desktop & Mobile)
    if (typeof html2pdf !== 'undefined') {
        const orientation = state.fields.print_orientation === 'portrait' ? 'portrait' : 'landscape';
        const targetWidth = 1122; // Keep wide for high quality, let PDF scale to A4
        
        _enterPrintMode(true, targetWidth);
        const el = byId('printArea');
        const school = (state.fields.school_name_input || 'jadwal').replace(/[^\u0600-\u06FF\w-]+/g, '-');

        const opt = {
            margin: 0,
            filename: `${school}-${new Date().toLocaleDateString('ar-SA').replace(/\//g, '-')}.pdf`,
            image: { type: 'jpeg', quality: 0.98 },
            html2canvas: {
                scale: 2,
                useCORS: true,
                logging: false,
                allowTaint: true,
                letterRendering: true,
                width: targetWidth,
                windowWidth: targetWidth
            },
            jsPDF: {
                unit: 'mm',
                format: 'a4',
                orientation: orientation,
                compress: true
            },
            pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
        };

        showToast('جاري تجهيز ملف PDF بدقة عالية...');
        setTimeout(() => {
            updateAll(); // Ensure latest data is reflected
            html2pdf().set(opt).from(el).save().then(() => {
                _exitPrintMode();
                showToast('تم تصدير ملف PDF بنجاح ✅');
            }).catch(err => {
                console.error('PDF Export Error:', err);
                _exitPrintMode();
                window.print(); // Fallback to browser print if library fails
            });
        }, 250);
    } else {
        window.print();
    }
}

function _enterPrintMode(isMobilePDF = false, targetWidth = 1122) {
    // Hide all editing tools and buttons
    const selectors = '.no-print, .cell-tools, .subject-select, .add-subject-btn, .delete-subject-btn, .class-delete-btn, .instruction-delete-btn, button:not(.action-btn)';
    document.querySelectorAll(selectors).forEach(el => {
        el.dataset._origDisplay = el.style.display;
        el.style.display = 'none';
        el.setAttribute('style', (el.getAttribute('style') || '') + '; display: none !important;');
    });
    document.querySelectorAll('.print-subject').forEach(el => {
        el.dataset._origDisplay = el.style.display;
        el.style.display = 'block';
    });

    const thead = byId('table_head');
    if (thead) {
        thead.dataset._origBg = thead.style.backgroundColor;
        thead.dataset._origColor = thead.style.color;
        thead.style.backgroundColor = '#064e3b';
        thead.style.color = 'white';
    }

    if (isMobilePDF) {
        const el = byId('printArea');
        el.dataset._origWidth = el.style.width;
        el.dataset._origMaxWidth = el.style.maxWidth;
        el.dataset._origOverflow = el.style.overflow;
        el.dataset._origMargin = el.style.margin;
        el.dataset._origPadding = el.style.padding;
        el.dataset._origMinHeight = el.style.minHeight;

        el.style.width = targetWidth + 'px';
        el.style.maxWidth = 'none';
        el.style.overflow = 'visible';
        el.style.margin = '0';
        el.style.padding = '10mm'; // هامش داخلي للطباعة
        el.style.minHeight = '0'; // إلغاء الحد الأدنى للارتفاع لتجنب الصفحة الثانية
        el.style.backgroundColor = 'white';

        // إجبار الأب على عدم القص وتوسيط المحتوى
        const wrapper = el.parentElement;
        if (wrapper) {
            wrapper.dataset._origOverflow = wrapper.style.overflow;
            wrapper.dataset._origDisplay = wrapper.style.display;
            wrapper.style.overflow = 'visible';
            wrapper.style.display = 'block';
        }
    }
}

function _exitPrintMode() {
    document.querySelectorAll('.no-print, .cell-tools, .subject-select, .add-subject-btn').forEach(el => {
        el.style.display = el.dataset._origDisplay || '';
        delete el.dataset._origDisplay;
    });
    document.querySelectorAll('.print-subject').forEach(el => {
        el.style.display = el.dataset._origDisplay || '';
        delete el.dataset._origDisplay;
    });
    const thead = byId('table_head');
    if (thead) {
        thead.style.backgroundColor = thead.dataset._origBg || '';
        thead.style.color = thead.dataset._origColor || '';
        delete thead.dataset._origBg;
        delete thead.dataset._origColor;
    }

    const el = byId('printArea');
    if (el && el.dataset._origWidth !== undefined) {
        el.style.width = el.dataset._origWidth;
        el.style.maxWidth = el.dataset._origMaxWidth;
        el.style.overflow = el.dataset._origOverflow;
        el.style.margin = el.dataset._origMargin || '';
        el.style.padding = el.dataset._origPadding || '';
        el.style.minHeight = el.dataset._origMinHeight || '';

        delete el.dataset._origWidth;
        delete el.dataset._origMaxWidth;
        delete el.dataset._origOverflow;
        delete el.dataset._origMargin;
        delete el.dataset._origPadding;
        delete el.dataset._origMinHeight;

        const wrapper = el.parentElement;
        if (wrapper && wrapper.dataset._origOverflow !== undefined) {
            wrapper.style.overflow = wrapper.dataset._origOverflow;
            wrapper.style.display = wrapper.dataset._origDisplay || '';
            delete wrapper.dataset._origOverflow;
            delete wrapper.dataset._origDisplay;
        }
    }
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
        updateAll();
        updatePrintStyle();
    });
}

boot();

