# RQ2 SHAP Top-k

Shared cohort: **1,363** flows.

## Samples per true class

| Class | Samples |
|---|---:|
| Benign | 100 |
| Bot | 100 |
| Brute Force -Web | 100 |
| Brute Force -XSS | 46 |
| DDOS attack-HOIC | 100 |
| DDOS attack-LOIC-UDP | 100 |
| DDoS attacks-LOIC-HTTP | 100 |
| DoS attacks-GoldenEye | 100 |
| DoS attacks-Hulk | 100 |
| DoS attacks-SlowHTTPTest | 100 |
| DoS attacks-Slowloris | 100 |
| FTP-BruteForce | 100 |
| Infilteration | 100 |
| SQL Injection | 17 |
| SSH-Bruteforce | 100 |

## Prediction summary

Correct predictions: **1,152/1,363**.

## Most frequent SHAP Top-1 feature

| True class | Feature | Count |
|---|---|---:|
| Benign | Fwd Pkt Len Max | 54 |
| Bot | Dst Port | 96 |
| Brute Force -Web | Init Fwd Win Byts | 31 |
| Brute Force -XSS | Init Fwd Win Byts | 23 |
| DDOS attack-HOIC | Init Fwd Win Byts | 100 |
| DDOS attack-LOIC-UDP | Tot Fwd Pkts | 98 |
| DDoS attacks-LOIC-HTTP | Init Fwd Win Byts | 44 |
| DoS attacks-GoldenEye | Fwd Seg Size Min | 100 |
| DoS attacks-Hulk | Fwd Seg Size Min | 100 |
| DoS attacks-SlowHTTPTest | Fwd Seg Size Min | 100 |
| DoS attacks-Slowloris | Bwd IAT Max | 71 |
| FTP-BruteForce | Fwd Seg Size Min | 100 |
| Infilteration | Fwd Pkt Len Max | 53 |
| SQL Injection | Init Fwd Win Byts | 7 |
| SSH-Bruteforce | Dst Port | 100 |

## Next step

Run LIME on exactly `rq2_shared_samples.csv`. Use `feature_key` to normalize LIME condition names before calculating Overlap and Jaccard for k = 1, 3, 5.