import json
import numpy as np
import pandas as pd
import pytest
from yf_pipeline.analytics import performance,technical,td9,monthly_cagr
from yf_pipeline.collector import clean,run

def sample(n=500):
    idx=pd.bdate_range("2023-01-02",periods=n)
    x=np.linspace(100,150,n)
    return pd.DataFrame({"Open":x,"High":x+2,"Low":x-2,"Close":x,"Adj Close":x*1.04,
       "Volume":np.full(n,500000),"Dividends":np.zeros(n),"Stock Splits":np.zeros(n)},index=idx)

def test_indicators():
    a=technical(sample())
    assert a["ma200"] is not None
    assert a["macd_histogram"] is not None
    assert a["rsi14"]==100.
    assert a["high_td9_setup"]==9
    fx=sample();fx["Volume"]=0
    assert technical(fx)["emv_14"] is None

def test_drawdown():
    s=pd.Series([100,120,80,100,125],index=pd.bdate_range("2023-01-02",periods=5))
    f=pd.DataFrame({"Adj Close":s})
    r=performance(f)
    assert r["max_drawdown"]==pytest.approx(-1/3,abs=1e-6)
    assert r["recovery_date"]==str(s.index[-1].date())

def test_insufficient_history():
    r=performance(sample())
    assert r["cagr_1y"] is not None
    assert r["cagr_5y"] is None
    assert r["cagr_15y_monthly"] is None

def test_missing_data_bad_high_low():
    s=sample();s.iloc[-1,s.columns.get_loc("High")]=1
    with pytest.raises(ValueError,match="High below Low"):clean(s)

def test_monthly_compounding():
    dates=pd.date_range("2000-01-31",periods=249,freq="ME")
    s=pd.Series(100*1.01**np.arange(len(dates)),index=dates)
    assert monthly_cagr(s,36)==pytest.approx(1.01**12-1,abs=1e-6)
    assert monthly_cagr(s,180)==pytest.approx(1.01**12-1,abs=1e-6)

def test_mocked_run(tmp_path):
    (tmp_path/"config").mkdir()
    (tmp_path/"config/symbols.json").write_text(json.dumps({"symbols":[{"ticker":"VOO"}]}))
    status=run(tmp_path,loader=lambda s:sample())
    assert status["symbols"]["VOO"]["status"]=="ok"
    result=json.loads((tmp_path/"outputs/latest_snapshot.json").read_text())
    assert "VOO" in result["records"]
    assert (tmp_path/"data/history/VOO.csv.gz").exists()
