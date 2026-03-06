# ============================================
# 配置文件模板 - 复制为 config.py 并填入你的密钥
# ============================================
# 使用方法：
#   1. 把这个文件复制一份，重命名为 config.py
#   2. 把下面四个占位符替换成你的真实密钥

# YouTube Data API 密钥
# 获取方式：Google Cloud Console → API和服务 → 凭据 → 创建API密钥
YOUTUBE_API_KEY = "在这里填入你的YouTube API密钥"  # 以 AIza 开头

# Notion Integration 密钥
# 获取方式：https://www.notion.so/my-integrations → New integration
NOTION_API_KEY = "在这里填入你的Notion Integration密钥"  # 以 ntn_ 开头

# Notion 博主数据库 ID（存放要监控的YouTube频道）
# 获取方式：打开数据库页面，URL中 ?v= 前面那段32位字符串
NOTION_CHANNEL_DATABASE_ID = "在这里填入博主数据库ID"

# Notion 选题追踪数据库 ID（自动写入视频信息）
NOTION_VIDEO_DATABASE_ID = "在这里填入选题追踪数据库ID"
