// TypeScript conversion of module/dependency.py

import * as fs from 'fs';
import * as path from 'path';
import * as properties from './properties';
import * as dictTools from './dict_tools';
import * as buildCmds from './build_cmds';
import * as files from './files';
import { OBIConstants } from './obi_constants';

interface SourceItem {
    source: string;
    cmds: any[];
}

interface LevelItem {
    level: number;
    sources: SourceItem[];
}

interface DependencyDict {
    [key: string]: string[];
}

interface ObjectsTree {
    [key: string]: ObjectsTree;
}

const defaultAppConfig = properties.getAppProperties();

export function parseDependencyFile(filePath: string): DependencyDict {
    return properties.getJson(filePath);
}

export function getBuildOrder(
    dependencyDict: DependencyDict,
    targetList: string[] = [],
    appConfig: any = defaultAppConfig
): { timestamp: string; compiles: LevelItem[] } {
    const objectsTree = getTargetsDependedObjects(dependencyDict, targetList);
    files.writeJson(objectsTree, '.obi/tmp/objects_tree.json');

    const dependedObjects = getTargetsOnlyDependedObjects(dependencyDict, targetList);
    console.log(`objectsTree=${JSON.stringify(objectsTree)}`);
    files.writeJson(dependedObjects, OBIConstants.get("DEPENDEND_OBJECT_LIST") || '.obi/tmp/dependend-object-list.json');

    const orderedTargetTree = getTargetsByLevel(objectsTree);
    console.log(`orderedTargetTree=${JSON.stringify(orderedTargetTree)}`);
    files.writeJson(orderedTargetTree, '.obi/tmp/ordered_target_tree.json');

    const newTargetTree = removeDuplicities(orderedTargetTree);
    files.writeJson(newTargetTree, '.obi/tmp/new_target_tree.json');
    console.log(`newTargetTree=${JSON.stringify(newTargetTree)}`);

    buildCmds.addBuildCmds(newTargetTree, appConfig);

    const result = {
        timestamp: new Date().toISOString(),
        compiles: newTargetTree
    };

    return result;
}

function getTargetsDependedObjects(
    dependencyDict: DependencyDict,
    targets: string[] = []
): ObjectsTree {
    const targetsObjects: ObjectsTree = {};

    for (const target of targets) {
        targetsObjects[target] = getTargetDependedObjects(dependencyDict, target);
    }

    return targetsObjects;
}

function getTargetDependedObjects(
    dependencyDict: DependencyDict,
    target: string,
    result: ObjectsTree = {}
): ObjectsTree {
    const dependedObjects: ObjectsTree = {};
    const srcBasePath = defaultAppConfig['general']?.['source-dir'] || 'src';

    for (const [obj, objDependencies] of Object.entries(dependencyDict)) {
        if (objDependencies.includes(target)) {
            const objPath = path.join(srcBasePath, obj);
            if (!fs.existsSync(objPath)) {
                console.log(`Doesn't exist: obj=${obj}, exists=${fs.existsSync(objPath)}`);
                continue;
            }
            
            console.log(`Add obj obj=${obj}`);
            dependedObjects[obj] = getTargetDependedObjects(dependencyDict, obj, result);
        }
    }
    
    return dependedObjects;
}

function getTargetsOnlyDependedObjects(
    dependencyDict: DependencyDict,
    targets: string[] = []
): string[] {
    let targetsObjects: string[] = [];

    for (const target of targets) {
        console.log(`Dependend 1 ${target}`);
        targetsObjects = targetsObjects.concat(getTargetOnlyDependedObjects(dependencyDict, target, targets));
    }

    return Array.from(new Set(targetsObjects));
}

function getTargetOnlyDependedObjects(
    dependencyDict: DependencyDict,
    target: string,
    origTargets: string[]
): string[] {
    let dependedObjects: string[] = [];
    const srcBasePath = defaultAppConfig['general']?.['source-dir'] || 'src';

    for (const [obj, objDependencies] of Object.entries(dependencyDict)) {
        if (objDependencies.includes(target)) {
            const objPath = path.join(srcBasePath, obj);
            if (!fs.existsSync(objPath)) {
                console.warn(`Doesn't exist: obj=${obj}, exists=${fs.existsSync(objPath)}`);
                continue;
            }
            
            if (origTargets.includes(obj)) {
                continue;
            }

            dependedObjects = dependedObjects.concat([obj], getTargetOnlyDependedObjects(dependencyDict, obj, origTargets));
        }
    }
    
    return dependedObjects;
}

function removeDuplicities(targetTree: LevelItem[]): LevelItem[] {
    // All levels
    for (const levelItem of targetTree.sort((a, b) => a.level - b.level)) {
        // All objects in this level
        for (const obj of levelItem.sources) {
            // Scan reverse for duplicated objects
            for (const revLevelItem of targetTree.slice().reverse().sort((a, b) => b.level - a.level)) {
                const revLevelSources = revLevelItem.sources.map(item => item.source);

                for (let i = 0; i < targetTree.length; i++) {
                    const sources = targetTree[i].sources.map(item => item.source);
                    if (targetTree[i].level < revLevelItem.level && 
                        revLevelSources.includes(obj.source) && 
                        sources.includes(obj.source)) {
                        const index = targetTree[i].sources.findIndex(item => item.source === obj.source);
                        if (index !== -1) {
                            targetTree[i].sources.splice(index, 1);
                        }
                    }
                }
            }
        }
    }

    return targetTree;
}

function getTargetsByLevel(targetTree: ObjectsTree, level: number = 1): LevelItem[] {
    let newTargetTree: LevelItem[] = [];
    
    // Add object to list
    for (const [obj, nextObjs] of Object.entries(targetTree)) {
        let loopLevelObj = newTargetTree.find(item => item.level === level);
        
        if (!loopLevelObj) {
            loopLevelObj = { level, sources: [] };
            newTargetTree.push(loopLevelObj);
        }

        if (loopLevelObj.sources.some(item => item.source === obj)) {
            continue;
        }

        loopLevelObj.sources.push({ source: obj, cmds: [] });

        // Also add depended objects to list
        for (const [nextObj, nextSubObjs] of Object.entries(nextObjs as ObjectsTree)) {
            let loopNextLevelObj = newTargetTree.find(item => item.level === level + 1);
            
            if (!loopNextLevelObj) {
                loopNextLevelObj = { level: level + 1, sources: [] };
                newTargetTree.push(loopNextLevelObj);
            }
            
            if (loopNextLevelObj.sources.some(item => item.source === nextObj)) {
                continue;
            }

            loopNextLevelObj.sources.push({ source: nextObj, cmds: [] });

            // Recursive call to go through the tree
            const extendedTree = getTargetsByLevel(nextSubObjs as ObjectsTree, level + 2);
            newTargetTree = dictTools.deepListMerge(extendedTree, newTargetTree);
        }
    }

    return newTargetTree.sort((a, b) => a.level - b.level);
}
