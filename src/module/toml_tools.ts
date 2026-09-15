// TypeScript conversion of module/toml_tools.py

function deepClone<T>(obj: T): T {
    if (obj === null || typeof obj !== 'object') {
        return obj;
    }
    if (Array.isArray(obj)) {
        return obj.map(item => deepClone(item)) as any;
    }
    const cloned: any = {};
    for (const key in obj) {
        if (obj.hasOwnProperty(key)) {
            cloned[key] = deepClone(obj[key]);
        }
    }
    return cloned;
}

export function getTableElement(toml: any, treeList: string[]): any {
    let tomlCopy = deepClone(toml);

    for (const entry of treeList) {
        if (!(entry in tomlCopy)) {
            return null;
        }
        tomlCopy = tomlCopy[entry];
    }

    return tomlCopy;
}
