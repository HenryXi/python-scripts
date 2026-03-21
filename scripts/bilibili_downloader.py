#!/usr/bin/env python3
"""
B站 UP 主视频批量下载脚本

用法:
    python bilibili_downloader.py <UP主UID> [选项]

示例:
    python bilibili_downloader.py 12345678
    python bilibili_downloader.py 12345678 --output ~/Videos/bilibili
    python bilibili_downloader.py 12345678 --quality 1080p
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.parse


def check_yt_dlp():
    """检查 yt-dlp 是否已安装"""
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True)
    except FileNotFoundError:
        print("错误: 未找到 yt-dlp，请先安装：")
        print("  pip install yt-dlp")
        print("  或: brew install yt-dlp")
        sys.exit(1)


def get_user_info(mid: str) -> dict:
    """获取 UP 主基本信息"""
    url = f"https://api.bilibili.com/x/space/wbi/acc/info?mid={mid}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": "https://www.bilibili.com",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        if data.get("code") == 0:
            return data["data"]
    except Exception:
        pass
    return {}


def get_all_video_bvids(mid: str) -> list[str]:
    """获取 UP 主所有视频的 BV 号"""
    bvids = []
    page = 1
    page_size = 50

    print(f"正在获取 UP 主 {mid} 的视频列表...")

    while True:
        url = (
            f"https://api.bilibili.com/x/space/arc/search"
            f"?mid={mid}&pn={page}&ps={page_size}&tid=0&keyword=&order=pubdate"
        )
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": f"https://space.bilibili.com/{mid}",
        }
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
        except Exception as e:
            print(f"获取第 {page} 页失败: {e}")
            break

        if data.get("code") != 0:
            print(f"API 返回错误: {data.get('message', '未知错误')}")
            print("提示: 若持续失败，可能需要登录 cookie，请使用 --cookies 参数")
            break

        vlist = data.get("data", {}).get("list", {}).get("vlist", [])
        if not vlist:
            break

        for v in vlist:
            bvids.append(v["bvid"])

        total = data["data"]["page"]["count"]
        fetched = (page - 1) * page_size + len(vlist)
        print(f"  已获取 {fetched}/{total} 个视频")

        if fetched >= total:
            break

        page += 1
        time.sleep(0.5)  # 避免请求过快

    return bvids


def download_videos(bvids: list[str], output_dir: str, quality: str, cookies_file: str | None):
    """使用 yt-dlp 下载视频列表"""
    if not bvids:
        print("没有找到可下载的视频")
        return

    os.makedirs(output_dir, exist_ok=True)

    quality_map = {
        "best": "bestvideo+bestaudio/best",
        "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
    }
    format_str = quality_map.get(quality, quality_map["best"])

    print(f"\n开始下载 {len(bvids)} 个视频到 {output_dir}")
    print("-" * 50)

    for i, bvid in enumerate(bvids, 1):
        url = f"https://www.bilibili.com/video/{bvid}"
        print(f"\n[{i}/{len(bvids)}] 下载: {url}")

        cmd = [
            "yt-dlp",
            url,
            "--format", format_str,
            "--output", os.path.join(output_dir, "%(title)s.%(ext)s"),
            "--no-playlist",
            "--retries", "3",
            "--fragment-retries", "3",
        ]

        if cookies_file:
            cmd += ["--cookies", cookies_file]

        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"  警告: {bvid} 下载失败，继续下一个...")

    print("\n全部完成！")


def main():
    parser = argparse.ArgumentParser(
        description="下载 B 站 UP 主的所有视频",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("mid", help="UP 主的 UID（数字 ID）")
    parser.add_argument(
        "--output", "-o",
        default="./downloads",
        help="下载目录（默认: ./downloads）",
    )
    parser.add_argument(
        "--quality", "-q",
        default="best",
        choices=["best", "1080p", "720p", "480p"],
        help="视频画质（默认: best）",
    )
    parser.add_argument(
        "--cookies", "-c",
        default=None,
        help="cookies 文件路径（Netscape 格式，用于需要登录的内容）",
    )

    args = parser.parse_args()

    check_yt_dlp()

    # 获取 UP 主信息
    info = get_user_info(args.mid)
    if info:
        print(f"UP 主: {info.get('name', '未知')} (UID: {args.mid})")
    else:
        print(f"UID: {args.mid}（无法获取用户信息，继续下载）")

    # 获取所有视频 BV 号
    bvids = get_all_video_bvids(args.mid)
    if not bvids:
        print("未找到任何视频，退出")
        sys.exit(0)

    print(f"\n共找到 {len(bvids)} 个视频")

    # 下载
    download_videos(bvids, args.output, args.quality, args.cookies)


if __name__ == "__main__":
    main()
