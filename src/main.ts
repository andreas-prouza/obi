// TypeScript conversion of create_build_list function from main.py

import * as fs from 'fs';
import * as path from 'path';
import * as properties from './module/properties';
import * as files from './module/files';
import * as dependency from './module/dependency';
import * as buildCmds from './module/build_cmds';
import * as results from './module/results';
import { OBIConstants } from './module/obi_constants';

interface Args {
    source?: string;
    setPath: string;
}

export function createBuildList(args: Args): void {
    console.log('Create build list');

    // Properties
    const appConfig = properties.getAppProperties();
    const generalConfig = appConfig['general'];
    
    const sourceDir = path.join(generalConfig['local-base-dir'], generalConfig['source-dir']);
    const buildList = generalConfig['compiled-object-list'];
    const objectTypes = generalConfig['supported-object-types'];
    const dependencyList = properties.getJson(generalConfig['dependency-list']);
    const buildOutputDir = appConfig['general']?.['build-output-dir'] || '.obi/build-output';
    const fsEncoding = appConfig['general']?.['file-system-encoding'] || 'utf-8';

    // Removes old files and dirs
    if (buildOutputDir.trim().length < 3 || buildOutputDir.trim() === '/') {
        throw new Error(`Wrong build output dir: ${buildOutputDir}`);
    }
    
    if (fs.existsSync(buildOutputDir)) {
        fs.rmSync(buildOutputDir, { recursive: true, force: true });
    }

    // Get source list
    let changedSourcesList: files.ChangedSources;
    
    if (!args.source) {
        const sourceList = files.getFiles(sourceDir, objectTypes, fsEncoding);
        changedSourcesList = files.getChangedSources(sourceDir, buildList, objectTypes, sourceList);
    } else {
        // Source provided by parameter
        const singleSourceList: files.SourceList = {};
        singleSourceList[args.source] = '';
        changedSourcesList = files.getChangedSources(sourceDir, buildList, objectTypes, singleSourceList);
    }

    files.writeJson(changedSourcesList, OBIConstants.get("CHANGED_OBJECT_LIST") || '.obi/tmp/changed-object-list.json');
    
    const allChangedSources = [...changedSourcesList['new-objects'], ...changedSourcesList['changed-sources']];
    let buildTargets = dependency.getBuildOrder(dependencyList, allChangedSources, appConfig);
    buildTargets = buildCmds.orderBuilds(buildTargets);

    // Write source list to json
    files.writeJson(buildTargets, generalConfig['compile-list'] || '.obi/tmp/compile-list.json');

    // Generate document
    results.createResultDoc(buildTargets, appConfig, fsEncoding);
}

// Main entry point
export function main(): void {
    const args: Args = {
        setPath: process.cwd()
    };
    
    // Parse command line arguments
    const argvIndex = process.argv.indexOf('--set-path');
    if (argvIndex !== -1 && process.argv[argvIndex + 1]) {
        args.setPath = process.argv[argvIndex + 1];
    }
    
    const sourceIndex = process.argv.indexOf('--source');
    if (sourceIndex !== -1 && process.argv[sourceIndex + 1]) {
        args.source = process.argv[sourceIndex + 1];
    }
    
    // Change to the project directory
    process.chdir(args.setPath);
    
    try {
        createBuildList(args);
        console.log('Build list created successfully!');
    } catch (error) {
        console.error('Error creating build list:', error);
        process.exit(1);
    }
}

// Run if called directly
if (require.main === module) {
    main();
}
