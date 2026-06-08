// --- Smart Table Shared Utilities ---

window.toArabicDigits = (str) => {
    if (typeof str !== 'string' && typeof str !== 'number') return str;
    const arabic = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'];
    return String(str).replace(/[0-9]/g, w => arabic[+w]);
};

window.timeToMinutes = (timeStr) => {
    if (!timeStr) return 0;
    const [hours, minutes] = timeStr.split(':').map(Number);
    return hours * 60 + minutes;
};

window.minutesToTime = (totalMinutes) => {
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
};

window.getCurrentTimeMinutes = () => {
    const now = new Date();
    return now.getHours() * 60 + now.getMinutes();
};

window.formatDuration = (totalSeconds) => {
    if (totalSeconds < 0) return "00:00";
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
};

// --- Storage Manager ---
window.SmartStorage = class {
    constructor(moduleName) {
        this.prefix = `smartTable_${moduleName}_`;
    }
    set(key, value) { localStorage.setItem(this.prefix + key, JSON.stringify(value)); }
    get(key, defaultValue = null) {
        const item = localStorage.getItem(this.prefix + key);
        try { return item ? JSON.parse(item) : defaultValue; } catch (e) { return defaultValue; }
    }
    clear() {
        Object.keys(localStorage).forEach(key => { if (key.startsWith(this.prefix)) localStorage.removeItem(key); });
    }
};

// --- Notifications ---
window.NotificationManager = class {
    constructor() {
        this.permission = "default";
        try { this.permission = Notification.permission; } catch(e) {}
        this.audioCtx = null;
    }
    async requestPermission() {
        try { this.permission = await Notification.requestPermission(); } catch(e) {}
    }
    notify(title, body) {
        if (this.permission === 'granted') new Notification(title, { body });
    }
    playBell(type = 'default') {
        try {
            if (!this.audioCtx) this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = this.audioCtx.createOscillator();
            const gain = this.audioCtx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(type === 'start' ? 880 : 440, this.audioCtx.currentTime);
            gain.gain.setValueAtTime(0, this.audioCtx.currentTime);
            gain.gain.linearRampToValueAtTime(0.5, this.audioCtx.currentTime + 0.1);
            gain.gain.exponentialRampToValueAtTime(0.01, this.audioCtx.currentTime + 2);
            osc.connect(gain);
            gain.connect(this.audioCtx.destination);
            osc.start(); osc.stop(this.audioCtx.currentTime + 2);
        } catch(e) { console.warn("Audio bell failed", e); }
    }
};

// --- Schedule Engine ---
window.ScheduleEngine = class {
    constructor(schedule = []) { this.schedule = schedule; }
    setSchedule(s) { this.schedule = s; }
    getStatus() {
        const now = window.getCurrentTimeMinutes();
        const nowSeconds = new Date().getSeconds();
        const sorted = [...this.schedule].sort((a, b) => window.timeToMinutes(a.start) - window.timeToMinutes(b.start));
        let current = null, next = null, remainingSeconds = 0;
        for (let i = 0; i < sorted.length; i++) {
            const s = sorted[i];
            const start = window.timeToMinutes(s.start), end = window.timeToMinutes(s.end);
            if (now >= start && now < end) {
                current = s; remainingSeconds = (end - now) * 60 - nowSeconds;
                next = sorted[i + 1] || null; break;
            } else if (now < start) {
                next = s; remainingSeconds = (start - now) * 60 - nowSeconds; break;
            }
        }
        return { current, next, remainingSeconds };
    }
};
