# finrl-trading-project

## 光明日报关键词词频爬取脚本

新增脚本：`scripts/gmrb_climate_risk_freq.py`

用于统计《光明日报》新闻中关键词（默认“气候风险”）在 2000-2024 年区间的出现词频（按年汇总），输出：

- `results/gmrb_climate_risk_2000_2024.csv`
- `results/gmrb_climate_risk_2000_2024.json`

### 运行方式

```bash
python scripts/gmrb_climate_risk_freq.py
```

可选参数：

```bash
python scripts/gmrb_climate_risk_freq.py \
  --keyword 气候风险 \
  --start 2000-01-01 \
  --end 2024-12-31 \
  --out-prefix results/gmrb_climate_risk_2000_2024
```

若仅调试（抓取少量日期）：

```bash
python scripts/gmrb_climate_risk_freq.py --max-days 10
```
