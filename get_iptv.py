import requests
import pandas as pd
import re
import os

# 源地址列表
urls = [
    "https://raw.githubusercontent.com/zwc456baby/iptv_alive/master/live.txt",
    "https://live.zbds.top/tv/iptv6.txt",
    "https://live.zbds.top/tv/iptv4.txt",
]

ipv4_pattern = re.compile(r'^http://(\d{1,3}\.){3}\d{1,3}')
ipv6_pattern = re.compile(r'^http://\[([a-fA-F0-9:]+)\]')

# 广告/垃圾关键词过滤
ban_words = [
    "广告", "购物", "测试", "垃圾", "备用源", "vip", "付费",
    "游戏", "棋牌", "成人", "解密", "高清备用", "直播源分享"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# 需要自动清理的旧输出文件列表
old_output_files = [
    "iptv.txt",
    "iptv.m3u"
]

# 分组排序优先级
group_priority = {
    "央视频道": 0,
    "卫视频道": 1,
    "少儿频道": 2,
    "地方频道": 3,
    "其他频道": 4
}


def clean_old_files():
    """自动清理旧输出文件"""
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
    """提取CCTV后面数字用于排序，无数字返回999放末尾"""
    m = re.search(r"CCTV[-‑]?(\d+)", name.upper())
    if m:
        return int(m.group(1))
    return 999


def get_channel_group(name: str) -> str:
    """根据频道名判断分组【修复CCTV识别】"""
    if not name:
        return "其他频道"

    # 少儿频道优先匹配
    kid_keywords = ["少儿", "动画", "卡通", "金鹰卡通", "卡酷少儿", "优漫卡通"]
    for k in kid_keywords:
        if k in name:
            return "少儿频道"

    # 央视频道：包含CCTV 或者 央视
    name_upper = name.upper()
    if "CCTV" in name_upper or "央视" in name:
        return "央视频道"

    # 卫视频道
    if "卫视" in name:
        return "卫视频道"

    # 地方台
    return "地方频道"


def clean_program_name(name: str) -> str:
    """清洗节目名称，保留CCTV‑1数字编号"""
    if not name:
        return ""
    # 去除特殊表情符号
    name = re.sub(r'[★✨🔴💥🔥⚡]', '', name)
    name = re.sub(r'\s+', ' ', name)
    # 只清除末尾的高清/超清/4K/HD等后缀
    name = re.sub(r'\s*(高清|超清|标清|HD|SD|4K|2K)$', '', name, flags=re.IGNORECASE)
    name = name.strip()
    return name


def is_bad_name(name: str) -> bool:
    """判断是否垃圾节目"""
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
            response.encoding = 'utf-8'
            if response.status_code == 200:
                return response.text
            print(f"第{attempt+1}次请求 {url} 状态码:{response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"请求 {url} 异常: {e}")
    print(f"跳过来源: {url}")
    return None


def fetch_all_streams():
    all_streams = []
    for url in urls:
        content = fetch_streams_from_url(url)
        if content:
            all_streams.append(content)
    return "\n".join(all_streams)


def parse_m3u(content):
    streams = []
    current_program = None
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("#EXTINF"):
            match = re.search(r'tvg-name="([^"]+)"', line)
            if match:
                current_program = clean_program_name(match.group(1).strip())
        elif line.startswith("http"):
            if current_program and not is_bad_name(current_program):
                streams.append({"program_name": current_program, "stream_url": line})
            current_program = None  # 解析完链接立刻清空，修复错乱问题
    return streams


def parse_txt(content):
    streams = []
    for line in content.splitlines():
        # 修复：允许行开头存在空格
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


def organize_streams(content):
    parser = parse_m3u if content.lstrip().startswith("#EXTM3U") else parse_txt
    raw = parser(content)
    df = pd.DataFrame(raw)
    if df.empty:
        return df
    # 联合去重：频道+链接同时一样才删除
    df = df.drop_duplicates(subset=['program_name', 'stream_url'], keep="first")
    df = df[df['program_name'].str.len() > 0]
    df = df[df['stream_url'].str.len() > 0]
    df['group'] = df['program_name'].apply(get_channel_group)

    # 排序字段
    df["group_sort"] = df["group"].map(group_priority)
    df["cctv_num_sort"] = df["program_name"].apply(get_cctv_sort_key)
    # 先按分组，再按cctv数字，再频道名称
    df = df.sort_values(by=["group_sort", "cctv_num_sort", "program_name"], ascending=[True, True, True])
    df = df.reset_index(drop=True)

    cctv_df = df[df['group'] == "央视频道"]
    print(f"\n🔍解析到央视频道数量：{len(cctv_df)}")
    return df


def save_to_total_txt(df, filename="iptv.txt"):
    """保存总txt文件，区分IPv4/IPv6，保持已经排好的顺序"""
    ipv4 = []
    ipv6 = []
    for _, row in df.iterrows():
        program = row['program_name']
        url = row['stream_url']
        if ipv4_pattern.match(url):
            ipv4.append(f"{program},{url}")
        elif ipv6_pattern.match(url):
            ipv6.append(f"{program},{url}")

    with open(filename, 'w', encoding='utf-8') as f:
        f.write("# IPv4 Streams\n")
        f.write("\n".join(ipv4))
        f.write("\n\n# IPv6 Streams\n")
        f.write("\n".join(ipv6))
    print(f"总文本文件已保存: {os.path.abspath(filename)}")


def save_to_m3u(df, filename="iptv.m3u"):
    with open(filename, 'w', encoding='utf-8', newline='') as f:
        f.write("#EXTM3U\n")
        for _, row in df.iterrows():
            program = row['program_name']
            group = row['group']
            url = row['stream_url']
            f.write(f'#EXTINF:-1 tvg-name="{program}" group-title="{group}",{program}\n{url}\n')
    print(f"M3U文件已保存: {os.path.abspath(filename)}")


if __name__ == "__main__":
    # 第一步：清理旧文件
    clean_old_files()

    print("开始抓取所有源...")
    content = fetch_all_streams()
    if content:
        print("整理源数据中...")
        df_result = organize_streams(content)
        if not df_result.empty:
            save_to_total_txt(df_result)
            save_to_m3u(df_result)
            print(f"\n✅全部完成！共 {len(df_result)} 条直播流")
        else:
            print("❌没有解析到有效节目")
    else:
        print("❌未能获取有效数据")
