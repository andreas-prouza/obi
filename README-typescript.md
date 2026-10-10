# TypeScript Conversion of create_build_list Function

This directory contains a TypeScript conversion of the `create_build_list` function from `main.py`, along with all necessary dependencies.

## Overview

The following Python modules have been converted to TypeScript:

- `main.py` → `src/main.ts` (create_build_list function)
- `module/obi_constants.py` → `src/module/obi_constants.ts`
- `module/dict_tools.py` → `src/module/dict_tools.ts`
- `module/toml_tools.py` → `src/module/toml_tools.ts`
- `module/files.py` → `src/module/files.ts`
- `module/properties.py` → `src/module/properties.ts`
- `module/app_config_tools.py` → `src/module/app_config_tools.ts` (simplified)
- `module/build_cmds.py` → `src/module/build_cmds.ts`
- `module/dependency.py` → `src/module/dependency.ts`
- `module/results.py` → `src/module/results.ts` (create_result_doc function only)

## Prerequisites

- Node.js (v14 or higher)
- npm

## Installation

Install the required dependencies:

```bash
npm install
```

## Building

To compile the TypeScript code:

```bash
npm run build
```

This will compile the TypeScript files in the `src/` directory and output JavaScript files to the `dist/` directory.

## Usage

To run the create_build_list function:

```bash
node dist/main.js --set-path /path/to/project
```

Optional parameters:
- `--set-path`: Path to the project directory (required)
- `--source`: Consider a single source file (optional)

Example:

```bash
node dist/main.js --set-path /home/user/myproject
node dist/main.js --set-path /home/user/myproject --source mylib/qrpglesrc/mysource.rpgle
```

## Dependencies

The TypeScript version uses the following npm packages:

- `typescript`: TypeScript compiler
- `@types/node`: Type definitions for Node.js
- `@iarna/toml`: TOML parser for reading configuration files

## Differences from Python Version

1. **Error Handling**: TypeScript version uses standard JavaScript error handling
2. **File I/O**: Uses Node.js `fs` module instead of Python's file operations
3. **Path Handling**: Uses Node.js `path` module for cross-platform path handling
4. **TOML Parsing**: Uses `@iarna/toml` instead of Python's `toml` library
5. **Type Safety**: Includes TypeScript interfaces for better type checking
6. **Simplified app_config_tools**: Extended source processing has been simplified in the initial conversion

## Project Structure

```
obi/
├── src/
│   ├── main.ts                    # Main entry point with create_build_list
│   └── module/
│       ├── obi_constants.ts       # Constants
│       ├── dict_tools.ts          # Dictionary manipulation utilities
│       ├── toml_tools.ts          # TOML utilities
│       ├── files.ts               # File operations
│       ├── properties.ts          # Configuration management
│       ├── app_config_tools.ts    # Application config utilities
│       ├── build_cmds.ts          # Build command generation
│       ├── dependency.ts          # Dependency resolution
│       └── results.ts             # Result document generation
├── dist/                          # Compiled JavaScript (generated)
├── tsconfig.json                  # TypeScript configuration
├── package.json                   # npm package configuration
└── README-typescript.md           # This file
```

## Notes

- The TypeScript version maintains the same logic flow as the Python version
- All file paths are handled in a cross-platform manner
- The compiled JavaScript can be run on any platform with Node.js
- The `dist/` directory is excluded from version control via `.gitignore`
