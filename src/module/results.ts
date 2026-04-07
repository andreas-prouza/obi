// TypeScript conversion of module/results.py (simplified - only create_result_doc)

import * as fs from 'fs';
import * as path from 'path';
import * as files from './files';

interface CommandItem {
    cmd: string;
    status: string;
}

interface SourceItem {
    source: string;
    cmds: CommandItem[];
}

interface LevelItem {
    level: number;
    sources: SourceItem[];
}

interface BuildTargets {
    timestamp: string;
    compiles: LevelItem[];
}

export function createResultDoc(
    buildTargets: BuildTargets,
    appConfig: any,
    encoding: string = 'utf-8'
): void {
    const buildOutputDir = appConfig['general']?.['build-output-dir'] || '.obi/build-output';
    const compiledObjectListMd = appConfig['general']?.['compiled-object-list-md'] || 
                                  path.join(buildOutputDir, 'compiled-object-list.md');
    
    let mdContent = '# Build List\n\n';
    mdContent += `**Timestamp:** ${buildTargets.timestamp}\n\n`;
    mdContent += `**Total Levels:** ${buildTargets.compiles.length}\n\n`;
    
    for (const levelItem of buildTargets.compiles) {
        mdContent += `## Level ${levelItem.level}\n\n`;
        mdContent += `**Sources in this level:** ${levelItem.sources.length}\n\n`;
        
        for (const sourceItem of levelItem.sources) {
            mdContent += `### ${sourceItem.source}\n\n`;
            
            if (sourceItem.cmds && sourceItem.cmds.length > 0) {
                mdContent += '**Commands:**\n\n';
                for (const cmd of sourceItem.cmds) {
                    mdContent += `- Status: ${cmd.status}\n`;
                    mdContent += `  \`\`\`\n  ${cmd.cmd}\n  \`\`\`\n\n`;
                }
            } else {
                mdContent += '*No commands*\n\n';
            }
        }
    }
    
    files.writeText(mdContent, compiledObjectListMd, true, encoding);
    console.log(`Result document created: ${compiledObjectListMd}`);
}
