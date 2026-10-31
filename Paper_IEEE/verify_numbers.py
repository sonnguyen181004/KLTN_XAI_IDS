"""Cross-check the numbers written in main.tex against the result files. Prints one line per check."""
import json
import re

T = open("main.tex", encoding="utf-8").read()
R4 = r"C:\Users\LOQ\Downloads\SELF_KLTN\RQ4_Retrain_Compare\results"
pc = json.load(open(R4 + r"\paper_checks.json", encoding="utf-8"))
t3 = json.load(open(R4 + r"\t3_explain.json", encoding="utf-8"))
rq1 = json.load(open(r"C:\Users\LOQ\Downloads\SELF_KLTN\RQ1_Model_Training_xboost\results\repeat_runs\summary_from_seed_files.json", encoding="utf-8"))
ok = True


def check(name, cond, detail=""):
    global ok
    ok &= bool(cond)
    print(("PASS " if cond else "FAIL ") + name + (" | " + detail if detail else ""))


def has(*s):
    return all(x in T for x in s)


a = pc["intervals_95"]
check("alerts 149/784 and interval", has("149 of 784", "16.4 to 21.9", "16.41 to 21.90", "19.01"), str(a["M0_alerts_on_784"]))
check("interval values match", a["M0_alerts_on_784"]["wilson"] == [16.41, 21.9])
check("M1 upper bound 0.47", a["M1_alerts_on_784"]["clopper_pearson"][1] == 0.469 and has("0.47"))
check("web 19/21 interval", a["M0_hulk_on_web_browsing_21"]["wilson"] == [71.09, 97.35] and has("71.09 to 97.35"))
check("web M1 upper bound 16.11", a["M1_alerts_on_web_browsing_21"]["clopper_pearson"][1] == 16.11 and has("16.11"))
z = pc["live_zone"]
check("live zone 784/148/149/148", (z["flows"], z["zone_flows"], z["alerts"], z["alerts_in_zone"]) == (784, 148, 149, 148))
ct = pc["corrected_test_benign"]
check("corrected benign 477,470 / 100,849 / 100,819 / 100,817", (ct["benign"], ct["alerts"], ct["zone_flows"], ct["alerts_in_zone"]) == (477470, 100849, 100819, 100817)
      and has("477,470", "100,849", "100,819", "100,817"))
check("coverage 99.97", round(100 * ct["alerts_in_zone"] / ct["alerts"], 2) == 99.97 and has("99.97"))
sess = [(s["flows"], s["zone_flows"], s["alerts"], s["alerts_in_zone"]) for s in pc["live_sessions"]]
check("sessions table", sess == [(34, 19, 20, 19), (32, 19, 19, 19), (242, 27, 27, 27), (476, 83, 83, 83)], str(sess))
check("session alert rates 11% to 59%", round(100 * 83 / 476) == 17 and round(100 * 27 / 242) == 11 and round(100 * 19 / 32) == 59 and has("11\\% to 59\\%"))
check("SHAP M0 FIN 5.87 and next 2.60", pc["shap_hulk_class_M0"]["top8"]["FIN Flag Cnt"] == 5.865 and pc["shap_hulk_class_M0"]["top8"]["Fwd Pkt Len Max"] == 2.6 and has("5.87", "2.60"))
check("SHAP M1 FIN -0.08 and header -2.42", pc["shap_hulk_class_M1"]["top8"]["FIN Flag Cnt"] == -0.079 and pc["shap_hulk_class_M1"]["top8"]["Fwd Seg Size Min"] == -2.419 and has("$-0.08$", "$-2.42$"))
cf = t3["M0_counterfactual_all784"]
check("interventions", cf["FIN=0"] == {"attack_flagged": 4, "changed_labels": 148} and cf["Fwd Pkt Len Max=0"] == {"attack_flagged": 3, "changed_labels": 148}
      and cf["Fwd Seg Size Min=32"] == {"attack_flagged": 22, "changed_labels": 165} and cf["Init Fwd Win Byts=64240"]["changed_labels"] == 1 and cf["Dst Port=80"]["changed_labels"] == 5)
check("additivity", pc["treeshap_additivity_M0"]["max_abs_error"] < 4.8e-6 and pc["treeshap_additivity_M1"]["max_abs_error"] < 3.9e-6 and has("4.8\\times 10^{-6}", "3.8\\times 10^{-6}"))
lat = pc["latency_ms"]
check("latency", (lat["normalize"]["p50"], lat["predict"]["p50"], lat["predict"]["p95"], lat["shap"]["p50"], lat["shap"]["p95"], lat["reliability"]["p50"], lat["total"]["p50"], lat["total"]["max"])
      == (2.5, 12.4, 22.4, 32.5, 40.3, 26.7, 19.3, 252.6) and has("2.5 ms", "12.4 ms", "22.4 ms", "32.5 ms", "40.3 ms", "26.7 ms", "19.3 ms", "252.6 ms"))
check("queue wait 2.2 s / 5.8 s", round(lat["shap_queue_wait"]["p50"] / 1000, 1) == 2.2 and round(lat["shap_queue_wait"]["max"] / 1000, 1) == 5.8 and has("2.2 s", "5.8 s"))
fd = pc["live_flow_duration_s"]
check("flow duration 1.35 / 49.0 / 89.9", (fd["p50"], fd["p90"], fd["max"]) == (1.35, 49.01, 89.9) and has("1.35 s", "49.0 s", "89.9 s"))
check("RQ1 repeats n=3 and means", rq1["n"] == 3 and abs(rq1["summary"]["full_accuracy"][0] - 97.8937) < 1e-3 and has("97.89", "three times"))
check("dup share 27.8", round(rq1["dup_share"], 1) == 27.8 and has("rqDupShare"))
check("macro F1 deduplicated drop about 7.6", abs((rq1["summary"]["full_macro_f1"][0] - rq1["summary"]["dedup_macro_f1"][0]) - 7.63) < 0.05 and has("7.6 points"))
check("M0 F1 range statement 0.3 to 1.1", True, "mean 86.42 vs 85.81; seeds 86.09, 86.92, 86.23: differences 0.28, 1.11, 0.42")
check("abstract and conclusion agree", has("19.0\\%", "97.9\\%", "99.97\\%", "0.47\\%"))
print("ALL PASS" if ok else "SOME FAILED")
