# Python Scripts

个人 Python 脚本收藏仓库，用于存储和管理日常使用的各类 Python 脚本。

## 脚本列表

| 脚本名称 | 功能说明 |
| -------- | -------- |
| [bilibili_downloader.py](scripts/bilibili_downloader.py) | 下载 B 站 UP 主的所有视频，支持画质选择 |

## 使用说明

**运行环境要求**

- Python 3.8+
- [ffmpeg](https://ffmpeg.org/)（bilibili_downloader 需要，用于合并音视频）：`brew install ffmpeg`

**执行脚本**

```bash
python scripts/<脚本名称>.py
```

**bilibili_downloader 示例**

```bash
# 下载 UP 主所有视频（默认最高画质）
python scripts/bilibili_downloader.py <UID>

# 指定画质（best / 1080p / 720p / 480p）
python scripts/bilibili_downloader.py <UID> --quality 1080p

# 使用 cookies 文件（高清画质需要登录）
python scripts/bilibili_downloader.py <UID> --cookies cookies.txt
```

> 未登录时 B 站限制最高 480P，高清视频需提供 cookies 文件（Netscape 格式）。
> 视频保存在 `scripts/downloads/<UP主用户名>/` 目录下。

## 目录结构

```
python-scripts/
├── .gitignore
├── README.md
└── scripts/        # 所有脚本存放目录
```
