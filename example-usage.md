# Example Usage of TypeScript create_build_list

This document provides examples of how to use the TypeScript version of the `create_build_list` function.

## Prerequisites

Before using the TypeScript version, ensure you have:

1. Installed dependencies: `npm install`
2. Built the TypeScript code: `npm run build`
3. A valid OBI project structure with `.obi/config.toml`

## Command Line Usage

### Basic Usage

Run the build list creation for a project:

```bash
node dist/main.js --set-path /path/to/your/project
```

### With a Specific Source File

To create a build list for only a specific source file:

```bash
node dist/main.js --set-path /path/to/your/project --source mylib/qrpglesrc/mysource.rpgle
```

## Programmatic Usage

You can also use the TypeScript module programmatically in your own Node.js applications:

```typescript
import { createBuildList } from './dist/main';

const args = {
    setPath: '/path/to/your/project',
    source: 'mylib/qrpglesrc/mysource.rpgle' // Optional
};

try {
    createBuildList(args);
    console.log('Build list created successfully!');
} catch (error) {
    console.error('Error creating build list:', error);
}
```

## Expected Project Structure

Your project should have the following structure for the TypeScript version to work:

```
your-project/
├── .obi/
│   ├── config.toml              # Main configuration
│   ├── config.user.toml         # User-specific config (optional)
│   ├── source-config.toml       # Source-specific config (optional)
│   └── tmp/                     # Temporary files (created automatically)
├── src/                         # Your source code
│   └── mylib/
│       └── qrpglesrc/
│           └── mysource.rpgle
└── ...
```

## Configuration Files

### .obi/config.toml

Example minimal configuration:

```toml
[general]
local-base-dir = "."
source-dir = "src"
compiled-object-list = ".obi/compiled-object-list.json"
dependency-list = ".obi/dependency-list.json"
deployment-object-list = ".obi/deployment-object-list.txt"
supported-object-types = [".rpgle", ".sqlrpgle", ".pgm", ".srvpgm"]
build-output-dir = ".obi/build-output"
file-system-encoding = "utf-8"
compile-list = ".obi/tmp/compile-list.json"

[global.cmds]
add-lible = "ADDLIBLE LIB($(LIB))"

[global.steps]
"*.rpgle" = ["global.compile-cmds.rpgle"]
```

### .obi/dependency-list.json

Example dependency list:

```json
{
  "mylib/qrpglesrc/program1.rpgle": ["mylib/qrpglesrc/module1.rpgle"],
  "mylib/qrpglesrc/module1.rpgle": []
}
```

## Output

The TypeScript version will create:

1. **Compile List** (`.obi/tmp/compile-list.json`): JSON file with ordered build commands
2. **Changed Objects** (`.obi/tmp/changed-object-list.json`): List of new and changed objects
3. **Build Report** (`.obi/build-output/compiled-object-list.md`): Markdown report of the build
4. **Deployment List** (`.obi/deployment-object-list.txt`): Text file for deployment tools

## Error Handling

Common errors and solutions:

### "Wrong build output dir"
- Ensure `build-output-dir` in config.toml is set correctly and not empty or "/"

### "Config file not found"
- Ensure `.obi/config.toml` exists in the project directory
- Check the `--set-path` parameter points to the correct directory

### "Module not found"
- Run `npm install` to ensure all dependencies are installed
- Run `npm run build` to compile the TypeScript code

## Differences from Python Version

1. **Node.js Runtime**: Requires Node.js instead of Python
2. **Type Safety**: Includes TypeScript type checking for better reliability
3. **Dependencies**: Uses npm packages instead of Python packages
4. **Performance**: May have different performance characteristics compared to Python

## Support

For issues or questions:
- Check the main README.md
- Review the Python version documentation
- Examine the TypeScript source code in `src/`
