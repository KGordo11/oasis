"""The "LLM Bias V3 Data" page: cleaning, then V3 vs V3a and V1 vs V3, small to big (log 14.62). Stdlib only.

    python3 examples/experiment/llm_bias/v3_report_data.py data/llm_bias/v3_report.json   (first)
    python3 examples/experiment/llm_bias/make_v3_data_page.py <out.html> [data/llm_bias/v3_report.json]

Every number comes from v3_report.json (v3_report_data.py), so the page and the Excel file always agree. The page's
CSS is the same as the "Inside LLM Bias" pages (inside_v2_template.html).
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1]
REPORT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "../../../data/llm_bias/v3_report.json")

data = json.load(open(REPORT))
tpl = open(os.path.join(HERE, "v3_data_template.html")).read()
css = re.search(r"<style>(.*?)</style>", open(os.path.join(HERE, "inside_v2_template.html")).read(), re.S)[1]
html = tpl.replace("/*__CSS__*/", css).replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")).replace("</", "<\\/"))
open(OUT, "w").write(html)
print(f"wrote {OUT}: {len(html) / 1e6:.2f} MB; runs {data['runs']}")
