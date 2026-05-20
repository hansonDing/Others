import pandas as pd
import urllib.request
import re
import time
from datetime import datetime
import json

def fetch_tencent_batch(codes, timeout=30):
    """从腾讯接口批量获取股票实时行情"""
    url = f"https://qt.gtimg.cn/q={','.join(codes)}"
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = resp.read().decode('gbk', errors='ignore')
        return data
    except Exception as e:
        print(f"请求失败: {e}")
        return None

def parse_tencent_data(raw_data):
    """解析腾讯接口返回的数据"""
    stocks = []
    for line in raw_data.strip().split('\n'):
        if not line.strip():
            continue
        m = re.search(r'v_(sh|sz)(\d+)="([^"]*)"', line)
        if not m:
            continue
        prefix, code, content = m.group(1), m.group(2), m.group(3)
        fields = content.split('~')
        if len(fields) < 40:
            continue
        
        try:
            stock = {
                'code': code,
                'market': prefix,
                'name': fields[1],
                'price': float(fields[3]) if fields[3] else 0,
                'prev_close': float(fields[4]) if fields[4] else 0,
                'open': float(fields[5]) if fields[5] else 0,
                'volume': int(fields[6]) if fields[6] else 0,
                'high': float(fields[33]) if fields[33] else 0,
                'low': float(fields[34]) if fields[34] else 0,
                'change_amount': float(fields[31]) if fields[31] else 0,
                'change_pct': float(fields[32]) if fields[32] else 0,
                'turnover': float(fields[38]) if fields[38] else 0,
                'pe': float(fields[39]) if fields[39] else None,
                'pb': float(fields[46]) if fields[46] else None,
                'total_market': float(fields[45]) if fields[45] else 0,
                'circ_market': float(fields[44]) if fields[44] else 0,
                'volume_ratio': float(fields[49]) if fields[49] else 0,
                'amplitude': float(fields[43]) if fields[43] else 0,
                'time': fields[30],
            }
            stocks.append(stock)
        except (ValueError, IndexError) as e:
            continue
    return stocks

def get_all_stock_codes():
    """获取全市场股票代码列表"""
    import akshare as ak
    df = ak.stock_info_a_code_name()
    codes = []
    for _, row in df.iterrows():
        code = str(row['code']).zfill(6)
        # 判断市场
        if code.startswith('6') or code.startswith('68'):
            codes.append(f"sh{code}")
        elif code.startswith('0') or code.startswith('3'):
            codes.append(f"sz{code}")
        elif code.startswith('4') or code.startswith('8'):
            # 北交所/新三板，暂不支持
            continue
        else:
            # 其他，默认上海
            codes.append(f"sh{code}")
    return codes

def scan_market(change_pct_threshold=3.0):
    """扫描全市场，找出涨幅超过阈值的股票"""
    print("获取股票代码列表...")
    all_codes = get_all_stock_codes()
    print(f"共 {len(all_codes)} 只股票")
    
    all_stocks = []
    batch_size = 100
    total_batches = (len(all_codes) + batch_size - 1) // batch_size
    
    for i in range(0, len(all_codes), batch_size):
        batch = all_codes[i:i+batch_size]
        batch_num = i // batch_size + 1
        print(f"请求批次 {batch_num}/{total_batches} ({len(batch)}只)...", end=' ')
        
        raw = fetch_tencent_batch(batch)
        if raw:
            stocks = parse_tencent_data(raw)
            all_stocks.extend(stocks)
            print(f"返回 {len(stocks)} 只")
        else:
            print("失败")
        
        # 适当延时，避免触发频率限制
        if batch_num < total_batches:
            time.sleep(0.3)
    
    print(f"\n共获取 {len(all_stocks)} 只股票数据")
    
    # 转换为DataFrame
    df = pd.DataFrame(all_stocks)
    if len(df) == 0:
        return df
    
    # 筛选涨幅超过阈值的股票
    hot_stocks = df[df['change_pct'] >= change_pct_threshold].copy()
    hot_stocks = hot_stocks.sort_values('change_pct', ascending=False)
    
    print(f"涨幅 ≥ {change_pct_threshold}% 的股票: {len(hot_stocks)} 只")
    return hot_stocks

if __name__ == '__main__':
    start = time.time()
    result = scan_market(change_pct_threshold=3.0)
    elapsed = time.time() - start
    print(f"\n耗时: {elapsed:.1f}秒")
    
    if len(result) > 0:
        print("\n=== 涨幅 ≥ 3% 的股票 ===")
        display_cols = ['code', 'name', 'price', 'change_pct', 'turnover', 'pe', 'volume_ratio']
        print(result[display_cols].head(20).to_string(index=False))
        
        # 保存结果
        result.to_csv(f'/tmp/hot_stocks_{datetime.now().strftime("%Y%m%d")}.csv', 
                      index=False, encoding='utf-8-sig')
        print(f"\n结果已保存到 /tmp/hot_stocks_{datetime.now().strftime('%Y%m%d')}.csv")
