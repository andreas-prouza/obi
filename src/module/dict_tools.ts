// TypeScript conversion of module/dict_tools.py

interface SourceItem {
    source: string;
    cmds: any[];
}

interface LevelItem {
    level: number;
    sources: SourceItem[];
}

export function deepMerge(a: Record<string, SourceItem[]>, b: Record<string, SourceItem[]>): Record<string, SourceItem[]> {
    const result = { ...a };

    for (const [bLevel, bSourceList] of Object.entries(b)) {
        for (const bSource of bSourceList) {
            if (!(bLevel in result)) {
                result[bLevel] = [];
            }

            const sourceExists = result[bLevel].some(item => item.source === bSource.source);
            if (!sourceExists) {
                result[bLevel].push(bSource);
            }
        }
    }

    return result;
}

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

export function deepListMerge(a: LevelItem[], b: LevelItem[]): LevelItem[] {
    const result = deepClone(a);

    for (const bLevelItem of b) {
        const bLevel = bLevelItem.level;
        const bSources = bLevelItem.sources;

        let resultLevelItem = result.find((item: LevelItem) => item.level === bLevel);

        if (!resultLevelItem) {
            resultLevelItem = { level: bLevel, sources: [] };
            result.push(resultLevelItem);
        }

        for (const bSource of bSources) {
            const sourceExists = resultLevelItem.sources.some((item: SourceItem) => item.source === bSource.source);
            if (!sourceExists) {
                resultLevelItem.sources.push({ source: bSource.source, cmds: bSource.cmds });
            }
        }
    }

    return result;
}

export function dictMerge(baseDct: any, mergeFromDct: any): any {
    const result: any = {};
    const allKeys = new Set([...Object.keys(baseDct), ...Object.keys(mergeFromDct)]);

    for (const k of allKeys) {
        if (k in baseDct && k in mergeFromDct) {
            if (typeof baseDct[k] === 'object' && baseDct[k] !== null && 
                typeof mergeFromDct[k] === 'object' && mergeFromDct[k] !== null &&
                !Array.isArray(baseDct[k]) && !Array.isArray(mergeFromDct[k])) {
                result[k] = dictMerge(baseDct[k], mergeFromDct[k]);
            } else {
                if (typeof mergeFromDct[k] === 'boolean' || 
                    (typeof mergeFromDct[k] === 'string' && mergeFromDct[k].length !== 0) ||
                    (typeof mergeFromDct[k] !== 'string' && mergeFromDct[k])) {
                    result[k] = mergeFromDct[k];
                } else {
                    result[k] = baseDct[k];
                }
            }
        } else if (k in baseDct) {
            result[k] = baseDct[k];
        } else {
            result[k] = mergeFromDct[k];
        }
    }

    return result;
}
