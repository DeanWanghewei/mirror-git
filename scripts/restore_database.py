#!/usr/bin/env python3
"""
数据库恢复脚本

用于在升级后恢复旧的数据库数据。
"""

import shutil
import sys
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

def main():
    print("=" * 60)
    print("数据库恢复工具")
    print("=" * 60)
    print()

    # 数据库文件路径
    data_dir = PROJECT_ROOT / "data"
    old_db = data_dir / "sync.db"
    new_db = data_dir / "mirror_sync.db"

    print(f"数据目录: {data_dir}")
    print(f"旧数据库: {old_db} ({'存在' if old_db.exists() else '不存在'})")
    print(f"新数据库: {new_db} ({'存在' if new_db.exists() else '不存在'})")
    print()

    # 检查情况
    if not old_db.exists() and not new_db.exists():
        print("❌ 错误：没有找到任何数据库文件")
        print("   请确保您之前使用过该系统并生成了数据")
        return 1

    if old_db.exists() and not new_db.exists():
        print("✓ 情况1：只有旧数据库存在")
        print("  不需要恢复，系统会自动使用旧数据库 (sync.db)")
        return 0

    if not old_db.exists() and new_db.exists():
        print("⚠️  情况2：只有新数据库存在")
        print("   这可能是升级后创建的空数据库")
        print()
        response = input("是否要将新数据库重命名为旧数据库格式? (y/n): ")
        if response.lower() == 'y':
            backup = new_db.with_suffix('.db.backup')
            shutil.copy2(new_db, backup)
            print(f"✓ 已备份到: {backup}")
            shutil.move(new_db, old_db)
            print(f"✓ 已重命名: {new_db.name} -> {old_db.name}")
            print("✓ 完成！重启应用即可使用")
        else:
            print("已取消")
        return 0

    if old_db.exists() and new_db.exists():
        print("⚠️  情况3：新旧数据库都存在")
        print()

        # 比较大小
        old_size = old_db.stat().st_size
        new_size = new_db.stat().st_size

        print(f"旧数据库大小: {old_size:,} bytes")
        print(f"新数据库大小: {new_size:,} bytes")
        print()

        if old_size > new_size + 1000:  # 旧数据库明显更大
            print("✓ 检测到旧数据库包含更多数据")
            print()
            response = input("是否要使用旧数据库替换新数据库? (y/n): ")
            if response.lower() == 'y':
                # 备份新数据库
                backup = new_db.with_suffix('.db.new_backup')
                shutil.copy2(new_db, backup)
                print(f"✓ 新数据库已备份到: {backup}")

                # 删除新数据库
                new_db.unlink()
                print(f"✓ 已删除新数据库")

                print("✓ 完成！系统将使用旧数据库 (sync.db)")
                print("  重启应用即可恢复所有数据")
            else:
                print("已取消")
        else:
            print("ℹ️  两个数据库大小相近，或新数据库更大")
            print("   请手动检查并决定使用哪个数据库")
            print()
            print("选项:")
            print("1. 删除新数据库，使用旧数据库 (sync.db)")
            print("2. 删除旧数据库，使用新数据库 (mirror_sync.db)")
            print("3. 取消，保持现状")
            print()
            choice = input("请选择 (1/2/3): ")

            if choice == '1':
                backup = new_db.with_suffix('.db.new_backup')
                shutil.copy2(new_db, backup)
                new_db.unlink()
                print(f"✓ 新数据库已备份并删除")
                print("✓ 系统将使用旧数据库 (sync.db)")
            elif choice == '2':
                backup = old_db.with_suffix('.db.old_backup')
                shutil.copy2(old_db, backup)
                old_db.unlink()
                print(f"✓ 旧数据库已备份并删除")
                print("✓ 系统将使用新数据库 (mirror_sync.db)")
                print("⚠️  注意：需要设置环境变量 DATABASE_URL=sqlite:///app/data/mirror_sync.db")
            else:
                print("已取消")

        return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)
