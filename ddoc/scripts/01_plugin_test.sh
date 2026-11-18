# Quick smoke for the plugin subsystem (Round-5 update — v1 names removed).
# These commands are safe to copy-paste line-by-line.

# 도움말
ddoc --help
ddoc plugin --help

# 플러그인 목록/정보
ddoc plugin list
ddoc plugin info ddoc_builtins   # core ops module — always present

# 플러그인 설치 (PyPI 또는 editable)
# pip install ddoc-plugin-nlp                       # PyPI
# pip install -e plugins/ddoc-plugin-timeseries     # editable
ddoc plugin list
ddoc plugin info ddoc_timeseries

# v2 의 drift 호출 (path mode 또는 snapshot mode)
# ddoc analyze drift --data-path-ref /path/ref --data-path-cur /path/cur --json
# ddoc analyze drift baseline current --json

# Note: v1 의 `ddoc drift --ref ... --cur ...` 와 `ddoc transform` 은
# v2 에서 제거됨. transform 대체는 plugin 의 `eda_run` / `drift_detect`
# hookspec 으로 흡수되었음.
