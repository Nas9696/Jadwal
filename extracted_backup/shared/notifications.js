export class NotificationManager {
    constructor() {
        this.permission = Notification.permission;
        this.audioCtx = null;
    }

    async requestPermission() {
        if (this.permission !== 'granted') {
            this.permission = await Notification.requestPermission();
        }
        return this.permission;
    }

    notify(title, body, icon = '/favicon.ico') {
        if (this.permission === 'granted') {
            new Notification(title, { body, icon });
        }
    }

    playBell(type = 'default') {
        // Basic Oscillator Bell if no audio file is available
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

        osc.start();
        osc.stop(this.audioCtx.currentTime + 2);
    }
}
