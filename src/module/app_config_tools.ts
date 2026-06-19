// TypeScript conversion of module/app_config_tools.py (simplified)

import * as path from 'path';
import * as fs from 'fs';

export function getSteps(source: string, appConfig: any): Array<string | any> {
    let initSteps: string[] = [];
    
    if ('*ALL' in appConfig['global']['steps']) {
        initSteps = appConfig['global']['steps']['*ALL'];
    }
    
    const steps = getExtendedSteps(source, appConfig);
    if (steps !== null) {
        return [...initSteps, ...steps];
    }

    return [...initSteps, ...getGlobalSteps(source, appConfig)];
}

function getGlobalSteps(source: string, appConfig: any): string[] {
    // Check if source matches the global steps
    for (const [extensionStep, stepValue] of Object.entries(appConfig['global']['steps'])) {
        if (extensionStep === source) {
            return stepValue as string[];
        }
    }
    
    // Simple pattern matching (simplified from fnmatch)
    for (const [extensionStep, stepValue] of Object.entries(appConfig['global']['steps'])) {
        if (source.match(new RegExp(extensionStep.replace(/\*/g, '.*').replace(/\?/g, '.')))) {
            return stepValue as string[];
        }
    }
    
    const srcSuffixes = path.extname(source);
    const fileExtensions = srcSuffixes.replace(/^\./, '');

    return appConfig['global']['steps'][fileExtensions] || [];
}

function getExtendedSteps(source: string, appConfig: any): Array<string | any> | null {
    // Simplified implementation - returns null for now
    // In full implementation, this would check extended source processing config
    return null;
}
