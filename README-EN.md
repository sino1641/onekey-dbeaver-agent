[中文说明](README.md)

# DBeaver Agent Onekey Script

## About This Project

This project is forked from [wgzhao/dbeaver-agent](https://github.com/wgzhao/dbeaver-agent), with the following enhancements:

- ✅ **One-Click Deployment Script (onekey.py)**: Automates the entire workflow including dependency discovery, compilation, deployment, and configuration
- ✅ **Multi-Environment Testing**: Tested across multiple platforms (Windows, macOS, Linux RHEL/Ubuntu/ARM) and JDK distributions
- ✅ **Agent Code Synchronization**: Core Agent code is kept in sync with the upstream repository

## Disclaimer

This Java Agent is for educational and research purposes only. Please delete it within 24 hours after downloading and support the official version: https://dbeaver.com/buy

## Tested Versions

- `25.2`
- `25.1`

## Quick Start 🚀

### Method 1: One-Click Auto Deployment (Recommended)

Use the Python automation script `onekey.py` to complete all configurations with a single command:

```bash
# Provide DBeaver installation path as parameter
python onekey.py "C:\Program Files\DBeaver"           # Windows
python onekey.py "/Applications/DBeaver.app"          # macOS
python onekey.py "/usr/share/dbeaver"                 # Linux

# Linux: If DBeaver is installed in a system directory (e.g., /usr/share/dbeaver), use sudo
sudo python3 onekey.py "/usr/share/dbeaver"

# Or run without parameters for interactive input
python onekey.py
```

**The script will automatically:**
1. ✅ Extract version info and product ID from DBeaver installation
2. ✅ Find and copy dependency jar files to `libs` directory
3. ✅ Auto-update version numbers and dependency paths in `pom.xml`
4. ✅ Compile the project (using Maven)
5. ✅ Deploy agent jar to DBeaver plugins directory
6. ✅ Auto-generate license key and copy to clipboard
7. ✅ Update `dbeaver.ini` configuration (add javaagent parameters)
8. ✅ Handle JRE dependencies (rename jre directory to force system JDK usage)
9. ✅ macOS: Auto-remove `-vm` parameter to use system JDK
10. ✅ Launch DBeaver

**Prerequisites:**
- Python 3.6+
- Maven (must be available in PATH)
- System JDK 21 (**JDK 21 is strongly recommended**)

**Linux Special Notes:**
- If DBeaver is installed in a directory requiring root privileges (e.g., `/usr/share/dbeaver`), run the script with `sudo`
- The script will automatically launch DBeaver as the current user (via `sudo -u` privilege dropping)
- **License key will NOT be automatically copied to clipboard**; please manually copy the license displayed in the terminal after completion

---

### Method 2: Manual Deployment

If you prefer to control each step manually, follow these instructions.

#### 1. Prepare Dependencies

From the `plugins` folder in your DBeaver installation directory, copy the following jar files to the `libs` directory in this project:

- `com.dbeaver.lm.api_*.jar` - License management API
- `org.jkiss.utils_*.jar` - Utility library

#### 2. Update pom.xml

Update the dependency versions and filenames in `pom.xml` according to the jar files you copied.

#### 3. Build the Project

Use Maven to build the project and generate a jar file with all dependencies:

```bash
mvn clean package
```

The generated file will be at `target/dbeaver-agent-{version}-jar-with-dependencies.jar`.

#### 4. Install DBeaver Agent

Copy the generated jar file to the `plugins` folder in your DBeaver installation directory, and rename it to `dbeaver-agent.jar`:

**Windows:**
```cmd
copy target\dbeaver-agent-*-jar-with-dependencies.jar "C:\Program Files\DBeaver\plugins\dbeaver-agent.jar"
```

**macOS:**
```bash
cp target/dbeaver-agent-*-jar-with-dependencies.jar "/Applications/DBeaver.app/Contents/Eclipse/plugins/dbeaver-agent.jar"
```

**Linux:**
```bash
cp target/dbeaver-agent-*-jar-with-dependencies.jar /usr/share/dbeaver/plugins/dbeaver-agent.jar
```

#### 5. Configure dbeaver.ini

Modify the `dbeaver.ini` file in your DBeaver installation directory (on macOS, it's at `Contents/Eclipse/dbeaver.ini`), and add the following below `-vmargs`:

```ini
-vmargs
-javaagent:plugins/dbeaver-agent.jar
-Dlm.debug.mode=true
```

**macOS Special Note:**
- The javaagent path should be: `-javaagent:../Eclipse/plugins/dbeaver-agent.jar`
- If there's a `-vm` parameter, please remove it along with its next line (JRE path)

**Windows CLI Users:**
- To use `dbeaver-cli.exe` for detailed logs, copy `dbeaver.ini` to `dbeaver-cli.ini`

#### 6. Handle JRE Dependencies

**It's strongly recommended to use system JDK 21** instead of DBeaver's built-in JRE:

- **Install JDK 21**: Verify after installation: `java -version` (should show Java 21)

- **Rename jre directory**: Rename the `jre` folder in your DBeaver installation directory to `jr` (or any other name), so DBeaver will automatically use the system JDK.
- **macOS**: Remove the `-vm` parameter from `dbeaver.ini` (if it exists).

#### 7. Activate License and Disable Data Sharing

After starting DBeaver for the first time:

1. Click **Import license**
2. Paste the generated license key
3. Click the **Import** button to activate
4. **Important**: After activation, check **"Do not share data"**

Additionally, to prevent DBeaver from sending data to `stats.dbeaver.com`, modify your hosts file:

```
127.0.0.1 stats.dbeaver.com
```

---

## Generate License Key

### Command Line Interface (CLI)

Use the `gen-license` script to generate licenses directly from the plugins directory in your DBeaver installation:

```bash
# Linux/macOS
./gen-license.sh [OPTIONS] [DBeaver_Path]

# Windows
gen-license.bat [OPTIONS] [DBeaver_Path]
```

**Arguments:**
- `[DBeaver_Path]`: Path to DBeaver installation directory or executable (optional)
  - If not provided, the script will enter interactive mode and prompt for input
  - Can be a directory (e.g., `C:\Program Files\DBeaver`)
  - Or an executable file (e.g., `g:\Portable\dbeaver\dbeaver.exe`)

**Optional Parameters:**
- `-h, --help`: Show help message
- `-t, --type=<type>`: License type
  - `le`: Lite Edition
  - `ee`: Enterprise Edition
  - `ue`: Ultimate Edition
  - If not specified, the script will try to read from `.eclipseproduct` file, or prompt for input
- `-v, --version=<version>`: Product version (e.g., `25`)
  - If not specified, the script will try to read from `.eclipseproduct` file, or prompt for input

**Examples:**

```bash
# Interactive mode (no path or parameters, script will auto-read or prompt)
./gen-license.sh                                                # Linux/macOS
gen-license.bat                                                 # Windows

# Command line mode (provide path, auto-read version and product type)
./gen-license.sh "/Applications/DBeaver.app"                    # macOS
./gen-license.sh "/usr/share/dbeaver"                           # Linux
gen-license.bat "C:\Program Files\DBeaver"                      # Windows
gen-license.bat "C:\Program Files\DBeaver\dbeaver.exe"         # Windows (executable)

# Specify license type and version (override auto-read)
./gen-license.sh -t ee -v 24 "/usr/share/dbeaver"              # Linux
gen-license.bat -t ee -v 24 "C:\Program Files\DBeaver"         # Windows
```

**Important Notes:**
- ⚠️ Before using this script, you must deploy the agent using `onekey.py` or manually
- ⚠️ The script executes in DBeaver's plugins directory, using the deployed dbeaver-agent.jar
- ℹ️ The script will automatically read product type and version from `.eclipseproduct` file

---

## FAQ

### Q: What version of JDK should I use?

A: **JDK 21 is strongly recommended**. Reasons:
- DBeaver 25.x has the best compatibility with JDK 21
- The agent requires newer Java features
- Verify after installation: `java -version`

### Q: License not working after starting DBeaver?

A: It's recommended to start DBeaver from the command line to see detailed logs:

```bash
# Windows
"C:\Program Files\DBeaver\dbeaver.exe"
# Or use CLI version for detailed logs
"C:\Program Files\DBeaver\dbeaver-cli.exe"

# macOS
open /Applications/DBeaver.app

# Linux
/usr/share/dbeaver/dbeaver
```

**Windows Tip**: The onekey.py script automatically creates `dbeaver-cli.ini`, making it easy to use `dbeaver-cli.exe` to view detailed logs.

Check the console output for agent loading success messages. Also ensure the license is activated and "Do not share data" is checked.

### Q: Maven build fails?

A: Make sure:
1. Maven is properly installed and available in PATH (run `mvn -version` to check)
2. **JDK 21 is installed** (run `java -version` to check)
3. Required jar files are correctly copied to the `libs` directory
4. Version numbers and filenames in `pom.xml` match the actual files

### Q: DBeaver fails to start on macOS?

A: Check:
1. Whether the `-vm` parameter has been correctly removed from `dbeaver.ini`
2. **Whether JDK 21 is installed on the system** (run `java -version` to check)
3. Whether the javaagent path in `dbeaver.ini` is correct (should be `../Eclipse/plugins/dbeaver-agent.jar`)

### Q: Auto-deployment script fails?

A: The `onekey.py` script provides detailed error messages and progress indicators. Common issues:
- Ensure the provided DBeaver path is correct
- Ensure Maven is installed
- **Ensure JDK 21 is installed on the system**
- Linux: If DBeaver is installed in a system directory, ensure you run the script with `sudo`
- Review the detailed error messages in the script output

### Q: Why isn't the license automatically copied to clipboard on Linux?

A: Due to environment variable configuration issues with clipboard tools (wl-copy, xclip, etc.) when running scripts with `sudo` on Linux, the script does not automatically copy the license. After deployment completes, the license key will be displayed in the terminal for manual copying:

```
--- LICENSE ---
[License key displayed here]
--- END LICENSE ---
```

Then paste it into the "Import license" dialog in DBeaver.

---

## Supported Products

- ✅ **DBeaver Ultimate Edition** (UE)
- ✅ **DBeaver Enterprise Edition** (EE)
- ✅ **DBeaver Lite Edition** (LE)

> **Note**: For CloudBeaver support, please see upstream issue [#10](https://github.com/wgzhao/dbeaver-agent/issues/10).
>
> Personal recommendation: Please support the official version at https://dbeaver.com/buy/#cloudbeaver

## Tested Systems and Dependencies

| Operating System | Version | JDK | Status |
|-----------------|---------|-----|--------|
| Windows | 11 25H2 | Microsoft Build of OpenJDK 21 | ✅ |
| RHEL | 10 | Red Hat Build of OpenJDK 21 | ✅ |
| Ubuntu on EC2 Graviton | 24.04 | Amazon Corretto 21 | ✅ |
| macOS | 26.0 | Zulu 21 | ✅ |
