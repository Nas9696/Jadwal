import { timeToMinutes, getCurrentTimeMinutes } from './utils.js';

export class ScheduleEngine {
    constructor(schedule = []) {
        this.schedule = schedule; // [{ name, start, end, type }]
    }

    setSchedule(newSchedule) {
        this.schedule = newSchedule;
    }

    getStatus() {
        const now = getCurrentTimeMinutes();
        const nowSeconds = new Date().getSeconds();
        
        // Sort schedule by start time
        const sorted = [...this.schedule].sort((a, b) => timeToMinutes(a.start) - timeToMinutes(b.start));
        
        let current = null;
        let next = null;
        let remainingSeconds = 0;

        for (let i = 0; i < sorted.length; i++) {
            const session = sorted[i];
            const start = timeToMinutes(session.start);
            const end = timeToMinutes(session.end);

            if (now >= start && now < end) {
                current = session;
                remainingSeconds = (end - now) * 60 - nowSeconds;
                next = sorted[i + 1] || null;
                break;
            } else if (now < start) {
                next = session;
                remainingSeconds = (start - now) * 60 - nowSeconds;
                break;
            }
        }

        return { current, next, remainingSeconds };
    }
}
