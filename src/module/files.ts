// TypeScript conversion of module/files.py

import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';
import { OBIConstants } from './obi_constants';

export interface SourceList {
    [key: string]: string;
}

export interface ChangedSources {
    'new-objects': string[];
    'changed-sources': string[];
}

export function getFiles(
    dirPath: string,
    fileExtensions: string[] = [],
    fsEncoding: string = 'utf-8',
    withTime: boolean = false
): SourceList {
    const src: SourceList = {};

    function walkDir(dir: string) {
        const files = fs.readdirSync(dir, { withFileTypes: true });

        for (const file of files) {
            const filePath = path.join(dir, file.name);

            if (file.isDirectory()) {
                walkDir(filePath);
            } else if (file.isFile()) {
                const hasMatchingExtension = fileExtensions.length === 0 || 
                    fileExtensions.some(ext => file.name.endsWith(ext));

                if (hasMatchingExtension) {
                    const relativePath = path.relative(dirPath, filePath).replace(/\\/g, '/');
                    const hashedFile = getFileHash(filePath);
                    src[relativePath] = hashedFile;
                }
            }
        }
    }

    walkDir(dirPath);
    return src;
}

export function getChangedSources(
    sourceDir: string,
    buildJson: string,
    objectTypes: string[],
    srcList: SourceList | null = null
): ChangedSources {
    if (srcList === null) {
        srcList = getFiles(sourceDir, objectTypes);
    }

    let buildList: SourceList = {};
    if (fs.existsSync(buildJson)) {
        const content = fs.readFileSync(buildJson, 'utf-8');
        buildList = JSON.parse(content);
    }

    console.log(`Objects in build list: ${Object.keys(buildList).length}`);
    console.log(`Search for changed sources in '${sourceDir}'`);
    console.log(`Found ${Object.keys(srcList).length} sources`);

    const missingObj: string[] = [];
    const changedSrc: string[] = [];

    for (const [src, hashValue] of Object.entries(srcList)) {
        if (!(src in buildList)) {
            console.log(`${src} not in build list`);
            missingObj.push(src);
            continue;
        }
        if (buildList[src] === null || hashValue !== buildList[src]) {
            changedSrc.push(src);
        }
    }

    return { 'new-objects': missingObj, 'changed-sources': changedSrc };
}

export function getFileHash(filename: string): string {
    if (!fs.existsSync(filename)) {
        return '';
    }

    const stats = fs.statSync(filename);
    if (stats.size === 0) {
        return '';
    }

    const hash = crypto.createHash('md5');
    const fileBuffer = fs.readFileSync(filename);
    hash.update(fileBuffer);
    return hash.digest('hex');
}

export function writeJson(content: any, filePath: string): void {
    if (filePath === null) {
        return;
    }

    const dir = path.dirname(filePath);
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }

    fs.writeFileSync(filePath, JSON.stringify(content, null, 2), 'utf-8');
}

const validEncodings: BufferEncoding[] = ['utf-8', 'utf8', 'ascii', 'latin1', 'binary', 'base64', 'base64url', 'hex', 'ucs2', 'ucs-2', 'utf16le', 'utf-16le'];

function isValidEncoding(encoding: string): encoding is BufferEncoding {
    return validEncodings.includes(encoding as BufferEncoding);
}

export function writeText(
    content: string,
    filePath: string,
    writeEmptyFile: boolean = false,
    encoding: string = 'utf-8',
    mode: string = 'w'
): void {
    if (filePath === null || (content.length === 0 && !writeEmptyFile)) {
        return;
    }

    console.log(`Write Textfile: ${path.resolve(filePath)}; ${content.length} Bytes`);

    const dir = path.dirname(filePath);
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }

    const validEncoding = isValidEncoding(encoding) ? encoding : 'utf-8';
    fs.writeFileSync(filePath, content, validEncoding);
}

export function writeToml(content: any, filePath: string): void {
    if (filePath === null) {
        return;
    }

    const dir = path.dirname(filePath);
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }

    const toml = require('@iarna/toml');
    const tomlString = toml.stringify(content);
    fs.writeFileSync(filePath, tomlString, 'utf-8');
}
