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
from pathlib import Path


def check_maven_available():
    """
    检查 Maven 是否可用

    Returns:
        Maven 命令字符串，如果不可用则返回 None
    """
    maven_commands = ['mvn', 'mvn.cmd', 'mvn.bat']

    for cmd in maven_commands:
        try:
            # 明确传递环境变量
            env = os.environ.copy()
            result = subprocess.run(
                [cmd, '-version'],
                capture_output=True,
                text=True,
                shell=True,
                timeout=5,
                env=env  # 显式传递环境变量
            )
            if result.returncode == 0:
                print(f"  检测到 Maven: {cmd}")
                # 打印 Maven 版本信息的第一行
                first_line = result.stdout.split('\n')[0] if result.stdout else ''
                if first_line:
                    print(f"  版本: {first_line}")
                return cmd
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
            continue

    return None


def find_dbeaver_dir(input_path):
    """
    确定 DBeaver 的安装目录

    Args:
        input_path: 用户输入的路径（可以是目录或 dbeaver.exe 文件）

    Returns:
        DBeaver 安装目录的 Path 对象
    """
    path = Path(input_path.strip().strip('"\''))

    if not path.exists():
        raise FileNotFoundError(f"路径不存在: {path}")

    # 如果是文件，取其父目录
    if path.is_file():
        if path.name.lower() == 'dbeaver.exe':
            return path.parent
        else:
            raise ValueError(f"不是 dbeaver.exe 文件: {path}")

    # 如果是目录，检查是否包含 dbeaver.exe
    if path.is_dir():
        dbeaver_exe = path / 'dbeaver.exe'
        if dbeaver_exe.exists():
            return path
        else:
            raise FileNotFoundError(f"目录中未找到 dbeaver.exe: {path}")

    raise ValueError(f"无效的路径: {path}")


def read_version_from_eclipseproduct(dbeaver_dir):
    """
    从 .eclipseproduct 文件中读取版本号

    Args:
        dbeaver_dir: DBeaver 安装目录

    Returns:
        版本号字符串，例如 "25.2.0"
    """
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
        print("\n请确保 Maven 已正确安装并配置：")
        print("  1. 下载 Maven: https://maven.apache.org/download.cgi")
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
        # 明确传递环境变量
        env = os.environ.copy()

        result = subprocess.run(
            [maven_cmd, 'clean', 'package', '-DskipTests'],
            cwd=script_dir,
            capture_output=True,
            text=True,
            encoding='utf-8',
            shell=True,
            env=env  # 显式传递环境变量
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

    ini_file = dbeaver_dir / 'dbeaver.ini'

    if not ini_file.exists():
        raise FileNotFoundError(f"dbeaver.ini 文件不存在: {ini_file}")

    # 读取现有内容
    with open(ini_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 检查是否已存在配置
    javaagent_line = '-javaagent:plugins/dbeaver-agent.jar\n'
    debug_line = '-Dlm.debug.mode=true\n'

    has_javaagent = any(line.strip() == javaagent_line.strip() for line in lines)
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
        print(f"  - 已存在: {javaagent_line.strip()}")

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

    dbeaver_exe = dbeaver_dir / 'dbeaver.exe'

    if not dbeaver_exe.exists():
        raise FileNotFoundError(f"dbeaver.exe 不存在: {dbeaver_exe}")

    try:
        # 使用 Popen 启动，不等待进程结束
        subprocess.Popen([str(dbeaver_exe)], cwd=str(dbeaver_dir))
        print(f"✓ DBeaver 已启动")
    except Exception as e:
        print(f"✗ 启动失败: {e}")
        raise


def main():
    """主函数"""
    print("=" * 60)
    print("DBeaver Agent - 自动部署工具")
    print("=" * 60)

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
        print("  - 可以是目录路径，例如: G:\\Portable\\dbeaver")
        print("  - 也可以是 dbeaver.exe 文件路径，例如: G:\\Portable\\dbeaver\\dbeaver.exe")
        print()
        dbeaver_path = input("路径: ").strip()

    if not dbeaver_path:
        print("错误: 未提供路径")
        sys.exit(1)

    try:
        # 步骤1: 确定 DBeaver 目录
        print(f"\n[1/6] 正在处理: {dbeaver_path}")
        dbeaver_dir = find_dbeaver_dir(dbeaver_path)
        print(f"✓ DBeaver 目录: {dbeaver_dir}")

        # 步骤2: 读取版本号
        print(f"\n[2/6] 读取版本信息...")
        main_version = read_version_from_eclipseproduct(dbeaver_dir)
        print(f"✓ 检测到版本: {main_version}")

        # 步骤3: 查找并复制依赖 jar 文件
        print(f"\n[3/6] 从 plugins 目录查找依赖...")
        jar_info_list = find_and_copy_jars(dbeaver_dir, libs_dir)

        if not jar_info_list:
            print("警告: 未找到任何依赖 jar 文件")

        # 步骤4: 更新 pom.xml
        print(f"\n[4/6] 更新 pom.xml...")
        update_pom_xml(pom_file, main_version, jar_info_list)

        # 步骤5: 编译项目
        compiled_jar = compile_project(script_dir)

        # 步骤6: 部署到 DBeaver
        deploy_agent_to_dbeaver(compiled_jar, dbeaver_dir)

        # 步骤7: 更新配置文件
        update_dbeaver_ini(dbeaver_dir)

        # 步骤8: 启动 DBeaver
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
