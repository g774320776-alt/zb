import requests
import pandas as pd
import re
import os

# ====================== 【自定义配置区】 ======================
# 优先频道顺序：越靠前输出越优先
PRIORITY_CHANNELS = [
    "CCTV-1",
    "CCTV-2",
    "CCTV-3",
    "CCTV-4",
    "CCTV-5",
    "CCTV-6",
    "CCTV-7",
    "CCTV-8",
    "CCTV-9",
    "CCTV-10",
    "CCTV-11",
    "CCTV-12",
    "CCTV-13",
    "CCTV-14",
    "CCTV-15",
    "湖南卫视",
    "浙江卫视",
    "江苏卫视",
    "东方卫视",
    "广东卫视"
]

# 只保留 CCTV 和 卫视频道
ENABLE_WHITELIST = True
CHANNEL_WHITELIST = [
    "CCTV",
    "卫视"
]

# 网络抓取源列表：移除第一个报错的migu外网源
urls = [
    "https://raw.githubusercontent.com/zwc456baby/iptv_alive/master/live.txt",
    "https://ghproxy.com/https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/ipv6.m3u",
    "https://live.zbds.top/tv/iptv6.txt",
    "https://live.zbds.top/tv/iptv4.txt",
]

# 本地源文件名（仓库根目录 local.txt）
LOCAL_SOURCE_FILE = "local.txt"
# ========================================================================

pd.options.mode.chained_assignment = None

ipv4_pattern = re.compile(r'^http://(\d{1,3}\.){3}\d{1,3}')
ipv6_pattern = re.compile(r'^http://\[([a-fA-F0-9:]+)\]')
clean_char_pattern = re.compile(r'[^\x00-\x7E\u4e00-\u9fff]')

def clean_text(text: str) -> str:
    """清理文本中隐形特殊Unicode字符"""
    return clean_char_pattern.sub('', text)

def fetch_local_file(filepath):
    """读取仓库本地自定义源 local.txt"""
    if os.path.exists(filepath):
        print(f"✅加载本地源文件: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            raw = f.read()
        return clean_text(raw)
    else:
        print(f"⚠️本地源文件 {filepath} 不存在，跳过本地源")
        return None

def get_priority_score(channel_name):
    """手动优先列表，匹配到返回序号，没匹配返回9999"""
    for idx, keyword in enumerate(PRIORITY_CHANNELS):
        if keyword in channel_name:
            return idx
    return 9999

def get_group_name(channel_name):
    """获取分组名称：央视频道 / 卫视频道"""
    if "CCTV" in channel_name.upper():
        return "央视频道"
    elif "卫视" in channel_name:
        return "卫视频道"
    return "其他"

def parse_cctv_num(name):
    """提取CCTV后面数字，用于央视排序，返回数字；非CCTV返回999"""
    m = re.search(r'CCTV\D*(\d+)', name.upper())
    if m:
        return int(m.group(1))
    return 999

def is_keep_channel(channel_name, stream_url):
    """过滤：只保留白名单（CCTV / 卫视）"""
    name = channel_name.lower()
    if ENABLE_WHITELIST:
        hit = any(kw.lower() in name for kw in CHANNEL_WHITELIST)
        if not hit:
            return False
    return True

def fetch_streams_from_url(url):
    print(f"正在爬取网站源: {url}")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        if response.status_code == 200:
            raw = response.text
            return clean_text(raw)
        print(f"从 {url} 获取数据失败，状态码: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"请求 {url} 时发生错误: {e}")
    return None

def fetch_all_streams():
    all_streams = []
    # 优先读取本地源（优先级最高）
    local_content = fetch_local_file(LOCAL_SOURCE_FILE)
    if local_content and len(local_content.strip())>5:
        all_streams.append(local_content.strip())

    # 读取网络源
    for url in urls:
        content = fetch_streams_from_url(url)
        if content and len(content.strip()) > 10:
            all_streams.append(content.strip())
        else:
            print(f"跳过来源: {url}")
    return "\n".join(all_streams)

def parse_content(content):
    """解析m3u/txt，同时执行过滤，只留下CCTV和卫视"""
    streams = []
    current_program = None

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue

        if line.startswith("#EXTINF"):
            match = re.search(r'tvg-name="([^"]+)"', line)
            if match:
                current_program = match.group(1).strip()
            continue
        # txt格式：频道名,url
        if ',' in line and not line.startswith(('http', 'https')):
            match = re.match(r"(.+?),\s*(http.+)", line)
            if match:
                p_name = match.group(1).strip()
                p_url = match.group(2).strip()
                if is_keep_channel(p_name, p_url):
                    streams.append({"program_name": p_name, "stream_url": p_url})
            continue
        # m3u链接行
        if line.startswith(("http://", "https://")):
            if current_program:
                if is_keep_channel(current_program, line):
                    streams.append({"program_name": current_program, "stream_url": line})
                current_program = None
    return streams


def organize_streams(content):
    raw_list = parse_content(content)
    if not raw_list:
        print("警告：没有解析到任何频道数据！")
        return pd.DataFrame(columns=["program_name", "stream_url"])

    df = pd.DataFrame(raw_list)
    df = df[(df["program_name"] != "") & (df["stream_url"] != "")]
    df = df.drop_duplicates(subset=['program_name', 'stream_url'])
    print(f"过滤后总频道链接数: {len(df)}")

    grouped = df.groupby('program_name')['stream_url'].apply(list).reset_index()
    grouped['group'] = grouped['program_name'].apply(get_group_name)
    grouped['priority'] = grouped['program_name'].apply(get_priority_score)
    grouped['cctv_no'] = grouped['program_name'].apply(parse_cctv_num)

    group_order = {"央视频道":0, "卫视频道":1}
    grouped["group_order"] = grouped["group"].map(group_order)

    grouped = grouped.sort_values(
        by=["group_order", "priority", "cctv_no", "program_name"],
        ascending=[True, True, True, True]
    )
    grouped = grouped.drop(columns=["priority", "cctv_no", "group_order"]).reset_index(drop=True)
    print(f"✅完成优化排序")
    return grouped


def save_to_txt(grouped_streams, filename="iptv.txt"):
    cctv_rows = grouped_streams[grouped_streams["group"]=="央视频道"]
    ws_rows = grouped_streams[grouped_streams["group"]=="卫视频道"]

    with open(filename, 'w', encoding='utf-8') as f:
        f.write("# 央视频道\n")
        for _, row in cctv_rows.iterrows():
            program = row['program_name']
            for url in row['stream_url']:
                f.write(f"{program},{url}\n")
        f.write("\n# 卫视频道\n")
        for _, row in ws_rows.iterrows():
            program = row['program_name']
            for url in row['stream_url']:
                f.write(f"{program},{url}\n")
    print(f"✅文本文件已保存: {os.path.abspath(filename)}")
    print(f"  央视频道数量: {len(cctv_rows)}")
    print(f"  卫视频道数量: {len(ws_rows)}")


def save_to_m3u(grouped_streams, filename="iptv.m3u"):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for _, row in grouped_streams.iterrows():
            program = row['program_name']
            group = row['group']
            for url in row['stream_url']:
                f.write(f'#EXTINF:-1 tvg-name="{program}" group-title="{group}",{program}\n{url}\n')
    print(f"✅M3U文件已保存: {os.path.abspath(filename)}")


def clean_old_files():
    """提前删除旧的 iptv.txt、iptv.m3u"""
    for file in ["iptv.txt", "iptv.m3u"]:
        if os.path.exists(file):
            os.remove(file)
            print(f"🗑️已删除旧文件: {file}")


if __name__ == "__main__":
    clean_old_files()
    print("===== IPTV源抓取开始 =====")
    full_content = fetch_all_streams()
    if full_content and len(full_content.strip()) > 20:
        print("整理源数据中...")
        organized_df = organize_streams(full_content)
        if len(organized_df) > 0:
            save_to_txt(organized_df)
            save_to_m3u(organized_df)
        else:
            print("解析后无频道数据，跳过输出")
    else:
        print("❌未能获取有效数据，全部源抓取失败")
