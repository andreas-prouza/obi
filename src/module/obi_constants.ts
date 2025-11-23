// TypeScript conversion of module/obi_constants.py

export class OBIConstants {
    static readonly JOBLOG = '.obi/log/joblog.txt';
    static readonly OBI_BACKEND_VERSION = 2;

    static get(key: string, defaultValue: string | null = null): string {
        // In Python, this tries to get from etc.constants first, then falls back to class attributes
        // For now, we'll just return class attributes
        const value = (OBIConstants as any)[key];
        return value !== undefined ? value : (defaultValue || '');
    }
}
