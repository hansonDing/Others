#!/usr/bin/env python3
"""
科技板块晨间扫描器
- 美股科技隔夜走势（新浪接口）
- 港股科技开盘表现（新浪接口）
- A股科技指数（新浪接口）
- A股科技龙头竞价/行情（腾讯接口）
- 综合预判并发送邮件
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

# ============ 配置 ============

# 美股科技标的（新浪gb_前缀）
US_SYMBOLS = {
    '纳斯达克指数': 'gb_ixic',
    '英伟达': 'gb_nvda',
    'AMD': 'gb_amd',
    '台积电': 'gb_tsm',
    '美光科技': 'gb_mu',
    '英特尔': 'gb_intc',
    '高通': 'gb_qcom',
    '博通': 'gb_avgo',
    '迈威尔': 'gb_mrvl',
}

# 港股科技标的（新浪hk前缀）
HK_SYMBOLS = {
    '中芯国际': 'hk00981',
    '小米集团': 'hk01810',
    '腾讯控股': 'hk00700',
    '美团': 'hk03690',
    '阿里巴巴': 'hk09988',
    '商汤科技': 'hk00020',
    '比亚迪电子': 'hk00285',
    '联想集团': 'hk00992',
}

# A股科技指数
A_INDEXES = {
    '科创50': 'sh000688',
    '创业板指': 'sz399006',
    '中证TMT': 'sh000998',
}

# A股科技龙头（腾讯格式: shxxx / szxxx）
A_LEADERS = {
    '中芯国际': 'sh688981',
    '北方华创': 'sz002371',
    '海光信息': 'sh688041',
    '中兴通讯': 'sz000063',
    '立讯精密': 'sz002475',
    '韦尔股份': 'sh603501',
    '兆易创新': 'sh603986',
    '澜起科技': 'sh688008',
    '中微公司': 'sh688012',
    '寒武纪': 'sh688256',
    '长电科技': 'sh600584',
    '沪硅产业': 'sh688126',
    '紫光国微': 'sz002049',
    '晶盛机电': 'sz300316',
    '通富微电': 'sz002156',
}

# ============ 通用HTTP获取 ============

def fetch_sina(codes):
    """通过新浪接口获取行情"""
    url = f"https://hq.sinajs.cn/list={','.join(codes)}"
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://finance.sina.com.cn'
        })
        resp = urllib.request.urlopen(req, timeout=15)
        return resp.read().decode('gbk', errors='ignore')
    except Exception as e:
        print(f"    新浪接口请求失败: {e}")
        return None

def fetch_tencent(codes):
    """通过腾讯接口获取行情"""
    url = f"https://qt.gtimg.cn/q={','.join(codes)}"
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        resp = urllib.request.urlopen(req, timeout=15)
        return resp.read().decode('gbk', errors='ignore')
    except Exception as e:
        print(f"    腾讯接口请求失败: {e}")
        return None

# ============ 数据获取 ============

def parse_us_data(raw):
    """解析新浪美股数据"""
    results = {}
    sina_map = {v: k for k, v in US_SYMBOLS.items()}
    for line in raw.strip().split('\n'):
        m = re.search(r'var hq_str_(gb_[^=]+)="([^"]*)"', line)
        if not m:
            continue
        code, content = m.group(1), m.group(2)
        fields = content.split(',')
        if len(fields) < 3 or not fields[1]:
            continue
        name = sina_map.get(code, code)
        try:
            price = float(fields[1])
            change_pct = float(fields[2])
            prev_close = float(fields[9]) if len(fields) > 9 and fields[9] else price / (1 + change_pct/100) if change_pct != -100 else price
            results[name] = {
                'symbol': code.replace('gb_', '').upper(),
                'price': price,
                'change_pct': change_pct,
                'change_amount': price - prev_close,
                'prev_close': prev_close,
            }
        except (ValueError, IndexError, ZeroDivisionError):
            continue
    return results

def parse_hk_data(raw):
    """解析新浪港股数据"""
    results = {}
    sina_map = {v: k for k, v in HK_SYMBOLS.items()}
    for line in raw.strip().split('\n'):
        m = re.search(r'var hq_str_(hk\d+)=\"([^\"]*)\"', line)
        if not m:
            continue
        code, content = m.group(1), m.group(2)
        fields = content.split(',')
        if len(fields) < 10:
            continue
        name = sina_map.get(code, code)
        try:
            price = float(fields[2])
            change_pct = float(fields[8])
            results[name] = {
                'code': code.replace('hk', ''),
                'price': price,
                'change_pct': change_pct,
                'change_amount': float(fields[7]),
            }
        except (ValueError, IndexError):
            continue
    return results

def parse_a_index(raw):
    """解析新浪A股指数数据"""
    results = {}
    sina_map = {v: k for k, v in A_INDEXES.items()}
    for line in raw.strip().split('\n'):
        m = re.search(r'var hq_str_(sh\d+|sz\d+)=\"([^\"]*)\"', line)
        if not m:
            continue
        code, content = m.group(1), m.group(2)
        fields = content.split(',')
        if len(fields) < 4:
            continue
        name = sina_map.get(code, code)
        try:
            # 格式: 名称, 昨收, 今开, 最新价, 最高, 最低, ...
            prev_close = float(fields[1])
            current = float(fields[3])
            change_pct = (current - prev_close) / prev_close * 100 if prev_close else 0
            results[name] = {
                'code': code,
                'price': current,
                'prev_close': prev_close,
                'change_pct': change_pct,
                'change_amount': current - prev_close,
                'high': float(fields[4]) if len(fields) > 4 else 0,
                'low': float(fields[5]) if len(fields) > 5 else 0,
            }
        except (ValueError, IndexError):
            continue
    return results

def parse_a_leaders(raw):
    """解析腾讯A股数据"""
    results = {}
    tencent_map = {v: k for k, v in A_LEADERS.items()}
    for line in raw.strip().split('\n'):
        if not line.strip():
            continue
        m = re.search(r'v_(sh|sz)(\d+)="([^"]*)"', line)
        if not m:
            continue
        prefix, code, content = m.group(1), m.group(2), m.group(3)
        key = f"{prefix}{code}"
        fields = content.split('~')
        if len(fields) < 50:
            continue
        try:
            results[key] = {
                'code': code,
                'name': fields[1],
                'price': float(fields[3]) if fields[3] else 0,
                'prev_close': float(fields[4]) if fields[4] else 0,
                'open': float(fields[5]) if fields[5] else 0,
                'change_pct': float(fields[32]) if fields[32] else 0,
                'volume': int(fields[6]) if fields[6] else 0,
                'turnover': float(fields[38]) if fields[38] else 0,
                'circ_market': float(fields[44]) if fields[44] else 0,
                'pe': float(fields[39]) if fields[39] else None,
                'volume_ratio': float(fields[49]) if fields[49] else 0,
                'high': float(fields[33]) if fields[33] else 0,
                'low': float(fields[34]) if fields[34] else 0,
            }
        except (ValueError, IndexError):
            continue
    return results

# ============ 分析逻辑 ============

def analyze_us(us_data):
    """分析美股科技信号"""
    sig = {'nasdaq': {'score': 0, 'direction': '无数据'},
           'semis': {'score': 0, 'direction': '无数据'},
           'overall': {'score': 0, 'direction': '无数据'}}
    if not us_data:
        return sig
    
    ndx = us_data.get('纳斯达克指数')
    if ndx:
        pct = ndx.get('change_pct', 0)
        if pct > 1.5: sig['nasdaq'] = {'score': 25, 'direction': f'🔴 强涨 +{pct:.2f}%'}
        elif pct > 0.5: sig['nasdaq'] = {'score': 12, 'direction': f'🟢 上涨 +{pct:.2f}%'}
        elif pct < -1.5: sig['nasdaq'] = {'score': -25, 'direction': f'🔴 强跌 {pct:.2f}%'}
        elif pct < -0.5: sig['nasdaq'] = {'score': -12, 'direction': f'🟢 下跌 {pct:.2f}%'}
        else: sig['nasdaq'] = {'score': 0, 'direction': f'⚪ 平盘 {pct:.2f}%'}
    
    semi_scores = []
    for name in ['英伟达', 'AMD', '台积电']:
        d = us_data.get(name)
        if d:
            pct = d.get('change_pct', 0)
            if pct > 2: semi_scores.append(18)
            elif pct > 1: semi_scores.append(8)
            elif pct < -2: semi_scores.append(-18)
            elif pct < -1: semi_scores.append(-8)
            else: semi_scores.append(0)
    
    if semi_scores:
        avg = sum(semi_scores) / len(semi_scores)
        sig['semis']['score'] = int(avg)
        if avg > 8: sig['semis']['direction'] = '🔴 半导体强势'
        elif avg < -8: sig['semis']['direction'] = '🔴 半导体弱势'
        else: sig['semis']['direction'] = '⚪ 半导体平稳'
    
    total = sig['nasdaq']['score'] + sig['semis']['score']
    sig['overall']['score'] = total
    if total >= 25: sig['overall']['direction'] = '🟢 美股科技偏强 → A股科技高开概率大'
    elif total <= -25: sig['overall']['direction'] = '🔴 美股科技偏弱 → A股科技承压'
    elif total > 0: sig['overall']['direction'] = '🟡 美股科技温和 → A股科技小高开'
    elif total < 0: sig['overall']['direction'] = '🟡 美股科技偏弱 → A股科技小低开'
    else: sig['overall']['direction'] = '⚪ 美股无明显方向 → 看A股自身博弈'
    return sig

def analyze_hk(hk_data):
    """分析港股科技信号"""
    if not hk_data:
        return {'score': 0, 'direction': '无数据', 'details': []}
    scores = []
    details = []
    for name, d in hk_data.items():
        pct = d.get('change_pct', 0)
        if pct > 2: scores.append(15); details.append(f"{name} +{pct:.1f}% 🔥")
        elif pct > 1: scores.append(8); details.append(f"{name} +{pct:.1f}%")
        elif pct < -2: scores.append(-15); details.append(f"{name} {pct:.1f}% 📉")
        elif pct < -1: scores.append(-8); details.append(f"{name} {pct:.1f}%")
        else: scores.append(0)
    
    avg = sum(scores) / len(scores) if scores else 0
    if avg > 10: direction = '🟢 港股科技强势 → A股科技有支撑'
    elif avg < -10: direction = '🔴 港股科技偏弱 → 拖累A股'
    elif avg > 0: direction = '🟡 港股温和偏强'
    elif avg < 0: direction = '🟡 港股温和偏弱'
    else: direction = '⚪ 港股无明显方向'
    return {'score': int(avg), 'direction': direction, 'details': details}

def analyze_a_index(index_data):
    """分析A股科技指数信号"""
    if not index_data:
        return {'score': 0, 'direction': '无数据'}
    
    kc50 = index_data.get('科创50', {})
    cyb = index_data.get('创业板指', {})
    
    scores = []
    notes = []
    for name in ['科创50', '创业板指']:
        d = index_data.get(name)
        if not d:
            continue
        pct = d.get('change_pct', 0)
        if pct > 1.5: scores.append(12); notes.append(f"{name} +{pct:.2f}% 🔥")
        elif pct > 0.5: scores.append(5); notes.append(f"{name} +{pct:.2f}%")
        elif pct < -1.5: scores.append(-12); notes.append(f"{name} {pct:.2f}% 📉")
        elif pct < -0.5: scores.append(-5); notes.append(f"{name} {pct:.2f}%")
        else: scores.append(0); notes.append(f"{name} {pct:.2f}%")
    
    avg = sum(scores) / len(scores) if scores else 0
    if avg > 8: direction = '🟢 A股科技指数强势'
    elif avg < -8: direction = '🔴 A股科技指数弱势'
    elif avg > 0: direction = '🟡 科技指数偏强'
    elif avg < 0: direction = '🟡 科技指数偏弱'
    else: direction = '⚪ 科技指数平稳'
    
    return {'score': int(avg), 'direction': direction, 'notes': notes, 'data': index_data}

def analyze_a_leaders(leader_data):
    """分析A股科技龙头"""
    if not leader_data:
        return {'score': 0, 'direction': '无数据', 'leaders': [], 'top_gainers': [], 'top_losers': []}
    
    leaders = []
    for name, code_key in A_LEADERS.items():
        d = leader_data.get(code_key)
        if not d:
            continue
        leaders.append({
            'name': name,
            'code': d['code'],
            'price': d['price'],
            'change_pct': d['change_pct'],
            'volume_ratio': d.get('volume_ratio', 0),
            'circ_market': d.get('circ_market', 0),
        })
    
    leaders.sort(key=lambda x: x['change_pct'], reverse=True)
    up_count = sum(1 for l in leaders if l['change_pct'] > 0)
    down_count = sum(1 for l in leaders if l['change_pct'] < 0)
    avg_change = sum(l['change_pct'] for l in leaders) / len(leaders) if leaders else 0
    
    top_gainers = [l for l in leaders if l['change_pct'] > 2][:3]
    top_losers = [l for l in leaders if l['change_pct'] < -2][:3]
    
    if avg_change > 1.5: direction = '🟢 A股科技龙头集体强势'
    elif avg_change < -1.5: direction = '🔴 A股科技龙头集体弱势'
    elif avg_change > 0.5: direction = '🟡 龙头偏强'
    elif avg_change < -0.5: direction = '🟡 龙头偏弱'
    else: direction = '⚪ 龙头分化'
    
    return {
        'score': int(avg_change * 10),
        'direction': direction,
        'avg_change': avg_change,
        'up_count': up_count,
        'down_count': down_count,
        'leaders': leaders,
        'top_gainers': top_gainers,
        'top_losers': top_losers,
    }

def overall_judgment(us_sig, hk_sig, idx_sig, leader_sig):
    """综合预判"""
    total = (us_sig.get('overall', {}).get('score', 0) +
             hk_sig.get('score', 0) +
             idx_sig.get('score', 0) +
             leader_sig.get('score', 0))
    
    if total >= 35:
        return '🔴 偏多', total, '多层信号共振偏强，科技板块高开概率大，关注领涨龙头持续性'
    elif total >= 18:
        return '🟢 偏多', total, '外围偏强+内部龙头有支撑，科技板块温和高开，精选个股优于板块'
    elif total <= -35:
        return '🔴 偏空', total, '多层信号共振偏弱，科技板块低开承压，谨慎追高，关注抗跌品种'
    elif total <= -18:
        return '🟢 偏空', total, '外围偏弱，A股科技承压，等待企稳信号'
    elif total > 0:
        return '🟡 中性偏多', total, '信号混杂偏积极，科技板块可能高开震荡，关注成交量能否放大'
    elif total < 0:
        return '🟡 中性偏空', total, '信号混杂偏谨慎，科技板块可能低开震荡，关注承接力度'
    else:
        return '⚪ 中性', total, '无明确方向，市场等待催化，聚焦个股业绩/事件驱动'

# ============ 报告生成 ============

def generate_report(us_data, hk_data, idx_data, leader_data, us_sig, hk_sig, idx_sig, leader_sig):
    """生成晨间扫描报告"""
    lines = []
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    lines.append("=" * 70)
    lines.append(f"📡 科技板块晨间扫描器 - {now}")
    lines.append("=" * 70)
    lines.append("")
    
    direction, score, note = overall_judgment(us_sig, hk_sig, idx_sig, leader_sig)
    lines.append(f"【综合预判】{direction}  综合评分: {score}/100")
    lines.append(f"  {note}")
    lines.append("")
    
    # === 美股 ===
    lines.append("━" * 70)
    lines.append("🇺🇸 美股科技隔夜走势")
    lines.append("━" * 70)
    if us_data:
        ndx = us_data.get('纳斯达克指数', {})
        if ndx:
            lines.append(f"  纳斯达克指数: {ndx.get('price', 0):,.2f}  {ndx.get('change_pct', 0):+.2f}%")
        lines.append(f"  半导体信号: {us_sig.get('semis', {}).get('direction', '无')}")
        for name in ['英伟达', 'AMD', '台积电', '美光科技', '博通', '英特尔']:
            d = us_data.get(name)
            if d:
                pct = d['change_pct']
                emoji = "🔺" if pct > 1 else "🔻" if pct < -1 else "➖"
                lines.append(f"  {emoji} {name}({d.get('symbol', '')}): {d['price']:.2f}  {pct:+.2f}%")
        lines.append(f"  → {us_sig.get('overall', {}).get('direction', '无')}")
    else:
        lines.append("  ⚠️ 美股数据获取失败（请自行关注纳斯达克/英伟达隔夜走势）")
    lines.append("")
    
    # === 港股 ===
    lines.append("━" * 70)
    lines.append("🇭🇰 港股科技表现")
    lines.append("━" * 70)
    if hk_data:
        for name, d in hk_data.items():
            pct = d['change_pct']
            emoji = "🔺" if pct > 1.5 else "🔻" if pct < -1.5 else "➖"
            lines.append(f"  {emoji} {name}({d.get('code', '')}): {d['price']:.2f}  {pct:+.2f}%")
        lines.append(f"  → {hk_sig.get('direction', '无')}")
        if hk_sig.get('details'):
            for d in hk_sig['details']:
                lines.append(f"     • {d}")
    else:
        lines.append("  ⚠️ 港股数据获取失败")
    lines.append("")
    
    # === A股指数 ===
    lines.append("━" * 70)
    lines.append("🇨🇳 A股科技板块指数")
    lines.append("━" * 70)
    if idx_data:
        for name in ['科创50', '创业板指']:
            d = idx_data.get(name)
            if d:
                pct = d['change_pct']
                emoji = "🔺" if pct > 1 else "🔻" if pct < -1 else "➖"
                lines.append(f"  {emoji} {name}({d.get('code', '')}): {d['price']:.2f}  {pct:+.2f}%")
        lines.append(f"  → {idx_sig.get('direction', '无')}")
    else:
        lines.append("  ⚠️ 指数数据获取失败")
    lines.append("")
    
    # === A股龙头 ===
    lines.append("━" * 70)
    lines.append("🇨🇳 A股科技龙头行情")
    lines.append("━" * 70)
    if leader_sig.get('leaders'):
        lines.append(f"  平均涨跌: {leader_sig.get('avg_change', 0):+.2f}%  上涨: {leader_sig.get('up_count', 0)}  下跌: {leader_sig.get('down_count', 0)}")
        lines.append("")
        if leader_sig.get('top_gainers'):
            lines.append("  🔺 领涨龙头:")
            for l in leader_sig['top_gainers']:
                lines.append(f"     {l['code']} {l['name']}  {l['change_pct']:+.2f}%  量比:{l.get('volume_ratio', 0):.1f}")
        if leader_sig.get('top_losers'):
            lines.append("  🔻 领跌龙头:")
            for l in leader_sig['top_losers']:
                lines.append(f"     {l['code']} {l['name']}  {l['change_pct']:+.2f}%")
        lines.append("")
        lines.append("  📋 全部哨兵:")
        lines.append(f"{'代码':<8} {'名称':<10} {'现价':<9} {'涨跌':<8} {'量比':<7}")
        lines.append("  " + "-" * 50)
        for l in leader_sig['leaders']:
            lines.append(f"  {l['code']:<8} {l['name']:<10} {l['price']:<9.2f} {l['change_pct']:<+8.2f}% {l.get('volume_ratio', 0):<7.1f}")
    else:
        lines.append("  ⚠️ A股数据获取失败")
    lines.append("")
    
    # === 操作建议 ===
    lines.append("━" * 70)
    lines.append("🎯 今日关注方向")
    lines.append("━" * 70)
    if "偏多" in direction and "🔴" in direction:
        lines.append("  • 关注领涨半导体龙头（北方华创、中微公司、中芯国际）")
        lines.append("  • 英伟达/AMD强势时，关注海光信息、寒武纪等算力链")
        lines.append("  • 避免追高涨幅>5%的跟风股，看龙头持续性")
    elif "偏空" in direction and "🔴" in direction:
        lines.append("  • 谨慎开仓，优先观察抗跌品种（中兴通讯、长电科技）")
        lines.append("  • 若低开低走，等待10:30后企稳信号")
        lines.append("  • 半导体弱势时，消费电子可能相对防御（立讯精密）")
    elif "偏多" in direction:
        lines.append("  • 高开不追，等回踩均线低吸核心龙头")
        lines.append("  • 关注量价配合，量比>1.5的标的优先")
    elif "偏空" in direction:
        lines.append("  • 控制仓位，不轻易抄底")
        lines.append("  • 关注能否在关键均线获得支撑")
    else:
        lines.append("  • 精选个股，不赌板块方向")
        lines.append("  • 关注有事件催化的标的（订单公告、行业政策）")
        lines.append("  • 量能萎缩时减少操作频率")
    
    lines.append("")
    lines.append("━" * 70)
    lines.append("📌 哨兵体系说明")
    lines.append("━" * 70)
    lines.append("  • 中芯国际 → 半导体制造情绪")
    lines.append("  • 北方华创 → 设备国产替代")
    lines.append("  • 海光信息 → CPU/GPU算力")
    lines.append("  • 中兴通讯 → 通信/5G")
    lines.append("  • 立讯精密 → 消费电子")
    lines.append("  • 每天先看这5只，再决定看不看板块")
    lines.append("")
    lines.append("⚠️ 免责声明: 本分析仅供学习研究，不构成投资建议")
    lines.append(f"  数据时间: {now}  |  来源: 新浪/腾讯行情")
    
    return "\n".join(lines)

# ============ 主流程 ============

def run_analysis():
    print(f"\n{'='*60}")
    print(f"科技板块晨间扫描器 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    # 1. 美股
    print("[1/4] 获取美股科技隔夜行情...")
    raw_us = fetch_sina(list(US_SYMBOLS.values()))
    us_data = parse_us_data(raw_us) if raw_us else {}
    us_sig = analyze_us(us_data)
    print(f"  纳斯达克: {us_sig.get('nasdaq', {}).get('direction', '无')}")
    
    # 2. 港股
    print("[2/4] 获取港股科技行情...")
    raw_hk = fetch_sina(list(HK_SYMBOLS.values()))
    hk_data = parse_hk_data(raw_hk) if raw_hk else {}
    hk_sig = analyze_hk(hk_data)
    print(f"  港股信号: {hk_sig.get('direction', '无')}")
    
    # 3. A股指数
    print("[3/4] 获取A股科技指数...")
    raw_idx = fetch_sina(list(A_INDEXES.values()))
    idx_data = parse_a_index(raw_idx) if raw_idx else {}
    idx_sig = analyze_a_index(idx_data)
    print(f"  科技指数: {idx_sig.get('direction', '无')}")
    
    # 4. A股龙头
    print("[4/4] 获取A股科技龙头...")
    raw_a = fetch_tencent(list(A_LEADERS.values()))
    leader_data = parse_a_leaders(raw_a) if raw_a else {}
    leader_sig = analyze_a_leaders(leader_data)
    print(f"  龙头平均: {leader_sig.get('avg_change', 0):+.2f}%  涨:{leader_sig.get('up_count', 0)} 跌:{leader_sig.get('down_count', 0)}")
    
    # 生成报告
    report = generate_report(us_data, hk_data, idx_data, leader_data, us_sig, hk_sig, idx_sig, leader_sig)
    
    report_path = f"/tmp/tech_sector_scan_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n报告已保存: {report_path}")
    
    return report, report_path

# ============ 入口 ============

if __name__ == '__main__':
    report, report_path = run_analysis()
    print("\n" + report)
    
    try:
        skill_dir = '/root/.openclaw/workspace/skills/imap-smtp-email-chinese'
        result = subprocess.run(
            [
                'node', f'{skill_dir}/scripts/smtp.js', 'send',
                '--to', 'hansonnan.ding@sc.com,leo.sun@sc.com,jacky.an@sc.com',
                '--subject', f'科技板块晨间扫描 - {datetime.now().strftime("%Y-%m-%d %H:%M")}',
                '--body', report,
                '--attach', report_path
            ],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            print("\n邮件通知已发送")
        else:
            print(f"\n邮件发送失败: {result.stderr}")
    except Exception as e:
        print(f"\n邮件发送失败: {e}")
