# Python Scripts

个人 Python 脚本收藏仓库，用于存储和管理日常使用的各类 Python 脚本。

## 脚本列表

| 脚本名称 | 功能说明 |
| -------- | -------- |
| [bilibili_by_uploader.py](scripts/bilibili_by_uploader.py) | 根据 UP 主 ID 下载该 UP 主的所有视频 |
| [bilibili_by_bvid.py](scripts/bilibili_by_bvid.py) | 根据视频 BV 号下载该视频的所有分集 |

## 使用说明

**运行环境要求**

- Python 3.8+
- [ffmpeg](https://ffmpeg.org/)（B 站下载脚本需要，用于合并音视频）：`brew install ffmpeg`

**执行脚本**

```bash
python scripts/<脚本名称>.py
```

### B 站视频下载脚本使用说明

两个脚本都使用纯 Python 实现，支持 WBI 签名验证、多画质选择和并发下载。

**获取 cookies 文件：**

1. 安装浏览器扩展：
   - Chrome/Edge: "Get cookies.txt LOCALLY"
   - Firefox: "cookies.txt"
2. 访问 bilibili.com 并登录
3. 点击扩展图标，导出 cookies 到文件（Netscape 格式）

#### 1. bilibili_by_uploader.py - 根据 UP 主下载

下载指定 UP 主的所有视频。

**使用示例：**

```bash
# 下载 UP 主所有视频（默认最高画质）
python3 scripts/bilibili_by_uploader.py <UP主UID> --cookies cookies.txt

# 指定画质和并发数
python3 scripts/bilibili_by_uploader.py <UP主UID> --cookies cookies.txt --quality 1080p --concurrency 5

# 画质选项：best（默认，最高）/ 1080p / 720p / 480p
```

**说明：**
- 视频保存在 `scripts/downloads/<UP主用户名>/` 目录下
- 自动跳过已下载的视频

#### 2. bilibili_by_bvid.py - 根据 BV 号下载

下载指定视频的所有分集（适合下载课程、连载视频等）。

**使用示例：**

```bash
# 下载视频所有分集（默认最高画质）
python3 scripts/bilibili_by_bvid.py BV1P7411C7Gz --cookies cookies.txt

# 也可以直接传入完整 URL
python3 scripts/bilibili_by_bvid.py https://www.bilibili.com/video/BV1P7411C7Gz/ --cookies cookies.txt

# 指定画质和并发数
python3 scripts/bilibili_by_bvid.py BV1P7411C7Gz --cookies cookies.txt --quality 1080p --concurrency 5
```

**说明：**
- 视频保存在 `scripts/downloads/<视频标题>/` 目录下
- 文件命名格式：P1_分集标题.mp4、P2_分集标题.mp4...
- 自动跳过已下载的分集

**通用注意事项：**

- 必须提供完整的 cookies 文件（包含 SESSDATA、buvid3 等），只有 SESSDATA 不够
- 未登录或 cookies 不完整时，B 站会限制画质和访问频率
- 下载过程中会在 `.tmp` 目录生成临时文件，合并完成后自动删除
- 默认并发数为 3，可根据网络情况调整

## 目录结构

```
python-scripts/
├── .gitignore
├── README.md
└── scripts/
    ├── bilibili_by_uploader.py
    ├── bilibili_by_bvid.py
    └── downloads/          # 下载的视频（自动创建）
        ├── <UP主用户名>/
        └── <视频标题>/
```
