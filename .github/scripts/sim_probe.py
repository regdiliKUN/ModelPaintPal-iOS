#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 iOS 模拟器里装好探针、启动、截图取证。

用法::

    python3 sim_probe.py <XXX.app 路径> <输出目录>

这个脚本只做取证，不做判断——判断由人看截图完成。它会把模拟器设成
最新 iOS 运行时里屏幕最大的 iPhone（Pro Max），因为那块屏正好是
App Store 截图要用的 6.9 寸。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time

WAIT_BOOT = 240
WAIT_LAUNCH = 25


def run(args, check=True):
    result = subprocess.run(args, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise SystemExit(f"命令失败: {' '.join(args)}\n{result.stdout}\n{result.stderr}")
    return result


def json_of(args):
    return json.loads(run(args).stdout)


def pick_runtime():
    runtimes = json_of(["xcrun", "simctl", "list", "runtimes", "-j"])["runtimes"]
    ios = [r for r in runtimes if r.get("platform") == "iOS" and r.get("isAvailable")]
    if not ios:
        raise SystemExit("没有可用的 iOS 模拟器运行时")

    def version_key(rt):
        return [int(p) for p in rt.get("version", "0").split(".") if p.isdigit()]

    ios.sort(key=version_key)
    return ios[-1]


def pick_device_type():
    types = json_of(["xcrun", "simctl", "list", "devicetypes", "-j"])["devicetypes"]
    iphones = [t for t in types if t["name"].startswith("iPhone")]
    if not iphones:
        raise SystemExit("没有可用的 iPhone 模拟器机型")

    def score(t):
        name = t["name"]
        return (
            "Pro Max" in name,
            int("".join(ch for ch in name.split()[-1] if ch.isdigit()) or 0)
            if name.split()[-1].isdigit()
            else 0,
        )

    iphones.sort(key=score)
    return iphones[-1]


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)

    app_path = os.path.abspath(sys.argv[1])
    out_dir = os.path.abspath(sys.argv[2])
    os.makedirs(out_dir, exist_ok=True)

    if not os.path.isdir(app_path):
        raise SystemExit(f"找不到 app 包: {app_path}")

    runtime = pick_runtime()
    device_type = pick_device_type()
    print(f"运行时: {runtime['name']} ({runtime['identifier']})")
    print(f"机型:   {device_type['name']} ({device_type['identifier']})")

    name = f"probe-{int(time.time())}"
    udid = run(["xcrun", "simctl", "create", name, device_type["identifier"], runtime["identifier"]]).stdout.strip()
    print(f"设备:   {udid}")
    with open(os.path.join(out_dir, "udid.txt"), "w", encoding="utf-8") as handle:
        handle.write(udid)

    run(["xcrun", "simctl", "boot", udid], check=False)
    run(["xcrun", "simctl", "bootstatus", udid, "-b"], check=False)
    run(["xcrun", "simctl", "install", udid, app_path])

    plist = os.path.join(app_path, "Info.plist")
    bundle_id = run(["plutil", "-extract", "CFBundleIdentifier", "raw", plist]).stdout.strip()
    print(f"Bundle: {bundle_id}")

    launched = run(["xcrun", "simctl", "launch", udid, bundle_id], check=False)
    print(launched.stdout.strip() or launched.stderr.strip())

    time.sleep(WAIT_LAUNCH)

    shot = os.path.join(out_dir, "sim-01.png")
    run(["xcrun", "simctl", "io", udid, "screenshot", shot], check=False)
    print(f"截图:   {shot}")

    alive = run(["xcrun", "simctl", "spawn", udid, "launchctl", "list"], check=False).stdout
    running = bundle_id in alive
    print(f"进程存活: {running}")

    logs = run(
        ["xcrun", "simctl", "spawn", udid, "log", "show", "--last", "3m", "--style", "compact",
         "--predicate", f'process == "{bundle_id.split(".")[-1]}"'],
        check=False,
    ).stdout
    with open(os.path.join(out_dir, "app.log"), "w", encoding="utf-8") as handle:
        handle.write(logs or "(无日志)")

    with open(os.path.join(out_dir, "status.txt"), "w", encoding="utf-8") as handle:
        handle.write(
            f"runtime={runtime['name']}\n"
            f"device={device_type['name']}\n"
            f"udid={udid}\n"
            f"bundle={bundle_id}\n"
            f"running={running}\n"
        )

    if not running:
        print("!! 应用没有保持运行，去看 app.log")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
