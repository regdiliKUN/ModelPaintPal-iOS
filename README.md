# ModelPaintPal · iOS

模型漆调色助手的 iOS 端，目标是在 App Store 上架。

桌面版（[ModelPaintPal](https://github.com/regdiliKUN/ModelPaintPal)）和安卓版
（[ModelPaintPal-APK](https://github.com/regdiliKUN/ModelPaintPal-APK)）已经在跑，
这个仓库只做 iPhone / iPad 这一份。

## 现在处于什么阶段

**探针阶段。** 还没有开始移植业务代码——先验证一件不确定的事：

> kivy-ios 能不能在 Xcode 26 / iOS 26 SDK 下编出可安装、可启动的 Kivy 应用？

这件事必须先验证，因为 2026-04-28 起 App Store 只收 Xcode 26 + iOS 26 SDK 构建的包，
而 Kivy 稳定版仍是 2.3.1（2024 年 12 月），kivy-ios 正在往 Kivy 3 / SDL3 迁移，
官方里程碑排在 2027 年初。**没有现成案例能证明这条链现在通不通。**

如果通，就按「复用现有 Python 代码」推进；如果不通，就得早一点决定是等 Kivy 3
还是改写成原生 SwiftUI——这个决定比写多少行代码重要得多。

## 探针在验什么

`probe/main.py` 是一个没有业务代码的纯自检界面，屏幕上直接打印答案：

| 检查项 | 为什么是它 |
|---|---|
| Kivy / Python 版本 | 工具链真的把解释器和框架编进去了 |
| Pillow 版本 + 实际取样 | 取色功能的命根子，必须真打开图片取值，不能只 import |
| 窗口尺寸 / dpi / 密度 | 后面所有布局都靠这三个数换算 |
| 存储可读写 + 路径 | iOS 沙盒里能落到哪个可写目录 |
| 中文字体 | 自带 NotoSansSC，不指望系统字体回退 |
| 触摸 pos 与 sx·sy | Android 端「点左边、取右边」栽过三次，iOS 必须先验坐标系 |
| 计时器每秒跳动 | 事件循环真的在跑，不是开机卡一帧 |

模拟器截图会随 artifact 一起上传，那张图就是结论。

## 怎么跑

工作流是 `.github/workflows/probe.yml`，在 `macos-26` 机器上跑（自带 Xcode 26，
公共仓库不消耗额度）。手动触发或推 `probe/` 下的改动都会跑一次：

```bash
gh workflow run probe.yml
gh run watch
```

跑完去 artifact `probe-run-<编号>` 里拿 `sim-01.png`。

## 目录

```
probe/                  探针应用（会被 toolchain create 打包）
  main.py               自检界面
  assets/fonts/         思源黑体，中文显示用
.github/workflows/      探针 CI
.github/scripts/        模拟器取证脚本
```

移植开始后这里会长出 `mobile/`（共享界面层）、`app/`（从桌面仓库同步的核心层）、
`ios/`（平台适配层），结构和安卓仓库保持一致。

## 已知的硬门槛（不是代码问题）

1. **Apple Developer Program**：个人 ¥688/年，实名 + 双币信用卡。没有它无法上架，
   也无法用 TestFlight。
2. **中国区上架要 App 备案号**：只要应用有一次联网行为就必须有，否则国区上不了。
   本项目的「联网核实颜料信息」正好踩线，需要单独办备案（域名 + 大陆服务器 +
   管局审核 7~20 个工作日）。
3. **没有 Mac 也能做**，但所有构建只能在云端 macOS 上跑，一轮迭代按分钟计。

## 许可

与桌面版一致，见 [LICENSE](https://github.com/regdiliKUN/ModelPaintPal/blob/main/LICENSE)。
