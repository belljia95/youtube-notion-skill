# ============================================
# YouTube频道监控 + Notion自动化脚本
# 功能：监控指定YouTube频道的新视频，自动同步到Notion数据库
# ============================================

import sys
import io

# 修复Windows编码问题，让脚本能正常显示中文和表情符号
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests  # 用于发送HTTP请求（调用API）
from datetime import datetime, timedelta, timezone  # 用于处理日期时间
import time  # 用于添加延迟，避免API请求过快

# 导入配置文件中的密钥和数据库ID
from config import (
    YOUTUBE_API_KEY,
    NOTION_API_KEY,
    NOTION_CHANNEL_DATABASE_ID,
    NOTION_VIDEO_DATABASE_ID
)

# ============================================
# 第一部分：Notion相关函数
# ============================================

def get_channels_from_notion():
    """
    从Notion的博主数据库中获取所有要监控的YouTube频道
    返回一个列表，每个元素包含频道名称和channelID
    """
    print("📋 正在从Notion获取频道列表...")

    # Notion API的请求地址
    url = f"https://api.notion.com/v1/databases/{NOTION_CHANNEL_DATABASE_ID}/query"

    # 请求头，包含认证信息和API版本
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",  # Notion API版本
        "Content-Type": "application/json"
    }

    # 发送POST请求查询数据库
    response = requests.post(url, headers=headers, json={})

    # 检查请求是否成功
    if response.status_code != 200:
        print(f"❌ 获取频道列表失败: {response.text}")
        return []

    # 解析返回的数据
    data = response.json()
    channels = []

    # 遍历每一行数据（每个频道）
    for page in data.get("results", []):
        properties = page.get("properties", {})

        # 获取频道名称（标题列）
        # Notion的标题列结构比较复杂，需要这样提取
        name_property = properties.get("Youtube博主", {})
        name = ""
        if name_property.get("title"):
            name = name_property["title"][0]["plain_text"] if name_property["title"] else ""

        # 获取channelID（文本列）
        channel_id_property = properties.get("channelID", {})
        channel_id = ""
        if channel_id_property.get("rich_text"):
            channel_id = channel_id_property["rich_text"][0]["plain_text"] if channel_id_property["rich_text"] else ""

        # 清理channelID（去除可能的引号）
        channel_id = channel_id.strip().strip('"').strip("'")

        # 如果channelID存在，添加到列表
        if channel_id:
            channels.append({
                "name": name,
                "channel_id": channel_id
            })
            print(f"  ✓ 找到频道: {name} ({channel_id})")

    print(f"📋 共找到 {len(channels)} 个频道")
    return channels


def check_video_exists(video_url):
    """
    检查某个视频是否已经存在于Notion的选题追踪数据库中
    通过视频URL来判断，避免重复添加
    """
    url = f"https://api.notion.com/v1/databases/{NOTION_VIDEO_DATABASE_ID}/query"

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    # 使用筛选条件查询是否存在相同URL的视频
    filter_data = {
        "filter": {
            "property": "主页地址",
            "url": {
                "equals": video_url
            }
        }
    }

    response = requests.post(url, headers=headers, json=filter_data)

    if response.status_code != 200:
        return False

    data = response.json()
    # 如果返回结果不为空，说明视频已存在
    return len(data.get("results", [])) > 0


def add_video_to_notion(video_info):
    """
    将一个新视频添加到Notion的选题追踪数据库
    video_info 包含视频的所有信息
    """
    url = "https://api.notion.com/v1/pages"

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    # 构建要添加到Notion的数据
    # 每个属性的格式根据其类型不同而不同
    data = {
        "parent": {"database_id": NOTION_VIDEO_DATABASE_ID},
        "properties": {
            # 标题列 - 视频标题
            "Title": {
                "title": [
                    {
                        "text": {
                            "content": video_info["title"][:2000]  # Notion标题有长度限制
                        }
                    }
                ]
            },
            # URL列 - 视频链接
            "主页地址": {
                "url": video_info["url"]
            },
            # 文本列 - 频道ID
            "channelID": {
                "rich_text": [
                    {
                        "text": {
                            "content": video_info["channel_id"]
                        }
                    }
                ]
            },
            # 文本列 - 视频描述
            "Description": {
                "rich_text": [
                    {
                        "text": {
                            "content": video_info["description"][:2000]  # 限制长度避免超出API限制
                        }
                    }
                ]
            },
            # 数字列 - 播放量
            "Views": {
                "number": video_info["views"]
            },
            # 数字列 - 点赞数
            "Likes": {
                "number": video_info["likes"]
            },
            # 日期列 - 发布时间
            "发布时间": {
                "date": {
                    "start": video_info["published_at"]  # ISO 8601 格式
                }
            },
            # Select列 - 博主名称（用于区分不同频道，会自动显示不同颜色）
            "博主": {
                "select": {
                    "name": video_info["channel_name"]
                }
            }
        }
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        print(f"  ✅ 已添加视频: {video_info['title'][:50]}...")
        return True
    else:
        print(f"  ❌ 添加视频失败: {response.text}")
        return False


# ============================================
# 第二部分：YouTube相关函数
# ============================================

def get_recent_videos(channel_id, hours=24):
    """
    获取某个YouTube频道在指定时间内发布的新视频
    默认获取最近24小时内的视频
    """
    # 计算时间范围（24小时前到现在）
    now = datetime.now(timezone.utc)
    time_threshold = now - timedelta(hours=hours)
    # YouTube API要求的时间格式：RFC 3339
    published_after = time_threshold.strftime("%Y-%m-%dT%H:%M:%SZ")

    # YouTube Search API 地址
    url = "https://www.googleapis.com/youtube/v3/search"

    # 请求参数
    params = {
        "key": YOUTUBE_API_KEY,
        "channelId": channel_id,
        "part": "snippet",  # 返回基本信息
        "order": "date",  # 按发布日期排序
        "publishedAfter": published_after,  # 只获取这个时间之后的视频
        "maxResults": 10,  # 最多返回10个视频
        "type": "video"  # 只要视频，不要播放列表等
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        print(f"  ❌ 获取视频列表失败: {response.text}")
        return []

    data = response.json()
    videos = []

    # 遍历搜索结果
    for item in data.get("items", []):
        video_id = item["id"]["videoId"]
        snippet = item["snippet"]

        videos.append({
            "video_id": video_id,
            "title": snippet["title"],
            "description": snippet.get("description", ""),
            "published_at": snippet["publishedAt"],
            "channel_id": channel_id
        })

    return videos


def get_video_statistics(video_id):
    """
    获取单个视频的详细统计信息（播放量、点赞数）
    因为Search API不返回这些数据，需要额外调用Videos API
    """
    url = "https://www.googleapis.com/youtube/v3/videos"

    params = {
        "key": YOUTUBE_API_KEY,
        "id": video_id,
        "part": "statistics"  # 只需要统计信息
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        return {"views": 0, "likes": 0}

    data = response.json()
    items = data.get("items", [])

    if not items:
        return {"views": 0, "likes": 0}

    stats = items[0].get("statistics", {})

    return {
        "views": int(stats.get("viewCount", 0)),
        "likes": int(stats.get("likeCount", 0))
    }


# ============================================
# 第三部分：描述清理功能
# ============================================

import re  # 用于正则表达式处理文本

def clean_description(description):
    """
    清理视频描述，去掉链接、广告、时间戳等无用信息
    输入：原始描述
    输出：清理后的描述
    """
    # 如果描述为空，直接返回
    if not description or len(description.strip()) < 5:
        return "暂无描述"

    text = description

    # 1. 去掉所有链接
    text = re.sub(r'https?://\S+', '', text)

    # 2. 去掉时间戳格式 (如 00:00, 1:23:45)
    text = re.sub(r'\b\d{1,2}:\d{2}(:\d{2})?\b', '', text)

    # 3. 去掉常见广告词汇所在的行
    ad_keywords = ['subscribe', 'follow me', 'my links', 'sponsor', 'discount code',
                   'use code', 'affiliate', 'check out', 'sign up', '订阅', '关注']
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line_lower = line.lower()
        if not any(kw in line_lower for kw in ad_keywords):
            cleaned_lines.append(line)
    text = '\n'.join(cleaned_lines)

    # 4. 去掉多余的空行和空格
    text = re.sub(r'\n{3,}', '\n\n', text)  # 多个换行变成两个
    text = re.sub(r' {2,}', ' ', text)  # 多个空格变成一个
    text = text.strip()

    # 5. 限制长度（保留前2000字符，这是Notion rich_text的最大限制）
    if len(text) > 2000:
        text = text[:2000] + "..."

    # 如果清理后为空，返回提示
    if len(text.strip()) < 5:
        return "暂无描述"

    return text


# ============================================
# 第四部分：主程序逻辑
# ============================================

def main():
    """
    主函数 - 整个程序的入口点
    执行流程：
    1. 从Notion获取要监控的频道列表
    2. 对每个频道，获取24小时内的新视频
    3. 检查每个视频是否已存在于Notion
    4. 如果是新视频，获取详细信息并添加到Notion
    """
    print("=" * 50)
    print("🚀 YouTube频道监控脚本启动")
    print(f"⏰ 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # 第一步：获取要监控的频道列表
    channels = get_channels_from_notion()

    if not channels:
        print("⚠️ 没有找到要监控的频道，请检查Notion数据库")
        return

    # 统计数据
    total_new_videos = 0

    # 第二步：遍历每个频道
    for channel in channels:
        print(f"\n🔍 正在检查频道: {channel['name']}")

        # 获取该频道7天内的新视频（可以修改hours参数调整时间范围）
        videos = get_recent_videos(channel["channel_id"], hours=168)  # 168小时 = 7天

        if not videos:
            print(f"  📭 没有发现新视频")
            continue

        print(f"  📺 发现 {len(videos)} 个视频，正在检查...")

        # 第三步：处理每个视频
        for video in videos:
            video_url = f"https://www.youtube.com/watch?v={video['video_id']}"

            # 检查视频是否已存在
            if check_video_exists(video_url):
                print(f"  ⏭️ 视频已存在，跳过: {video['title'][:30]}...")
                continue

            # 获取视频的统计信息
            stats = get_video_statistics(video["video_id"])

            # 清理描述（去掉链接、广告等）
            cleaned_desc = clean_description(video["description"])

            # 组装完整的视频信息
            video_info = {
                "title": video["title"],
                "description": cleaned_desc,  # 使用清理后的描述
                "url": video_url,
                "channel_id": video["channel_id"],
                "channel_name": channel["name"],  # 添加博主名称，用于在Notion中区分
                "views": stats["views"],
                "likes": stats["likes"],
                "published_at": video["published_at"][:10]  # 只取日期部分 YYYY-MM-DD
            }

            # 添加到Notion
            if add_video_to_notion(video_info):
                total_new_videos += 1

            # 添加小延迟，避免请求过快被API限制
            time.sleep(0.5)

    # 完成
    print("\n" + "=" * 50)
    print(f"✅ 监控完成！本次共添加 {total_new_videos} 个新视频")
    print("=" * 50)


# ============================================
# 第五部分：修复函数 - 重新获取完整描述
# ============================================

def get_all_videos_from_notion():
    """
    从Notion数据库获取所有视频的信息
    返回包含page_id和video_url的列表
    """
    url = f"https://api.notion.com/v1/databases/{NOTION_VIDEO_DATABASE_ID}/query"

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    # 查询所有视频（不加筛选条件）
    response = requests.post(url, headers=headers, json={})

    if response.status_code != 200:
        print(f"❌ 获取Notion数据失败: {response.text}")
        return []

    data = response.json()
    results = data.get("results", [])

    videos = []
    for page in results:
        page_id = page["id"]
        properties = page.get("properties", {})

        # 获取视频URL
        url_prop = properties.get("主页地址", {})
        video_url = url_prop.get("url", "")

        # 获取标题（用于显示）
        title_prop = properties.get("Title", {})
        title_items = title_prop.get("title", [])
        title = title_items[0]["text"]["content"] if title_items else "无标题"

        if video_url:
            videos.append({
                "page_id": page_id,
                "video_url": video_url,
                "title": title
            })

    return videos


def extract_video_id(video_url):
    """
    从YouTube视频URL中提取video_id
    支持多种URL格式：
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    """
    # 格式1: youtube.com/watch?v=VIDEO_ID
    if "watch?v=" in video_url:
        return video_url.split("watch?v=")[1].split("&")[0]

    # 格式2: youtu.be/VIDEO_ID
    if "youtu.be/" in video_url:
        return video_url.split("youtu.be/")[1].split("?")[0]

    return None


def get_video_full_info(video_id):
    """
    获取单个视频的完整信息，包括描述
    """
    url = "https://www.googleapis.com/youtube/v3/videos"

    params = {
        "key": YOUTUBE_API_KEY,
        "id": video_id,
        "part": "snippet"  # snippet包含标题、描述等基本信息
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        return None

    data = response.json()
    items = data.get("items", [])

    if not items:
        return None

    snippet = items[0].get("snippet", {})

    return {
        "description": snippet.get("description", "")
    }


def update_notion_description(page_id, new_description):
    """
    更新Notion页面的Description字段
    """
    url = f"https://api.notion.com/v1/pages/{page_id}"

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    # 只更新Description字段
    data = {
        "properties": {
            "Description": {
                "rich_text": [
                    {
                        "text": {
                            "content": new_description[:2000]  # Notion限制
                        }
                    }
                ]
            }
        }
    }

    response = requests.patch(url, headers=headers, json=data)

    return response.status_code == 200


def fix_all_descriptions():
    """
    修复所有现有视频的描述：
    1. 从Notion获取所有视频
    2. 从YouTube重新获取完整描述
    3. 清理后更新到Notion
    """
    print("=" * 50)
    print("🔧 开始修复视频描述...")
    print("=" * 50)

    # 1. 获取所有视频
    print("\n📋 正在从Notion获取现有视频...")
    videos = get_all_videos_from_notion()
    print(f"   找到 {len(videos)} 个视频")

    if not videos:
        print("❌ 没有找到任何视频，退出")
        return

    # 2. 逐个处理
    success_count = 0
    for i, video in enumerate(videos, 1):
        title = video["title"][:40]
        print(f"\n[{i}/{len(videos)}] 处理: {title}...")

        # 提取video_id
        video_id = extract_video_id(video["video_url"])
        if not video_id:
            print(f"   ⚠️ 无法解析视频ID，跳过")
            continue

        # 从YouTube获取完整描述
        video_info = get_video_full_info(video_id)
        if not video_info:
            print(f"   ⚠️ 无法获取视频信息，跳过")
            continue

        # 清理描述
        cleaned_desc = clean_description(video_info["description"])

        # 更新到Notion
        if update_notion_description(video["page_id"], cleaned_desc):
            print(f"   ✅ 已更新描述（{len(cleaned_desc)}字符）")
            success_count += 1
        else:
            print(f"   ❌ 更新失败")

        # 添加延迟避免API限制
        time.sleep(0.5)

    print("\n" + "=" * 50)
    print(f"✅ 修复完成！成功更新 {success_count}/{len(videos)} 个视频")
    print("=" * 50)


# 当直接运行这个脚本时，执行main函数
if __name__ == "__main__":
    # 正常运行：监控新视频
    main()

    # 如果需要修复现有视频的描述，可以取消下面这行的注释：
    # fix_all_descriptions()
