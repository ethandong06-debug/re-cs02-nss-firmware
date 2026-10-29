import hashlib, io, sys, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
o = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\output"
for n in ["immortalwrt-qualcommax-ipq60xx-jdcloud_re-cs-02-squashfs-sysupgrade.bin",
          "immortalwrt-qualcommax-ipq60xx-jdcloud_re-cs-02-squashfs-factory.bin"]:
    lp = os.path.join(o, n)
    h = hashlib.sha256(open(lp, "rb").read()).hexdigest()
    print("HASH", n, os.path.getsize(lp), h)
print("---official---")
print(open(os.path.join(o, "sha256sums"), "rb").read().decode("utf-8", "replace"))
