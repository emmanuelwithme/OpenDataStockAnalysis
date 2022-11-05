import json
import requests
from urllib import request
import flask
import pandas as pd
import io
import requests
from fake_useragent import UserAgent
import time
import random

app1 = flask.Flask(__name__)


@app1.route("/")
def hello():
    return flask.render_template("home_page.html")


@app1.route("/tellYouPopStock")
def tellYouPopStock():
    data_name_dict = {"Number": "股票數量",
                      "Code": "股票代碼", "Name": "股票名稱", "Date": "日期"}
    opendata_url = "https://openapi.twse.com.tw/v1/Announcement/BFZFZU_T"
    with request.urlopen(opendata_url) as response:
        data = json.load(response)
        print(data)
        print(type(data))
        for row in data:
            for key, value in data_name_dict.items():
                print(value, ": ", row[key])

    return flask.render_template("tell_you_pop_stock.html", data=data, data_name_dict=data_name_dict.items())


@app1.route("/stockPrice")
def stockPrice():
    data_name_dict = {"Code": "股票代號", "Name": "股票名稱",
                      "ClosingPrice": "日收盤價", "MonthlyAveragePrice": "月平均價"}
    opendata_url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_AVG_ALL"
    with request.urlopen(opendata_url) as response:
        data = json.load(response)
        # for individualStock in data:
        #     for key,value in individualStock.items():
        #         print(key,": ",value)
        #     print("-----------------------")
    return flask.render_template("stocks_price.html", data=data, data_name_dict=data_name_dict)


@app1.route("/individualStock", methods=['GET'])
def individualStock():
    # "stat":"查詢日期小於99年1月4日，請重新查詢!"
    stackNo = flask.request.args.get("stockNo")
    # stackNo = "0050"
    date = 20220101 # 起始年月份(都是只要1日)
    date_max = 20221101 # 現在最新年月份
    ua = UserAgent()
    data = pd.DataFrame()
    while date<=date_max:
        time.sleep(1.5+1*random.random())
        data_url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=csv&date="+str(date)+"&stockNo="+str(stackNo)
        headers = {'User-Agent': ua.random}
        try:
            s=requests.get(data_url,headers=headers).content
            data_new = pd.read_csv(io.StringIO(s.decode('big5')), encoding='big5', skiprows=1, usecols=["日期","成交股數","成交金額","開盤價","最高價","最低價","收盤價","漲跌價差","成交筆數"], index_col='日期')
            
            # 刪除最後4-5行說明文字，判斷 成交股數==nan 就刪除
            for index, row in data_new.iterrows():
                # print(row, " type", type(row))
                # print(row.成交股數)
                if(pd.isna(row.成交股數)):
                    data_new.drop(labels=None, axis=0, index=index, columns=None, level=None, inplace=True, errors='raise')
                    # axis – Default 0 -> 0 drop rows 1 drop columns.

            data = data.append(data_new)
            # print(data_new)
        except:
            print("Connection error!")
        if int(int(date/100)%100)==12: date+=8900
        else: date+=100

    # print('='*20)
    # print(data)
    # data.to_csv("data/"+str(stackNo)+'.csv')

    return flask.render_template("individual_stock.html",tables=[data.to_html(classes='data')], titles=data.columns.values)

if __name__ == "__main__":
    app1.run()
