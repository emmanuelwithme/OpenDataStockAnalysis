from fake_useragent import UserAgent
import pandas as pd
import time
import random
import requests
import io
import plotly

stackNo = "0050"
date = 20220101  # 起始年月份(都是只要1日)
date_max = 20220201  # 現在最新年月份
ua = UserAgent()
data = pd.DataFrame()
while date <= date_max:
    time.sleep(1.5+1*random.random())
    data_url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=csv&date=" + \
        str(date)+"&stockNo="+str(stackNo)
    headers = {'User-Agent': ua.random}
    try:
        s = requests.get(data_url, headers=headers).content
        data_new = pd.read_csv(io.StringIO(s.decode('big5')), encoding='big5', skiprows=1, usecols=[
                               "日期", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數"])

        # 刪除最後4-5行說明文字，判斷 成交股數==nan 就刪除
        for index, row in data_new.iterrows():
            # print(row, " type", type(row))
            # print(row.成交股數)
            if (pd.isna(row.成交筆數)):
                data_new.drop(labels=None, axis=0, index=index,
                              columns=None, level=None, inplace=True, errors='raise')
                # axis – Default 0 -> 0 drop rows 1 drop columns.

        data = data.append(data_new, ignore_index=True)
        print(data_new)
    except Exception:
        print("連線被伺服器阻擋了!!!!!!!")
    if int(int(date/100) % 100) == 12:
        date += 8900
    else:
        date += 100

print('='*20)
print(data)
# data.to_csv("data/"+str(stackNo)+'.csv')

fig = plotly.graph_objects.Figure(data_kicker=[plotly.graph_objects.Candlestick(x=data['日期'],open=data['開盤價'], high=data['最高價'],
                                                                                low=data['最低價'],
                                                                                close=data['收盤價'])])
fig.show()
