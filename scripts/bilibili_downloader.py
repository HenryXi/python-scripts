#!/usr/bin/env python3
"""
B站 UP 主视频批量下载脚本（纯 Python 实现）

用法:
    python bilibili_downloader.py <UP主UID> [选项]

示例:
    python bilibili_downloader.py 12345678
    python bilibili_downloader.py 12345678 --quality 1080p
    python bilibili_downloader.py 12345678 --cookies cookies.txt
"""

import argparse
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

# 跳过 SSL 证书验证
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

# 请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://www.bilibili.com",
}


def check_ffmpeg():
    """检查 ffmpeg 是否已安装"""
    if not shutil.which("ffmpeg"):
        print("错误: 未找到 ffmpeg，请先安装：")
        print("  brew install ffmpeg")
        sys.exit(1)


def load_cookies(cookies_file):
    """加载 cookies 文件（Netscape 格式）"""
    if not cookies_file or not os.path.exists(cookies_file):
        return ""

    cookies = []
    with open(cookies_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 7:
                cookies.append(f"{parts[5]}={parts[6]}")
    return "; ".join(cookies)


def get_user_info(mid):
    """获取 UP 主基本信息"""
    url = f"https://api.bilibili.com/x/space/wbi/acc/info?mid={mid}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10, context=ssl_ctx) as resp:
            data = json.loads(resp.read().decode())
        if data.get("code") == 0:
            return data["data"]
    except Exception:
        pass
    return {}


def get_all_videos(mid, cookies=""):
    """获取 UP 主所有视频列表"""
    print(f"正在获取 UP 主 {mid} 的视频列表...")

    videos = []
    page = 1
    page_size = 30

    headers = HEADERS.copy()
    if cookies:
        headers["Cookie"] = cookies

    while True:
        url = f"https://api.bilibili.com/x/space/wbi/arc/search?mid={mid}&pn={page}&ps={page_size}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10, context=ssl_ctx) as resp:
                data = json.loads(resp.read().decode())

            if data.get("code") != 0:
                break

            vlist = data["data"]["list"]["vlist"]
            if not vlist:
                break

            videos.extend(vlist)
            print(f"  已获取 {len(videos)} 个视频...")

            if len(vlist) < page_size:
                break

            page += 1
            time.sleep(0.5)
        except Exception as e:
            print(f"获取视频列表失败: {e}")
            break

    return videos


def get_video_playurl(bvid, quality, cookies=""):
    """获取视频播放地址"""
    # 先获取 cid
    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    headers = HEADERS.copy()
    if cookies:
        headers["Cookie"] = cookies

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10, context=ssl_ctx) as resp:
            data = json.loads(resp.read().decode())
        if data.get("code") != 0:
            return None
        cid = data["data"]["cid"]
        title = data["data"]["title"]
    except Exception as e:
        print(f"  获取视频信息失败: {e}")
        return None

    # 获取播放地址
    qn_map = {"best": 127, "1080p": 80, "720p": 64, "480p": 32}
    qn = qn_map.get(quality, 127)

    url = f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn={qn}&fnval=16"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10, context=ssl_ctx) as resp:
            data = json.loads(resp.read().decode())
        if data.get("code") != 0:
            return None

        durl = data["data"].get("durl")
        dash = data["data"].get("dash")

        if dash:  # DASH 格式（音视频分离）
            video_url = dash["video"][0]["baseUrl"] if dash.get("video") else None
            audio_url = dash["audio"][0]["baseUrl"] if dash.get("audio") else None
            return {"title": title, "video": video_url, "audio": audio_url, "type": "dash"}
        elif durl:  # FLV 格式（音视频合一）
            return {"title": title, "url": durl[0]["url"], "type": "flv"}
    except Exception as e:
        print(f"  获取播放地址失败: {e}")

    return None


def download_file(url, output_path, cookies=""):
    """下载文件"""
    headers = HEADERS.copy()
    if cookies:
        headers["Cookie"] = cookies

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30, context=ssl_ctx) as resp:
            total_size = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 1024 * 1024  # 1MB

            with open(output_path, "wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = downloaded * 100 / total_size
                        print(f"\r    下载进度: {percent:.1f}%", end="", flush=True)
            print()
        return True
    except Exception as e:
        print(f"\n    下载失败: {e}")
        return False


def merge_video_audio(video_path, audio_path, output_path):
    """使用 ffmpeg 合并视频和音频"""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c", "copy",
        output_path,
        "-loglevel", "error"
    ]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0


def sanitize_filename(name):
    """清理文件名中的非法字符"""
    return re.sub(r'[\\/:*?"<>|]', "_", name)


def download_video(bvid, title, output_dir, quality, cookies):
    """下载单个视频"""
    safe_title = sanitize_filename(title)
    output_path = os.path.join(output_dir, f"{safe_title}.mp4")

    if os.path.exists(output_path):
        print(f"  已存在，跳过: {safe_title}")
        return True

    play_info = get_video_playurl(bvid, quality, cookies)
    if not play_info:
        print(f"  无法获取播放地址，跳过")
        return False

    tmp_dir = os.path.join(output_dir, ".tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    if play_info["type"] == "dash":
        video_path = os.path.join(tmp_dir, f"{bvid}_video.m4s")
        audio_path = os.path.join(tmp_dir, f"{bvid}_audio.m4s")

        print(f"  下载视频流...")
        ok = download_file(play_info["video"], video_path, cookies)
        if not ok:
            return False

        print(f"  下载音频流...")
        ok = download_file(play_info["audio"], audio_path, cookies)
        if not ok:
            return False

        print(f"  合并音视频...")
        ok = merge_video_audio(video_path, audio_path, output_path)

        os.remove(video_path)
        os.remove(audio_path)

        if not ok:
            print(f"  合并失败")
            return False

    else:  # flv 格式直接下载
        print(f"  下载视频...")
        ok = download_file(play_info["url"], output_path, cookies)
        if not ok:
            return False

    print(f"  完成: {safe_title}.mp4")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="下载 B 站 UP 主的所有视频",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("mid", help="UP 主的 UID（数字 ID）")
    parser.add_argument(
        "--quality", "-q",
        default="best",
        choices=["best", "1080p", "720p", "480p"],
        help="视频画质（默认: best，即最高清晰度）",
    )
    parser.add_argument(
        "--cookies", "-c",
        default=None,
        help="cookies 文件路径（Netscape 格式，用于需要登录的内容）",
    )

    args = parser.parse_args()
    check_ffmpeg()

    cookies = load_cookies(args.cookies) if args.cookies else ""

    # 输出目录：脚本目录下的 downloads/<UP主ID>
    script_dir = Path(__file__).parent
    output_dir = str(script_dir / "downloads" / args.mid)

    # 获取 UP 主信息
    info = get_user_info(args.mid)
    if info:
        up_name = info.get("name", "未知")
        print(f"UP 主: {up_name} (UID: {args.mid})")
        output_dir = str(script_dir / "downloads" / sanitize_filename(up_name))
    else:
        print(f"UID: {args.mid}（无法获取用户信息，继续下载）")

    os.makedirs(output_dir, exist_ok=True)
    print(f"下载目录: {output_dir}")
    print(f"目标画质: {args.quality}")

    # 获取所有视频
    videos = get_all_videos(args.mid, cookies)
    if not videos:
        print("未找到任何视频，退出")
        sys.exit(0)

    print(f"\n共找到 {len(videos)} 个视频，开始下载...")
    print("-" * 50)

    success = 0
    failed = 0
    for i, video in enumerate(videos, 1):
        bvid = video["bvid"]
        title = video["title"]
        print(f"\n[{i}/{len(videos)}] {title}")

        ok = download_video(bvid, title, output_dir, args.quality, cookies)
        if ok:
            success += 1
        else:
            failed += 1

        time.sleep(1)  # 避免请求过快

    print("\n" + "=" * 50)
    print(f"下载完成: 成功 {success} 个，失败 {failed} 个")
    print(f"文件保存在: {output_dir}")


if __name__ == "__main__":
    main()
