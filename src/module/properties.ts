// TypeScript conversion of module/properties.py

import * as fs from 'fs';
import * as path from 'path';
import { OBIConstants } from './obi_constants';
import * as tomlTools from './toml_tools';
import * as files from './files';
import * as dictTools from './dict_tools';

const toml = require('@iarna/toml');

const configContent: Record<string, any> = {};

export function getJson(config: string): any {
    if (!fs.existsSync(config)) {
        return {};
    }

    if (config in configContent) {
        return configContent[config];
    }

    try {
        const content = fs.readFileSync(config, 'utf-8');
        configContent[config] = JSON.parse(content);
    } catch (e) {
        configContent[config] = {};
        console.error(e);
    }

    return configContent[config];
}

export function writeJson(config: string, content: any): void {
    configContent[config] = content;
    files.writeJson(content, config);
}

export function getConfig(config: string): any {
    if (!fs.existsSync(config)) {
        return {};
    }

    if (config in configContent) {
        return configContent[config];
    }

    try {
        const content = fs.readFileSync(config, 'utf-8');
        configContent[config] = toml.parse(content);
    } catch (e) {
        configContent[config] = {};
        console.error(`Error loading config file ${config}`);
        console.error(e);
    }

    return configContent[config];
}

export function writeConfig(config: string, content: any): void {
    configContent[config] = content;
    files.writeToml(content, config);
}

export function getAppProperties(): any {
    const appProjectConfig = getConfig(OBIConstants.get("CONFIG_TOML") || '.obi/config.toml');
    const appUserConfig = getConfig(OBIConstants.get("CONFIG_USER_TOML") || '.obi/config.user.toml');

    const appConfig = dictTools.dictMerge(appProjectConfig, appUserConfig);

    return appConfig;
}

export function getSourceProperties(config: any, source: string): any {
    const sourceConfig = getConfig(OBIConstants.get("SOURCE_CONFIG_TOML") || '.obi/source-config.toml');
    const srcSuffixes = path.extname(source);
    const fileExtensions = srcSuffixes.replace(/^\./, '');

    let globalSettings = tomlTools.getTableElement(config, ['global', 'settings', 'general']) || {};
    const typeSettings = tomlTools.getTableElement(config, ['global', 'settings', 'language']) || {};
    
    // Override source individual settings
    if (source in sourceConfig && 'settings' in sourceConfig[source]) {
        globalSettings = { ...globalSettings, ...sourceConfig[source]['settings'] };
    }

    if (fileExtensions in typeSettings) {
        globalSettings = { ...globalSettings, ...typeSettings[fileExtensions] };
    }

    globalSettings['SOURCE_FILE_NAME'] = path.join(config['general']['source-dir'], source).replace(/\\/g, '/');
    globalSettings['SOURCE_BASE_FILE_NAME'] = path.basename(globalSettings['SOURCE_FILE_NAME']);
    globalSettings['TARGET_LIB'] = getTargetLib(source, globalSettings['TARGET_LIB'], globalSettings['TARGET_LIB_MAPPING']);
    globalSettings['OBJ_NAME'] = path.basename(source, path.extname(source));

    globalSettings['SET_LIBL'] = getSetLiblCmd(config, globalSettings['LIBL'] || [], globalSettings['TARGET_LIB']);

    return globalSettings;
}

export function getSetLiblCmd(config: any, libl: string[], targetLib: string): string {
    let setLibl = "";
    for (const lib of libl) {
        const libReplaced = lib.replace("$(TARGET_LIB)", targetLib);
        if (setLibl.length > 0) {
            setLibl += '; ';
        }
        setLibl += config['global']['cmds']['add-lible'].replace('$(LIB)', libReplaced);
    }
    return setLibl;
}

export function getTargetLib(source: string, targetLib?: string, libMapping?: Record<string, string>): string {
    const sourceLib = source.split('/')[0].toLowerCase();

    if (targetLib && targetLib.toLowerCase() === '*source') {
        return sourceLib;
    }

    if (targetLib) {
        return targetLib.toLowerCase();
    }

    if (libMapping) {
        for (const [k, v] of Object.entries(libMapping)) {
            if (k.toLowerCase() === sourceLib) {
                return v.toLowerCase();
            }
        }
    }

    return sourceLib;
}
