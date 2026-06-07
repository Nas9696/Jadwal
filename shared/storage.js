export class SmartStorage {
    constructor(moduleName) {
        this.prefix = `smartTable_${moduleName}_`;
    }

    set(key, value) {
        localStorage.setItem(this.prefix + key, JSON.stringify(value));
    }

    get(key, defaultValue = null) {
        const item = localStorage.getItem(this.prefix + key);
        try {
            return item ? JSON.parse(item) : defaultValue;
        } catch (e) {
            console.error(`Error parsing storage key: ${key}`, e);
            return defaultValue;
        }
    }

    remove(key) {
        localStorage.removeItem(this.prefix + key);
    }

    clear() {
        Object.keys(localStorage).forEach(key => {
            if (key.startsWith(this.prefix)) {
                localStorage.removeItem(key);
            }
        });
    }

    getAll() {
        const data = {};
        Object.keys(localStorage).forEach(key => {
            if (key.startsWith(this.prefix)) {
                const cleanKey = key.replace(this.prefix, '');
                data[cleanKey] = this.get(cleanKey);
            }
        });
        return data;
    }
}
