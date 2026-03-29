#!/usr/bin/env python3
"""
微信媒体文件完整整理工具
执行顺序：复制 → MD5去重 → 重命名.pic → 删除缩略图

使用方法：
    python3 backup_wechat_favorites.py <微信用户ID>

示例：
    python3 backup_wechat_favorites.py wxid_7cvwwmh4twq221_1442
"""

import os
import sys
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from PIL import Image
import imagehash


def calculate_md5(file_path):
    """计算文件的MD5值"""
    md5_hash = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def copy_files(source_paths, dest_dir):
    """步骤1: 从源路径复制文件"""
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied = 0

    for source_path in source_paths:
        if not source_path.exists():
            print(f"警告: 源路径不存在: {source_path}")
            continue

        print(f"正在复制: {source_path}")
        for file in source_path.rglob('*'):
            if file.is_file():
                dest_file = dest_dir / file.name
                counter = 1
                while dest_file.exists():
                    dest_file = dest_dir / f"{file.stem}_{counter}{file.suffix}"
                    counter += 1
                shutil.copy2(file, dest_file)
                copied += 1

    print(f"已复制 {copied} 个文件\n")
    return copied


def remove_duplicates(directory):
    """步骤2: MD5去重"""
    md5_dict = defaultdict(list)

    print("正在计算文件MD5...")
    for file in directory.glob('*'):
        if file.is_file():
            md5 = calculate_md5(file)
            md5_dict[md5].append(file)

    deleted = 0
    for md5, files in md5_dict.items():
        if len(files) > 1:
            for file in files[1:]:
                file.unlink()
                deleted += 1

    print(f"已删除 {deleted} 个重复文件\n")
    return deleted


def rename_pic_files(directory):
    """步骤3: 重命名.pic文件为.jpeg"""
    renamed = 0
    for file in directory.glob('*.pic'):
        new_name = file.with_suffix('.jpeg')
        counter = 1
        while new_name.exists():
            new_name = file.parent / f"{file.stem}_{counter}.jpeg"
            counter += 1
        file.rename(new_name)
        renamed += 1

    print(f"已重命名 {renamed} 个.pic文件\n")
    return renamed


def remove_thumbnails(directory):
    """步骤4: 智能删除缩略图（保留文件大小最大的）"""
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}

    images_info = []
    print("正在分析图片...")
    for file in directory.glob('*'):
        if file.suffix.lower() in image_extensions and file.is_file():
            try:
                with Image.open(file) as img:
                    phash = imagehash.phash(img)
                    size_kb = file.stat().st_size / 1024
                    images_info.append({
                        'file': file,
                        'hash': phash,
                        'pixels': img.width * img.height,
                        'size_kb': size_kb
                    })
            except:
                pass

    # 按感知哈希分组
    groups = defaultdict(list)
    for info in images_info:
        groups[str(info['hash'])].append(info)

    # 标记要保留的文件
    keep_files = set()

    for hash_val, images in groups.items():
        # 无论单独还是多张，都保留文件大小最大的
        images.sort(key=lambda x: x['size_kb'], reverse=True)
        keep_files.add(images[0]['file'])

    # 删除未标记保留的文件
    deleted = 0
    for info in images_info:
        if info['file'] not in keep_files:
            info['file'].unlink()
            deleted += 1

    print(f"已删除 {deleted} 个缩略图\n")
    return deleted



def main():
    if len(sys.argv) < 2:
        print("用法: python3 backup_wechat_favorites.py <微信用户ID>")
        print("示例: python3 backup_wechat_favorites.py wxid_7cvwwmh4twq221_1442")
        sys.exit(1)

    wxid = sys.argv[1]
    base_path = Path(f"/Users/yong/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/{wxid}")

    source_paths = [
        base_path / "temp/ImageUtils",
        base_path / "business/favorite/temp"
    ]

    date_str = datetime.now().strftime("%Y%m%d")
    dest_dir = Path(f"/Users/yong/Downloads/{date_str}")

    # 如果目标目录已存在，先删除
    if dest_dir.exists():
        print(f"删除旧目录: {dest_dir}")
        shutil.rmtree(dest_dir)
        print()

    print(f"目标目录: {dest_dir}\n")
    print("=" * 50)

    print("\n步骤1: 复制文件")
    copy_files(source_paths, dest_dir)

    print("步骤2: MD5去重")
    remove_duplicates(dest_dir)

    print("步骤3: 重命名.pic文件")
    rename_pic_files(dest_dir)

    print("步骤4: 删除缩略图")
    remove_thumbnails(dest_dir)

    print("=" * 50)
    print(f"\n完成！文件已整理到: {dest_dir}")


if __name__ == "__main__":
    main()







