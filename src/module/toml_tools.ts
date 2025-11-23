// TypeScript conversion of module/toml_tools.py

export function getTableElement(toml: any, treeList: string[]): any {
    let tomlCopy = JSON.parse(JSON.stringify(toml)); // Deep copy

    for (const entry of treeList) {
        if (!(entry in tomlCopy)) {
            return null;
        }
        tomlCopy = tomlCopy[entry];
    }

    return tomlCopy;
}
