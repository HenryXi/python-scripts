#!/usr/bin/env python3
"""
B站视频分集批量下载脚本（纯 Python 实现）

用法:
    python bilibili_by_bvid.py <BV号> [选项]

示例:
    python bilibili_by_bvid.py BV1P7411C7Gz --cookies cookies.txt
    python bilibili_by_bvid.py BV1P7411C7Gz --cookies cookies.txt --quality 1080p
    python bilibili_by_bvid.py BV1P7411C7Gz --cookies cookies.txt --concurrency 5
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import reduce
from pathlib import Path
from threading import Lock

# 跳过 SSL 证书验证
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

# 请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Origin": "https://www.bilibili.com",
}

# WBI 签名混淆表
_MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52,
]

print_lock = Lock()


def log(msg):
    with print_lock:
        print(msg)


def _get_mixin_key(orig):
    return reduce(lambda s, i: s + orig[i], _MIXIN_KEY_ENC_TAB, '')[:32]


def get_wbi_key(cookies):
    """从 nav 接口获取 WBI 签名所需的 mixin_key"""
    headers = HEADERS.copy()
    headers["Cookie"] = cookies
    req = urllib.request.Request("https://api.bilibili.com/x/web-interface/nav", headers=headers)
    with urllib.request.urlopen(req, timeout=10, context=ssl_ctx) as resp:
        data = json.loads(resp.read().decode())
    wbi = data["data"]["wbi_img"]
    img_key = wbi["img_url"].split("/")[-1].split(".")[0]
    sub_key = wbi["sub_url"].split("/")[-1].split(".")[0]
    return _get_mixin_key(img_key + sub_key)


def wbi_sign(params, mixin_key):
    """对请求参数进行 WBI 签名"""
    params["wts"] = int(time.time())
    params = dict(sorted(params.items()))
    query = "&".join(f"{k}={re.sub(r'[!()*]', '', str(v))}" for k, v in params.items())
    params["w_rid"] = hashlib.md5((query + mixin_key).encode()).hexdigest()
    return params


def check_ffmpeg():
    """检查 ffmpeg 是否已安装"""
    if not shutil.which("ffmpeg"):
        print("错误: 未找到 ffmpeg，请先安装：")
        print("  brew install ffmpeg")
        sys.exit(1)


def clean_tmp(tmp_dir):
    """清理未完成的下载临时文件"""
    if not os.path.exists(tmp_dir):
        return
    files = list(Path(tmp_dir).glob("*.m4s")) + list(Path(tmp_dir).glob("*.flv"))
    if files:
        print(f"清理 {len(files)} 个未完成的临时文件...")
        for f in files:
            f.unlink()


def load_cookies(cookies_file):
    """加载 cookies 文件（Netscape 格式）或直接返回 cookies 字符串"""
    if not cookies_file:
        return ""

    if os.path.exists(cookies_file):
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

    if not cookies_file.startswith("SESSDATA="):
        cookies_file = f"SESSDATA={cookies_file}"
    return cookies_file


def get_video_pages(bvid, cookies=""):
    """获取视频的所有分集信息"""
    print(f"正在获取视频 {bvid} 的分集信息...")

    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    headers = HEADERS.copy()
    if cookies:
        headers["Cookie"] = cookies

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10, context=ssl_ctx) as resp:
            data = json.loads(resp.read().decode())

        if data.get("code") != 0:
            print(f"  API 错误 ({data.get('code')}): {data.get('message', '未知错误')}")
            return None, []

        video_data = data["data"]
        title = video_data["title"]
        pages = video_data.get("pages", [])

        print(f"  视频标题: {title}")
        print(f"  共 {len(pages)} 个分集")

        return title, pages
    except Exception as e:
        print(f"  获取视频信息失败: {e}")
        return None, []


def get_video_playurl(bvid, cid, quality, cookies=""):
    """获取视频播放地址"""
    qn_map = {"best": 127, "1080p": 80, "720p": 64, "480p": 32}
    qn = qn_map.get(quality, 127)

    url = f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn={qn}&fnval=16"
    headers = HEADERS.copy()
    if cookies:
        headers["Cookie"] = cookies

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10, context=ssl_ctx) as resp:
            data = json.loads(resp.read().decode())
        if data.get("code") != 0:
            return None

        durl = data["data"].get("durl")
        dash = data["data"].get("dash")

        if dash:
            video_url = dash["video"][0]["baseUrl"] if dash.get("video") else None
            audio_url = dash["audio"][0]["baseUrl"] if dash.get("audio") else None
            return {"video": video_url, "audio": audio_url, "type": "dash"}
        elif durl:
            return {"url": durl[0]["url"], "type": "flv"}
    except Exception as e:
        log(f"  获取播放地址失败: {e}")

    return None


def download_file(url, output_path, cookies=""):
    """下载文件"""
    headers = HEADERS.copy()
    if cookies:
        headers["Cookie"] = cookies

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60, context=ssl_ctx) as resp:
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

    return True


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


def download_page(bvid, page, index, total, output_dir, quality, cookies):
    """下载单个分集（线程安全）"""
    page_num = page["page"]
    page_title = page["part"]
    cid = page["cid"]

    # 文件名格式：P1_分集标题.mp4
    safe_title = sanitize_filename(page_title)
    output_path = os.path.join(output_dir, f"P{page_num}_{safe_title}.mp4")

    if os.path.exists(output_path):
        log(f"[{index}/{total}] 已存在，跳过: P{page_num}_{safe_title}")
        return True

    log(f"[{index}/{total}] 开始下载: P{page_num} - {page_title}")

    play_info = get_video_playurl(bvid, cid, quality, cookies)
    if not play_info:
        log(f"[{index}/{total}] 失败: 无法获取播放地址 - P{page_num}")
        return False

    tmp_dir = os.path.join(output_dir, ".tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    try:
        if play_info["type"] == "dash":
            video_path = os.path.join(tmp_dir, f"{bvid}_p{page_num}_video.m4s")
            audio_path = os.path.join(tmp_dir, f"{bvid}_p{page_num}_audio.m4s")

            download_file(play_info["video"], video_path, cookies)
            download_file(play_info["audio"], audio_path, cookies)

            ok = merge_video_audio(video_path, audio_path, output_path)
            os.remove(video_path)
            os.remove(audio_path)

            if not ok:
                log(f"[{index}/{total}] 失败: 音视频合并失败 - P{page_num}")
                return False
        else:
            download_file(play_info["url"], output_path, cookies)

    except Exception as e:
        log(f"[{index}/{total}] 失败: {e} - P{page_num}")
        return False

    log(f"[{index}/{total}] 完成: P{page_num}_{safe_title}.mp4")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="下载 B 站视频的所有分集",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("bvid", help="视频的 BV 号（如 BV1P7411C7Gz）")
    parser.add_argument(
        "--quality", "-q",
        default="best",
        choices=["best", "1080p", "720p", "480p"],
        help="视频画质（默认: best，即最高清晰度）",
    )
    parser.add_argument(
        "--cookies", "-c",
        default=None,
        help="cookies 文件路径（Netscape 格式）或直接传入 SESSDATA 值",
    )
    parser.add_argument(
        "--concurrency", "-n",
        type=int,
        default=3,
        help="并发下载数量（默认: 3）",
    )

    args = parser.parse_args()
    check_ffmpeg()

    # 规范化 BV 号（去除可能的 URL 前缀）
    bvid = args.bvid
    if "bilibili.com" in bvid:
        match = re.search(r'(BV[a-zA-Z0-9]+)', bvid)
        if match:
            bvid = match.group(1)

    cookies = load_cookies(args.cookies) if args.cookies else ""

    # 获取视频信息和分集列表
    video_title, pages = get_video_pages(bvid, cookies)
    if not pages:
        print("未找到任何分集，退出")
        sys.exit(0)

    # 输出目录：脚本目录下的 downloads/<视频标题>
    script_dir = Path(__file__).parent
    safe_video_title = sanitize_filename(video_title)
    output_dir = str(script_dir / "downloads" / safe_video_title)
    os.makedirs(output_dir, exist_ok=True)

    # 启动时清理未完成的临时文件
    clean_tmp(os.path.join(output_dir, ".tmp"))

    print(f"下载目录: {output_dir}")
    print(f"目标画质: {args.quality}")
    print(f"并发数量: {args.concurrency}")

    total = len(pages)
    print(f"\n共找到 {total} 个分集，开始下载...")
    print("-" * 50)

    success = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = {
            executor.submit(
                download_page,
                bvid, page, i, total,
                output_dir, args.quality, cookies
            ): page
            for i, page in enumerate(pages, 1)
        }

        for future in as_completed(futures):
            if future.result():
                success += 1
            else:
                failed += 1

    print("\n" + "=" * 50)
    print(f"下载完成: 成功 {success} 个，失败 {failed} 个")
    print(f"文件保存在: {output_dir}")


if __name__ == "__main__":
    main()
