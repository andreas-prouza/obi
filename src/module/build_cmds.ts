// TypeScript conversion of module/build_cmds.py

import * as path from 'path';
import * as properties from './properties';
import * as files from './files';
import * as appConfigTools from './app_config_tools';
import * as tomlTools from './toml_tools';
import { OBIConstants } from './obi_constants';

interface SourceItem {
    source: string;
    cmds: CommandItem[];
}

interface CommandItem {
    cmd: string;
    status: string;
}

interface LevelItem {
    level: number;
    sources: SourceItem[];
}

export function addBuildCmds(targetTree: LevelItem[], appConfig: any): void {
    const objectList: string[] = [];

    for (const targetItem of targetTree) {
        for (const sourceItem of targetItem.sources) {
            objectList.push(getObjectList(sourceItem.source, appConfig));
            sourceItem.cmds = getSourceBuildCmds(sourceItem.source, appConfig);
        }
    }

    const objectListStr = Array.from(new Set(objectList)).join('\n');
    console.log(`Write object list length=${objectListStr.length} to ${appConfig['general']['deployment-object-list']}`);
    files.writeText(objectListStr, appConfig['general']['deployment-object-list'], true);
}

function getObjectList(source: string, appConfig: any): string {
    const variableDict = properties.getSourceProperties(appConfig, source);
    console.log(`source=${source}`);
    console.log(`variableDict=${JSON.stringify(variableDict)}`);

    const prodLib = source.split('/')[0];
    const objType = source.split('.').pop() || '';
    const objAttr = source.split('.').slice(-2, -1)[0] || '';
    const deployObjList = `prod_obj|${prodLib}|${variableDict['TARGET_LIB']}|${variableDict['OBJ_NAME']}|${objType}|${objAttr}|${source}`;
    
    return deployObjList;
}

function removeUnresolvedCmdParameters(cmd: string): string {
    cmd = cmd.replace(/ACTGRP\(\$\(ACTGRP\)\)/g, '');
    cmd = cmd.replace(/ACTGRP\(\)/g, '');
    cmd = cmd.replace(/BNDDIR\(\$\(INCLUDE_BNDDIR\)\)/g, '');
    cmd = cmd.replace(/BNDDIR\(\)/g, '');
    cmd = cmd.replace(/TGTRLS\(\$\(TGTRLS\)\)/g, '');
    cmd = cmd.replace(/TGTRLS\(\)/g, '');
    cmd = cmd.replace(/STGMDL\(\$\(STGMDL\)\)/g, '');
    cmd = cmd.replace(/STGMDL\(\)/g, '');
    cmd = cmd.replace(/TGTCCSID\(\$\(TGTCCSID\)\)/g, '');
    cmd = cmd.replace(/TGTCCSID\(\)/g, '');
    cmd = cmd.replace(/DBGVIEW\(\$\(DBGVIEW\)\)/g, '');
    cmd = cmd.replace(/DBGVIEW\(\)/g, '');
    cmd = cmd.replace(/INCDIR\(\$\(INCDIR_SQLRPGLE\)\)/g, '');
    cmd = cmd.replace(/INCDIR\(\)/g, '');
    cmd = cmd.replace(/INCDIR\(\$\(INCDIR_RPGLE\)\)/g, '');
    return cmd;
}

export function getSourceBuildCmds(source: string, appConfig: any): CommandItem[] {
    console.log(`Check source cmds for ${source}`);
    const cmds: CommandItem[] = [];
    const sourcesConfig = properties.getConfig(OBIConstants.get("SOURCE_CONFIG_TOML") || '.obi/source-config.toml');
    const sourceConfig = source in sourcesConfig ? sourcesConfig[source] : {};

    const srcSuffixes = path.extname(source);
    const fileExtensions = srcSuffixes.replace(/^\./, '');
    console.log(`fileExtensions=${fileExtensions}`);
    console.log(`sourceConfig=${JSON.stringify(sourceConfig)}`);

    let steps = appConfigTools.getSteps(source, appConfig);

    // Override steps by individual source config
    if ('steps' in sourceConfig && sourceConfig['steps'].length > 0) {
        steps = sourceConfig['steps'];
        console.log(`steps=${JSON.stringify(steps)}`);
    }

    const variableDict = properties.getSourceProperties(appConfig, source);
    let varDictTmp: any = {};
    console.log(`variableDict=${JSON.stringify(variableDict)}`);

    for (const step of steps) {
        console.log(`step=${JSON.stringify(step)}`);
        if (typeof step === 'string' && step.trim() === '') {
            continue;
        }

        let cmd: string;
        
        if (typeof step === 'string') {
            cmd = getCmdFromStep(step, source, variableDict, appConfig, sourceConfig);
            console.log(`1 cmd=${cmd}`);
        } else if (typeof step === 'object') {
            varDictTmp = JSON.parse(JSON.stringify(variableDict)); // Deep copy
            console.log(`varDictTmp=${JSON.stringify(varDictTmp)}`);
            Object.assign(varDictTmp, step['properties'] || {});
            
            cmd = step['cmd'] || '';
            if (!cmd) {
                cmd = getCmdFromStep(step['step'] || '', source, varDictTmp, appConfig, sourceConfig);
                console.log(`2 cmd=${cmd}`);
            }
        } else {
            continue;
        }
        
        cmd = replaceCmdParameters(cmd, { ...variableDict, ...varDictTmp });
        cmds.push({ cmd, status: "new" });
    }

    console.log(`Added ${cmds.length} cmds for ${source}`);

    return cmds;
}

function getCmdFromStep(step: string, source: string, variableDict: any, appConfig: any, sourceConfig: any): string {
    let cmd = resolveCmdid({ ...appConfig, ...sourceConfig }, step);
    console.log(`2: cmd=${cmd}`);
    
    // Find all words starting and ending with %
    const percentWords = cmd.match(/%[\w\.]+%/g) || [];
    console.log(`Words starting and ending with %: ${JSON.stringify(percentWords)}`);
    
    for (const word of percentWords) {
        const key = word.replace(/%/g, '');
        const subcmd = resolveCmdid({ ...appConfig, ...sourceConfig }, key);
        cmd = cmd.replace(word, subcmd);
        console.log(`Replaced ${word} with ${subcmd} in cmd`);
    }

    variableDict['SET_LIBL'] = properties.getSetLiblCmd(appConfig, variableDict['LIBL'] || [], variableDict['TARGET_LIB']);
    
    if (!cmd || cmd === '') {
        throw new Error(`Step '${step}' not found in config`);
    }

    const dspjoblogCmd = appConfig['global']['cmds']['dspjoblog'] || null;
    if (dspjoblogCmd !== null) {
        const joblogSep = appConfig['global']['cmds']['joblog-separator'] || "";
        cmd += dspjoblogCmd.replace("$(joblog-separator)", joblogSep);
    }

    return cmd;
}

function resolveCmdid(config: any, cmdid: string): string {
    // Simple CSV parsing for cmdid like "global.compile-cmds.sqlrpgle.mod"
    const cmdidList = cmdid.split('.');
    console.log(`cmdidList=${JSON.stringify(cmdidList)}`);

    const cmd = tomlTools.getTableElement(config, cmdidList);
    
    if (!cmd || cmd === '') {
        throw new Error(`CmdID '${cmdid}' not found in config`);
    }

    return cmd;
}

function replaceCmdParameters(cmd: string, variableDict: any): string {
    for (const [k, v] of Object.entries(variableDict)) {
        if (typeof v !== 'string' && typeof v !== 'number') {
            continue;
        }
        cmd = cmd.replace(new RegExp(`\\$\\(${k}\\)`, 'g'), String(v));
    }

    cmd = removeUnresolvedCmdParameters(cmd);

    return cmd;
}

export function orderBuilds(targetTree: { timestamp: string; compiles: LevelItem[] }): { timestamp: string; compiles: LevelItem[] } {
    const orderedTargetTree: { timestamp: string; compiles: LevelItem[] } = {
        timestamp: targetTree.timestamp,
        compiles: []
    };
    
    for (const compiles of targetTree.compiles) {
        const levelList: LevelItem = { level: compiles.level, sources: [] };
        
        for (const sourceEntry of compiles.sources) {
            if (sourceEntry.source.split('.').pop() === 'file') {
                levelList.sources.unshift(sourceEntry);
                continue;
            }
            
            levelList.sources.push(sourceEntry);
        }
        
        orderedTargetTree.compiles.push(levelList);
    }
    
    return orderedTargetTree;
}
