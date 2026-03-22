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

**bilibili_downloader 使用说明**

这个脚本用于批量下载 B 站 UP 主的所有视频，使用纯 Python 实现，支持 WBI 签名验证。

**获取 cookies 文件：**

1. 安装浏览器扩展：
   - Chrome/Edge: "Get cookies.txt LOCALLY"
   - Firefox: "cookies.txt"
2. 访问 bilibili.com 并登录
3. 点击扩展图标，导出 cookies 到文件（Netscape 格式）

**使用示例：**

```bash
# 下载 UP 主所有视频（默认最高画质）
python3 scripts/bilibili_downloader.py <UP主UID> --cookies cookies.txt

# 指定画质
python3 scripts/bilibili_downloader.py <UP主UID> --cookies cookies.txt --quality 1080p

# 画质选项：best（默认，最高）/ 1080p / 720p / 480p
```

**注意事项：**

- 必须提供完整的 cookies 文件（包含 SESSDATA、buvid3 等），只有 SESSDATA 不够
- 未登录或 cookies 不完整时，B 站会限制画质和访问频率
- 视频保存在 `scripts/downloads/<UP主用户名>/` 目录下
- 下载过程中会在 `.tmp` 目录生成临时文件，合并完成后自动删除
- 脚本会自动跳过已下载的视频

## 目录结构

```
python-scripts/
├── .gitignore
├── README.md
└── scripts/        # 所有脚本存放目录
```
