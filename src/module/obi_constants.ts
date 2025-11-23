// TypeScript conversion of module/obi_constants.py

interface ConstantsMap {
    [key: string]: string | number;
}

export class OBIConstants {
    static readonly JOBLOG = '.obi/log/joblog.txt';
    static readonly OBI_BACKEND_VERSION = 2;

    static get(key: string, defaultValue: string | null = null): string {
        // In Python, this tries to get from etc.constants first, then falls back to class attributes
        // For now, we'll just return class attributes
        const constants: ConstantsMap = {
            JOBLOG: OBIConstants.JOBLOG,
            OBI_BACKEND_VERSION: String(OBIConstants.OBI_BACKEND_VERSION)
        };
        const value = constants[key];
        return value !== undefined ? String(value) : (defaultValue || '');
    }
}
