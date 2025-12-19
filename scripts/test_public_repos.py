#!/usr/bin/env python
"""
测试公共仓库镜像同步功能的示例脚本。

演示如何使用新的 gitea_owner 参数来同步公共仓库。
"""

import requests
import json
from typing import Dict, Any

# 配置
API_BASE_URL = "http://localhost:8000/api"
GITHUB_REPO = "https://github.com/anthropics/claude-code.git"
GITEA_ORG = "my-organization"  # 可选：指定 Gitea 组织
REPO_NAME = "claude-code-mirror"


def print_section(title: str):
    """打印章节标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def add_repository_with_org(
    url: str,
    name: str,
    org: str = None
) -> Dict[str, Any]:
    """
    添加仓库到同步系统并指定 Gitea 组织。

    Args:
        url: GitHub 仓库 URL
        name: 镜像仓库名称
        org: 可选的 Gitea 组织名称

    Returns:
        API 响应数据
    """
    payload = {
        "name": name,
        "owner": "mirror",  # 默认所有者
        "url": url,
        "enabled": True,
    }

    # 如果指定了组织，添加到请求中
    if org:
        payload["gitea_owner"] = org
        print(f"📦 添加仓库到 Gitea 组织: {org}/{name}")
    else:
        print(f"📦 添加仓库到默认用户命名空间: {name}")

    print(f"   GitHub URL: {url}")

    try:
        response = requests.post(
            f"{API_BASE_URL}/repositories",
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        print(f"✅ 仓库已添加: {data.get('id')}")
        return data
    except requests.exceptions.RequestException as e:
        print(f"❌ 添加失败: {e}")
        raise


def get_repository(repo_id: int) -> Dict[str, Any]:
    """获取仓库信息"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/repositories/{repo_id}",
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ 获取仓库信息失败: {e}")
        raise


def sync_repository(repo_id: int) -> Dict[str, Any]:
    """同步仓库"""
    print(f"\n🔄 正在同步仓库 ID: {repo_id}")

    try:
        response = requests.post(
            f"{API_BASE_URL}/repositories/{repo_id}/sync",
            timeout=300  # 同步可能需要较长时间
        )
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "success":
            print(f"✅ 同步成功!")
            print(f"   操作类型: {data.get('operation_type')}")
            print(f"   耗时: {data.get('duration_seconds'):.2f}秒")
        else:
            print(f"❌ 同步失败: {data.get('error')}")

        return data
    except requests.exceptions.RequestException as e:
        print(f"❌ 同步请求失败: {e}")
        raise


def update_repository_org(repo_id: int, new_org: str) -> Dict[str, Any]:
    """更新仓库的 Gitea 组织"""
    payload = {
        "gitea_owner": new_org
    }

    print(f"\n📝 更新仓库 ID {repo_id} 的 Gitea 组织为: {new_org}")

    try:
        response = requests.put(
            f"{API_BASE_URL}/repositories/{repo_id}",
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        print(f"✅ 仓库已更新")
        print(f"   Gitea 组织: {data.get('gitea_owner')}")
        return data
    except requests.exceptions.RequestException as e:
        print(f"❌ 更新失败: {e}")
        raise


def main():
    """主函数"""
    print_section("GitHub 公共仓库镜像同步 - 测试演示")

    print("本示例演示如何使用新的公共仓库支持功能:\n")
    print("场景: 同步一个公共仓库到指定的 Gitea 组织\n")

    # 步骤 1: 添加仓库
    print_section("步骤 1: 添加仓库")

    try:
        repo_data = add_repository_with_org(
            url=GITHUB_REPO,
            name=REPO_NAME,
            org=GITEA_ORG  # 指定 Gitea 组织
        )
        repo_id = repo_data.get("id")

        if not repo_id:
            print("❌ 无法获取仓库 ID")
            return

        # 步骤 2: 获取仓库信息
        print_section("步骤 2: 获取仓库信息")

        repo_info = get_repository(repo_id)
        print(f"仓库信息:")
        print(json.dumps(repo_info, indent=2, ensure_ascii=False))

        # 步骤 3: 同步仓库
        print_section("步骤 3: 同步仓库")

        sync_result = sync_repository(repo_id)
        print(f"同步结果:")
        print(json.dumps(sync_result, indent=2, ensure_ascii=False))

        # 步骤 4: 更新 Gitea 组织
        print_section("步骤 4: 更新 Gitea 组织")

        new_org = "different-organization"
        updated_repo = update_repository_org(repo_id, new_org)
        print(f"更新后的仓库信息:")
        print(json.dumps(updated_repo, indent=2, ensure_ascii=False))

        # 完成
        print_section("测试完成")
        print("✅ 公共仓库镜像同步功能验证成功!\n")

    except Exception as e:
        print_section("错误信息")
        print(f"❌ 测试失败: {e}\n")
        return False

    return True


if __name__ == "__main__":
    import sys

    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  测试被中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 未预期的错误: {e}")
        sys.exit(1)
