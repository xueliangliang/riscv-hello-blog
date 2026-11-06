+++
title = "RISC-V OS实验笔记"
series_id = "riscv-os"
description = "一张持续更新的路线图：从 RISC-V 裸机入口，经过 OS、文件系统和工具链，走到真实开发板。"
+++

本页是系列路线图。主线有 20 篇技术课程，另有一篇序篇 00。完成并发布的文章打勾；尚在计划中的内容不代表已经实现或验证。

☑ 已上线并核验　　☐ 计划中或待上线确认

## 序篇：为什么开始

{{< series-part id="prologue" >}}

## 第一部分：让 CPU 执行我们的第一段代码

{{< series-part id="entry" >}}

## 第二部分：从裸机程序长成一个小内核

{{< series-part id="kernel" >}}

## 第三部分：让程序和数据在重启之后留下来

{{< series-part id="storage" >}}

## 第四部分：让系统自己生成和加载程序

{{< series-part id="toolchain" >}}

## 第五部分：离开 QEMU，点亮真实开发板

{{< series-part id="hardware" >}}

## 这套路线怎么学

每篇都围绕一个问题、一段可以观察到的结果和一套可复现验收展开。代码仓库按课程标签固定状态，文章记录环境、命令、输出和本课范围。[QEMU（Quick Emulator，快速仿真器）](/terms/#qemu)通过只证明当前虚拟平台配置通过，不等于[操作系统（Operating System，OS）](/terms/#os)已移植，也不替代真实硬件验收；系列会把模拟器 bring-up、OS 服务和真机验收分开说明。

我把这当作[人工智能（Artificial Intelligence，AI）](/terms/#ai)辅助的费曼学习法：让 agent 协助拆小问题、实现和解释；我再检查代码与 diff，预测测试结果，实际运行，并尝试用自己的话讲清楚控制流和数据布局。AI 的回答不是验收标准，能复现、能解释、测试证据对得上，才算学会。

- [阅读序篇：为什么要重新学一次操作系统](/posts/why-this-series/)
- [查术语：RISC-V、OS 与裸机实验](/terms/)
