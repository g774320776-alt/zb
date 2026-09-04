import requests
import pandas as pd
import re
import os

# =========配置区=========
# 每个频道最多保留5条链接
MAX_URL_PER_CHANNEL = 5

# ✅范明明源放到第一位，优先级最高
urls = [
    "https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/ipv6.m3u",
    "https://raw.githubusercontent.com/zwc456baby/iptv_alive/master/live.txt",
    "https://live.zbds.top/tv/iptv6.txt",
    "https://live.zbds.top/tv/iptv4.txt"
]

ipv4_pattern = re.compile(r'^http://(\d{1,3}\.){3}\d{1,3}')
ipv6_pattern = re.compile(r'^http://\[([a‑fA‑F0‑9:]+)\]')

ban_words = [
    "广告", "购物", "测试", "垃圾", "备用源", "vip", "付费",
    "游戏", "棋牌", "成人", "解密", "高清备用", "直播源分享"
]

HEADERS = {
    "User‑Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

old_output_files = [
    "iptv.txt",
    "iptv.m3u"
]

group_priority = {
    "央视频道": 0,
    "卫视频道": 1,
    "少儿频道": 2
}


def clean_old_files():
    print("\n🧹正在清理旧输出文件...")
    for fpath in old_output_files:
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
                print(f"已删除旧文件: {fpath}")
            except Exception as e:
                print(f"删除文件 {fpath} 失败: {e}")
    print()


def get_cctv_sort_key(name: str):
    m = re.search(r"CCTV[-‑]?(\d+)", name.upper())
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass
    return 999


def get_channel_group(name: str):
    if not name:
        return None
    kid_keywords = ["少儿", "动画", "卡通", "金鹰卡通", "卡酷少儿", "优漫卡通"]
    for k in kid_keywords:
        if k in name:
            return "少儿频道"
    name_upper = name.upper()
    if "CCTV" in name_upper or "央视" in name:
        return "央视频道"
    if "卫视" in name:
        return "卫视频道"
    # 地方台、其他全部返回None直接丢弃
    return None


def clean_program_name(name: str) -> str:
    if not name:
        return ""
    name = re.sub(r'[★✨🔴💥🔥⚡]', '', name)
    name = re.sub(r'\s+', ' ', name)
    name = re.sub(r'\s*(高清|超清|标清|HD|SD|4K|2K)$', '', name, flags=re.IGNORECASE)
    name = name.strip()
    return name


def is_bad_name(name: str) -> bool:
    name_low = name.lower()
    for w in ban_words:
        if w in name_low:
            return True
    return False


def fetch_streams_from_url(url, retries=2):
    print(f"正在爬取网站源: {url}")
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.encoding = 'utf‑8'
            if response.status_code == 200:
                return response.text.replace('\r', '')
            print(f"第{attempt+1}次请求 {url} 状态码:{response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"请求 {url} 异常: {e}")
    print(f"跳过来源: {url}")
    return None


def parse_m3u(content):
    streams = []
    current_program = None
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("#EXTINF"):
            match = re.search(r'tvg‑name="([^"]+)"', line)
            if match:
                current_program = clean_program_name(match.group(1).strip())
        elif line.startswith("http"):
            if current_program and not is_bad_name(current_program):
                streams.append({"program_name": current_program, "stream_url": line})
            current_program = None
    return streams


def parse_txt(content):
    streams = []
    for line in content.splitlines():
        match = re.match(r"\s*(.+?),\s*(http.+)", line)
        if match:
            p_name = clean_program_name(match.group(1).strip())
            p_url = match.group(2).strip()
            if p_name and p_url.startswith("http") and not is_bad_name(p_name):
                streams.append({
                    "program_name": p_name,
                    "stream_url": p_url
                })
    return streams


def parse_single_source(content):
    """每个源独立解析，不再拼接大文本"""
    c = content.lstrip()
    if c.startswith("#EXTM3U"):
        return parse_m3u(content)
    else:
        return parse_txt(content)


def fetch_all_streams():
    """逐个抓取、逐个解析，保证源顺序优先级"""
    all_raw = []
    for url in urls:
        content = fetch_streams_from_url(url)
        if content:
            part = parse_single_source(content)
            all_raw.extend(part)
    return all_raw


def organize_streams(raw_list):
    df = pd.DataFrame(raw_list, columns=["program_name", "stream_url"])
    if df.empty:
        return df

    df = df[df['program_name'].str.len() > 0]
    df = df[df['stream_url'].str.len() > 0]
    df = df[df["stream_url"].str.match(r"^http")]

    df['group'] = df['program_name'].apply(get_channel_group)
    df = df[df["group"].notna()]

    # 删除完全重复【频道+链接】
    df = df.drop_duplicates(subset=["program_name", "stream_url"], keep="first")

    df["group_sort"] = df["group"].map(group_priority)
    df["cctv_num_sort"] = df["program_name"].apply(get_cctv_sort_key)

    # ==========关键修复：不破坏频道内部原始抓取顺序，只对频道做排序==========
    # 1.先记录每个频道的排序信息（每个频道取第一条）
    channel_meta = df.groupby("program_name", sort=False).first().reset_index()
    channel_meta = channel_meta[["program_name","group_sort","cctv_num_sort","group"]]
    # 频道之间排序
    channel_meta = channel_meta.sort_values(by=["group_sort","cctv_num_sort","program_name"], ascending=[True,True,True])

    # 2.按program_name分组，每个频道截取最多MAX_URL_PER_CHANNEL条，**保留内部原始抓取顺序（范明明优先在前）**
    df_grouped = df.groupby("program_name", sort=False).agg({"stream_url":lambda x: list(x.head(MAX_URL_PER_CHANNEL))}).reset_index()
    # 和排序后的频道元数据合并，得到正确频道顺序
    df_merge = pd.merge(channel_meta, df_grouped, on="program_name", how="inner")
    # 展开url列表为多行
    df_explode = df_merge.explode("stream_url").reset_index(drop=True)

    cctv_df = df_explode[df_explode['group'] == "央视频道"]
    wt_df = df_explode[df_explode['group'] == "卫视频道"]
    kid_df = df_explode[df_explode['group'] == "少儿频道"]
    print(f"\n🔍解析统计（每个频道最多保留 {MAX_URL_PER_CHANNEL} 条链接）：")
    print(f"央视频道：{len(cctv_df)}")
    print(f"卫视频道：{len(wt_df)}")
    print(f"少儿频道：{len(kid_df)}")
    print(f"总有效条目(含多url)：{len(df_explode)}")
    return df_explode


def save_to_total_txt(df, filename="iptv.txt"):
    ipv4 = []
    ipv6 = []
    domain = []
    # 修复：使用 .itertuples 规避旧pandas行索引KeyError问题
    for row in df.itertuples(index=False):
        program = row.program_name
        url = row.stream_url
        if ipv4_pattern.match(url):
            ipv4.append(f"{program},{url}")
        elif ipv6_pattern.match(url):
            ipv6.append(f"{program},{url}")
        else:
            domain.append(f"{program},{url}")

    with open(filename, 'w', encoding='utf‑8') as f:
        f.write("# IPv4 Streams\n")
        f.write("\n".join(ipv4))
        f.write("\n\n# IPv6 Streams\n")
        f.write("\n".join(ipv6))
        f.write("\n\n# Domain Streams\n")
        f.write("\n".join(domain))
    print(f"总文本文件已保存: {os.path.abspath(filename)}")


def save_to_m3u(df, filename="iptv.m3u"):
    with open(filename, 'w', encoding='utf‑8', newline='') as f:
        f.write("#EXTM3U\n")
        for row in df.itertuples(index=False):
            program = row.program_name
            group = row.group
            url = row.stream_url
            f.write(f'#EXTINF:-1 tvg‑name="{program}" group‑title="{group}",{program}\n{url}\n')
    print(f"M3U文件已保存: {os.path.abspath(filename)}")


if __name__ == "__main__":
    clean_old_files()
    print("开始抓取所有源...")
    raw_data = fetch_all_streams()
    if raw_data:
        print("整理源数据中...")
        df_result = organize_streams(raw_data)
        if not df_result.empty:
            save_to_total_txt(df_result)
            save_to_m3u(df_result)
            unique_channel_count = df_result["program_name"].nunique()
            print(f"\n✅全部完成！共 {unique_channel_count} 个唯一频道，{len(df_result)} 条直播流")
        else:
            print("❌没有有效节目")
    else:
        print("❌未能获取有效数据")
