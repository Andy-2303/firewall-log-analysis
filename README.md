# Firewall Traffic Log Analysis

Exploratory analysis of a public firewall session dataset: how much traffic is allowed vs. blocked, which destination ports and services are blocked most, and which sessions look unusual.

## Dataset
[Internet Firewall Data](https://archive.ics.uci.edu/dataset/542/internet+firewall+data) (UCI Machine Learning Repository, also on Kaggle). Download `log2.csv` and place it in `data/`.
Each row is a logged session with source/destination ports, action (allow, deny, drop, reset-both), bytes, packets and duration. The dataset has no IP addresses or timestamps.

## Questions answered
1. What share of sessions does the firewall allow vs. block, and by which action?
2. Which destination ports carry the most traffic, and which have the highest block rate?
3. How does traffic volume differ between allowed and blocked sessions?
4. Which sessions are outliers by size, and which allowed sessions are one-way?

## Key findings
<!-- Fill in after running the notebook, using your actual results -->
- 
- 
- 

## How to run
```bash
git clone <your-repo-url>
cd firewall-log-analysis
pip install -r requirements.txt
# place log2.csv in data/
jupyter notebook firewall_log_analysis.ipynb
```

## Tools
Python, pandas, numpy, matplotlib, seaborn

## Limitations
No IP addresses or timestamps, so the analysis cannot cover source-based scanning or time-of-day patterns. Block rates for low-volume ports are filtered (minimum 50 sessions) to avoid misleading percentages.
