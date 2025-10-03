#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DBeaver Agent 自动部署工具
1. 从 DBeaver 安装目录中提取版本信息和依赖 jar 文件
2. 更新 pom.xml
3. 编译项目
4. 复制产物到 DBeaver plugins 目录
5. 更新 dbeaver.ini 配置
6. 启动 DBeaver
"""

import os
import sys
import re
import shutil
import subprocess
import platform
from pathlib import Path


def check_maven_available():
    """
    检查 Maven 是否可用

    Returns:
        Maven 命令字符串，如果不可用则返回 None
    """
    system = platform.system()

    # 根据操作系统选择要测试的命令
    if system == 'Windows':
        maven_commands = ['mvn.cmd', 'mvn.bat', 'mvn']
    else:  # macOS 和 Linux
        maven_commands = ['mvn']

    for cmd in maven_commands:
        try:
            # Unix 系统上不使用 shell=True
            use_shell = (system == 'Windows')

            result = subprocess.run(
                [cmd, '-version'],
                capture_output=True,
                text=True,
                shell=use_shell,
                timeout=5,
                env=os.environ.copy()
            )
            if result.returncode == 0:
                print(f"  检测到 Maven: {cmd}")
                # 打印 Maven 版本信息的第一行
                first_line = result.stdout.split('\n')[0] if result.stdout else ''
                if first_line:
                    print(f"  版本: {first_line}")
                return cmd
        except FileNotFoundError:
            # 命令不存在，继续尝试下一个
            continue
        except subprocess.TimeoutExpired:
            print(f"  警告: {cmd} 命令超时")
            continue
        except Exception as e:
            # 其他错误，继续尝试
            continue

    return None


def find_dbeaver_dir(input_path):
    """
    确定 DBeaver 的安装目录

    Args:
        input_path: 用户输入的路径（可以是目录或可执行文件）

    Returns:
        DBeaver 安装目录的 Path 对象
    """
    path = Path(input_path.strip().strip('"\''))

    if not path.exists():
        raise FileNotFoundError(f"路径不存在: {path}")

    system = platform.system()

    # macOS 特殊处理：.app 包
    if system == 'Darwin':
        # 如果是 .app 目录
        if path.suffix == '.app' and path.is_dir():
            return path
        # 如果指向 .app 内部的文件
        if '.app/' in str(path) or '.app\\' in str(path):
            # 向上查找 .app 目录
            current = path
            while current.parent != current:
                if current.suffix == '.app':
                    return current
                current = current.parent
        # 检查是否在 Applications 目录下
        if path.is_dir():
            app_files = list(path.glob('DBeaver*.app'))
            if app_files:
                return app_files[0]
        raise ValueError(f"未找到 DBeaver.app: {path}")

    # Windows 和 Linux 处理
    if path.is_file():
        # Windows: dbeaver.exe
        # Linux: dbeaver 或其他可执行文件
        if system == 'Windows':
            if path.name.lower() == 'dbeaver.exe':
                return path.parent
            else:
                raise ValueError(f"不是 dbeaver.exe 文件: {path}")
        else:  # Linux
            if 'dbeaver' in path.name.lower():
                return path.parent
            else:
                raise ValueError(f"不是 dbeaver 可执行文件: {path}")

    # 如果是目录
    if path.is_dir():
        if system == 'Windows':
            dbeaver_exe = path / 'dbeaver.exe'
            if dbeaver_exe.exists():
                return path
            else:
                raise FileNotFoundError(f"目录中未找到 dbeaver.exe: {path}")
        else:  # Linux
            # 查找可执行文件
            dbeaver_bin = path / 'dbeaver'
            if dbeaver_bin.exists():
                return path
            else:
                raise FileNotFoundError(f"目录中未找到 dbeaver 可执行文件: {path}")

    raise ValueError(f"无效的路径: {path}")


def read_version_from_eclipseproduct(dbeaver_dir):
    """
    从 .eclipseproduct 文件中读取版本号

    Args:
        dbeaver_dir: DBeaver 安装目录

    Returns:
        版本号字符串，例如 "25.2.0"
    """
    system = platform.system()

    # 根据操作系统确定 .eclipseproduct 文件位置
    if system == 'Darwin':  # macOS
        # DBeaver.app/Contents/Eclipse/.eclipseproduct
        eclipseproduct_file = dbeaver_dir / 'Contents' / 'Eclipse' / '.eclipseproduct'
    else:  # Windows 和 Linux
        eclipseproduct_file = dbeaver_dir / '.eclipseproduct'

    if not eclipseproduct_file.exists():
        raise FileNotFoundError(f".eclipseproduct 文件不存在: {eclipseproduct_file}")

    with open(eclipseproduct_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找 version=25.2.0 这样的行
    match = re.search(r'version\s*=\s*([0-9]+\.[0-9]+\.[0-9]+)', content)
    if match:
        return match.group(1)
    else:
        raise ValueError(f".eclipseproduct 文件中未找到版本号")


def find_and_copy_jars(dbeaver_dir, libs_dir):
    """
    从 plugins 目录中查找并复制所需的 jar 文件到 libs 目录

    Args:
        dbeaver_dir: DBeaver 安装目录
        libs_dir: 目标 libs 目录

    Returns:
        包含 jar 信息的字典列表，每个字典包含 artifactId, version, filename
    """
    # 根据操作系统确定 plugins 目录位置
    system = platform.system()

    if system == 'Darwin':  # macOS
        # DBeaver.app/Contents/Eclipse/plugins
        plugins_dir = dbeaver_dir / 'Contents' / 'Eclipse' / 'plugins'
    else:  # Windows 和 Linux
        plugins_dir = dbeaver_dir / 'plugins'

    if not plugins_dir.exists():
        raise FileNotFoundError(f"plugins 目录不存在: {plugins_dir}")

    # 需要查找的 jar 文件模式
    patterns = [
        (r'com\.dbeaver\.lm\.api_(.+?)\.jar', 'api'),
        (r'org\.jkiss\.utils_(.+?)\.jar', 'utils'),
    ]

    jar_info_list = []

    for pattern, artifact_id in patterns:
        found = False
        for jar_file in plugins_dir.glob('*.jar'):
            match = re.match(pattern, jar_file.name)
            if match:
                full_version = match.group(1)  # 例如 3.0.9.202506090822
                # 提取主版本号（前三位）
                version_match = re.match(r'(\d+\.\d+\.\d+)', full_version)
                if version_match:
                    version = version_match.group(1)
                else:
                    version = full_version

                # 复制 jar 文件到 libs 目录
                libs_dir.mkdir(parents=True, exist_ok=True)
                target_file = libs_dir / jar_file.name

                if target_file.exists():
                    print(f"  删除旧文件: {target_file.name}")
                    target_file.unlink()

                print(f"  复制: {jar_file.name} -> libs/")
                shutil.copy2(jar_file, target_file)

                jar_info_list.append({
                    'artifactId': artifact_id,
                    'version': version,
                    'filename': jar_file.name
                })

                found = True
                break

        if not found:
            print(f"  警告: 未找到匹配的 jar 文件: {pattern}")

    return jar_info_list


def update_pom_xml(pom_file, main_version, jar_info_list):
    """
    更新 pom.xml 文件（使用文本替换，保持原有格式）

    Args:
        pom_file: pom.xml 文件路径
        main_version: 主版本号（从 .eclipseproduct 读取）
        jar_info_list: jar 文件信息列表
    """
    # 读取原始内容
    with open(pom_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 更新主版本号（第一个 <version> 标签）
    version_pattern = r'(<artifactId>dbeaver-agent</artifactId>\s*\n\s*<version>)([^<]+)(</version>)'
    match = re.search(version_pattern, content)
    if match:
        old_version = match.group(2)
        content = re.sub(version_pattern, r'\g<1>' + main_version + r'\g<3>', content, count=1)
        print(f"\n更新主版本号: {old_version} -> {main_version}")

    # 2. 更新依赖版本和路径
    for jar_info in jar_info_list:
        artifact_id = jar_info['artifactId']
        new_version = jar_info['version']
        new_filename = jar_info['filename']

        # 构建依赖块的正则表达式
        # 匹配从 <dependency> 到 </dependency> 且包含指定 artifactId 的块
        dependency_pattern = (
            r'(<dependency>\s*\n'
            r'\s*<groupId>[^<]+</groupId>\s*\n'
            r'\s*<artifactId>' + re.escape(artifact_id) + r'</artifactId>\s*\n'
            r'\s*<version>)([^<]+)(</version>\s*\n'
            r'\s*<scope>system</scope>\s*\n'
            r'\s*<systemPath>\$\{project\.basedir\}/libs/)([^<]+)(</systemPath>\s*\n'
            r'\s*</dependency>)'
        )

        match = re.search(dependency_pattern, content)
        if match:
            old_version = match.group(2)
            old_filename = match.group(4)

            # 替换版本号和文件路径
            content = re.sub(
                dependency_pattern,
                r'\g<1>' + new_version + r'\g<3>' + new_filename + r'\g<5>',
                content
            )

            print(f"更新 {artifact_id} 版本: {old_version} -> {new_version}")
            print(f"更新 {artifact_id} 路径: {old_filename} -> {new_filename}")

    # 写回文件（保持原有格式）
    with open(pom_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"\npom.xml 更新完成！")
def compile_project(script_dir):
    """
    编译 Maven 项目

    Args:
        script_dir: 项目根目录

    Returns:
        编译后的 jar 文件路径
    """
    print("\n" + "=" * 60)
    print("开始编译项目...")
    print("=" * 60)

    # 检查 Maven 是否可用
    maven_cmd = check_maven_available()

    if not maven_cmd:
        print("✗ 未找到 Maven 命令")
        system = platform.system()
        print("\n请确保 Maven 已正确安装并配置：")
        print("  1. 下载 Maven: https://maven.apache.org/download.cgi")

        if system == 'Darwin':  # macOS
            print("  2. macOS 推荐使用 Homebrew 安装:")
            print("     brew install maven")
            print("  3. 或手动安装后添加到 PATH:")
            print("     export PATH=/path/to/maven/bin:$PATH")
            print("  4. 验证安装: mvn -version")
        elif system == 'Linux':
            print("  2. Linux 使用包管理器安装:")
            print("     Ubuntu/Debian: sudo apt-get install maven")
            print("     CentOS/RHEL: sudo yum install maven")
            print("     Fedora: sudo dnf install maven")
            print("  3. 或手动安装后添加到 PATH:")
            print("     export PATH=/path/to/maven/bin:$PATH")
            print("  4. 验证安装: mvn -version")
        else:  # Windows
            print("  2. 解压到某个目录，例如: C:\\Program Files\\Apache\\maven")
            print("  3. 添加环境变量:")
            print("     - MAVEN_HOME = C:\\Program Files\\Apache\\maven")
            print("     - 在 PATH 中添加: %MAVEN_HOME%\\bin")
            print("  4. 打开新的命令行窗口，执行: mvn -version")

        print("  5. 重新运行此脚本")
        raise RuntimeError("未找到 Maven 命令")

    print(f"✓ 使用 Maven 命令: {maven_cmd}")

    # 执行 mvn clean package
    try:
        system = platform.system()
        use_shell = (system == 'Windows')

        result = subprocess.run(
            [maven_cmd, 'clean', 'package', '-DskipTests'],
            cwd=script_dir,
            capture_output=True,
            text=True,
            encoding='utf-8',
            shell=use_shell,
            env=os.environ.copy()
        )

        if result.returncode == 0:
            print("✓ 编译成功！")
            # 查找编译产物
            target_dir = script_dir / 'target'
            jar_pattern = '*-jar-with-dependencies.jar'
            jar_files = list(target_dir.glob(jar_pattern))

            if jar_files:
                jar_file = jar_files[0]
                print(f"✓ 找到产物: {jar_file.name}")
                return jar_file
            else:
                raise FileNotFoundError(f"未找到编译产物: {jar_pattern}")
        else:
            print("✗ 编译失败！")
            print("\n=== Maven 输出 ===")
            print(result.stdout)
            if result.stderr:
                print("\n=== 错误信息 ===")
                print(result.stderr)
            raise RuntimeError("Maven 编译失败")

    except Exception as e:
        print(f"✗ 编译过程出错: {e}")
        raise


def deploy_agent_to_dbeaver(jar_file, dbeaver_dir):
    """
    将编译好的 agent jar 复制到 DBeaver plugins 目录

    Args:
        jar_file: 编译产物 jar 文件路径
        dbeaver_dir: DBeaver 安装目录

    Returns:
        部署后的 jar 文件路径
    """
    print("\n" + "=" * 60)
    print("部署 agent 到 DBeaver...")
    print("=" * 60)

    # 根据操作系统确定 plugins 目录位置
    system = platform.system()

    if system == 'Darwin':  # macOS
        plugins_dir = dbeaver_dir / 'Contents' / 'Eclipse' / 'plugins'
    else:  # Windows 和 Linux
        plugins_dir = dbeaver_dir / 'plugins'

    if not plugins_dir.exists():
        raise FileNotFoundError(f"plugins 目录不存在: {plugins_dir}")

    target_jar = plugins_dir / 'dbeaver-agent.jar'

    # 删除旧文件
    if target_jar.exists():
        print(f"  删除旧文件: {target_jar}")
        target_jar.unlink()

    # 复制新文件
    print(f"  复制: {jar_file.name} -> {target_jar}")
    shutil.copy2(jar_file, target_jar)

    print(f"✓ 部署完成: {target_jar}")
    return target_jar


def update_dbeaver_ini(dbeaver_dir):
    """
    更新 dbeaver.ini 文件，添加 javaagent 和 debug 参数

    Args:
        dbeaver_dir: DBeaver 安装目录
    """
    print("\n" + "=" * 60)
    print("更新 dbeaver.ini...")
    print("=" * 60)

    system = platform.system()

    # 根据操作系统确定 ini 文件位置和 javaagent 路径
    if system == 'Darwin':  # macOS
        # DBeaver.app/Contents/Eclipse/dbeaver.ini
        ini_file = dbeaver_dir / 'Contents' / 'Eclipse' / 'dbeaver.ini'
        javaagent_path = '../Eclipse/plugins/dbeaver-agent.jar'
    else:  # Windows 和 Linux
        ini_file = dbeaver_dir / 'dbeaver.ini'
        javaagent_path = 'plugins/dbeaver-agent.jar'

    if not ini_file.exists():
        raise FileNotFoundError(f"dbeaver.ini 文件不存在: {ini_file}")

    # 读取现有内容
    with open(ini_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 检查是否已存在配置
    javaagent_line = f'-javaagent:{javaagent_path}\n'
    debug_line = '-Dlm.debug.mode=true\n'

    has_javaagent = any(javaagent_path in line for line in lines)
    has_debug = any(line.strip() == debug_line.strip() for line in lines)

    # 找到 -vmargs 的位置
    vmargs_index = -1
    for i, line in enumerate(lines):
        if line.strip() == '-vmargs':
            vmargs_index = i
            break

    if vmargs_index == -1:
        print("  警告: 未找到 -vmargs 行，将在文件末尾添加")
        lines.append('-vmargs\n')
        vmargs_index = len(lines) - 1

    # 添加配置（如果不存在）
    insert_index = vmargs_index + 1
    modified = False

    if not has_javaagent:
        lines.insert(insert_index, javaagent_line)
        print(f"  ✓ 添加: {javaagent_line.strip()}")
        insert_index += 1
        modified = True
    else:
        print(f"  - 已存在: javaagent 配置")

    if not has_debug:
        lines.insert(insert_index, debug_line)
        print(f"  ✓ 添加: {debug_line.strip()}")
        modified = True
    else:
        print(f"  - 已存在: {debug_line.strip()}")

    # 写回文件
    if modified:
        with open(ini_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"✓ dbeaver.ini 更新完成")
    else:
        print(f"✓ dbeaver.ini 无需更新")


def start_dbeaver(dbeaver_dir):
    """
    启动 DBeaver

    Args:
        dbeaver_dir: DBeaver 安装目录
    """
    print("\n" + "=" * 60)
    print("启动 DBeaver...")
    print("=" * 60)

    system = platform.system()

    if system == 'Darwin':  # macOS
        # 使用 open 命令启动 .app
        try:
            subprocess.Popen(['open', str(dbeaver_dir)])
            print(f"✓ DBeaver 已启动")
        except Exception as e:
            print(f"✗ 启动失败: {e}")
            raise
    elif system == 'Windows':
        dbeaver_exe = dbeaver_dir / 'dbeaver.exe'
        if not dbeaver_exe.exists():
            raise FileNotFoundError(f"dbeaver.exe 不存在: {dbeaver_exe}")
        try:
            subprocess.Popen([str(dbeaver_exe)], cwd=str(dbeaver_dir))
            print(f"✓ DBeaver 已启动")
        except Exception as e:
            print(f"✗ 启动失败: {e}")
            raise
    else:  # Linux
        dbeaver_bin = dbeaver_dir / 'dbeaver'
        if not dbeaver_bin.exists():
            raise FileNotFoundError(f"dbeaver 不存在: {dbeaver_bin}")
        try:
            subprocess.Popen([str(dbeaver_bin)], cwd=str(dbeaver_dir))
            print(f"✓ DBeaver 已启动")
        except Exception as e:
            print(f"✗ 启动失败: {e}")
            raise


def main():
    """主函数"""
    print("=" * 60)
    print("DBeaver Agent - 自动部署工具")
    print("=" * 60)

    system = platform.system()
    print(f"检测到操作系统: {system}")

    # 获取脚本所在目录（项目根目录）
    script_dir = Path(__file__).parent.absolute()
    pom_file = script_dir / 'pom.xml'
    libs_dir = script_dir / 'libs'

    # 检查 pom.xml 是否存在
    if not pom_file.exists():
        print(f"错误: 找不到 pom.xml 文件: {pom_file}")
        sys.exit(1)

    # 获取 DBeaver 路径
    dbeaver_path = None

    # 检查是否有命令行参数
    if len(sys.argv) > 1:
        dbeaver_path = sys.argv[1]
    else:
        # 交互式输入
        print("\n请输入 DBeaver 路径：")
        if system == 'Darwin':
            print("  - macOS: /Applications/DBeaver.app 或 /Applications/DBeaverUltimate.app")
        elif system == 'Windows':
            print("  - Windows: C:\\Program Files\\DBeaver 或 dbeaver.exe 路径")
        else:
            print("  - Linux: /opt/dbeaver 或 dbeaver 可执行文件路径")
        print()
        dbeaver_path = input("路径: ").strip()

    if not dbeaver_path:
        print("错误: 未提供路径")
        sys.exit(1)

    try:
        # 步骤1: 确定 DBeaver 目录
        print(f"\n[1/8] 正在处理: {dbeaver_path}")
        dbeaver_dir = find_dbeaver_dir(dbeaver_path)
        print(f"✓ DBeaver 目录: {dbeaver_dir}")

        # 步骤2: 读取版本号
        print(f"\n[2/8] 读取版本信息...")
        main_version = read_version_from_eclipseproduct(dbeaver_dir)
        print(f"✓ 检测到版本: {main_version}")

        # 步骤3: 查找并复制依赖 jar 文件
        print(f"\n[3/8] 从 plugins 目录查找依赖...")
        jar_info_list = find_and_copy_jars(dbeaver_dir, libs_dir)

        if not jar_info_list:
            print("警告: 未找到任何依赖 jar 文件")

        # 步骤4: 更新 pom.xml
        print(f"\n[4/8] 更新 pom.xml...")
        update_pom_xml(pom_file, main_version, jar_info_list)

        # 步骤5: 编译项目
        print(f"\n[5/8] 编译项目...")
        compiled_jar = compile_project(script_dir)

        # 步骤6: 部署到 DBeaver
        print(f"\n[6/8] 部署到 DBeaver...")
        deploy_agent_to_dbeaver(compiled_jar, dbeaver_dir)

        # 步骤7: 更新配置文件
        print(f"\n[7/8] 更新配置文件...")
        update_dbeaver_ini(dbeaver_dir)

        # 步骤8: 启动 DBeaver
        print(f"\n[8/8] 启动 DBeaver...")
        start_dbeaver(dbeaver_dir)

        print("\n" + "=" * 60)
        print("✓ 所有步骤完成！DBeaver 已启动")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
