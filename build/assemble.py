import json, os, sys

here = os.path.dirname(os.path.abspath(__file__))
tpl = open(os.path.join(here, "template.html"), encoding="utf-8").read()
data = open(os.path.join(here, "data.json"), encoding="utf-8").read()

# `<` only ever appears inside JSON string values here, so escaping it keeps a
# literal </script> from ever terminating the data block early.
data = data.replace("<", "\\u003c")

if "/*__DATA__*/" not in tpl:
    sys.exit("template.html is missing the /*__DATA__*/ placeholder")

out = tpl.replace("/*__DATA__*/", data)
dest = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "radio.html")
open(dest, "w", encoding="utf-8").write(out)
nb = len(out.encode())
print("wrote %s  (%.2f MB)" % (dest, nb / 1e6))
print("stations embedded:", len(json.loads(open(os.path.join(here, "data.json"), encoding="utf-8").read())["stations"]))
