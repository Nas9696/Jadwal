export const toArabicDigits = (str) => {
    if (typeof str !== 'string' && typeof str !== 'number') return str;
    const arabic = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'];
    return String(str).replace(/[0-9]/g, w => arabic[+w]);
};

export const parseArabicNum = (str) => {
    if (!str) return 0;
    const arabic = {'0':0,'1':1,'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9};
    const cleaned = String(str).replace(/[0-9]/g, d => arabic[d]);
    return parseInt(cleaned) || 0;
};

export const timeToMinutes = (timeStr) => {
    if (!timeStr) return 0;
    const [hours, minutes] = timeStr.split(':').map(Number);
    return hours * 60 + minutes;
};

export const minutesToTime = (totalMinutes) => {
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
};

export const getCurrentTimeMinutes = () => {
    const now = new Date();
    return now.getHours() * 60 + now.getMinutes();
};

export const formatDuration = (totalSeconds) => {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
};
