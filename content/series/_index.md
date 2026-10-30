+++
title = "系列总览：从第一条指令到真实开发板"
description = "一张持续更新的路线图：从 RISC-V 裸机入口，经过 OS、文件系统和工具链，走到真实开发板。"
+++

本页是系列路线图。主线有 20 篇技术课程，另有一篇序篇 00。完成并发布的文章打勾；尚在计划中的内容不代表已经实现或验证。

☑ 已完成并发布　　☐ 计划中

## 序篇：为什么开始

- ☑ [00. 为什么要重新学一次操作系统：把概念变成能运行的东西](/posts/why-this-series/)

## 第一部分：让 CPU 执行我们的第一段代码

- ☑ [01. 一条命令背后：搭建可复现的 RISC-V 实验环境](/posts/environment-and-first-entry/)
- ☑ [02. 没有 main 之前：启动汇编、C 运行环境与串口（Universal Asynchronous Receiver-Transmitter，UART）Hello World](/posts/c-runtime-uart-hello/)
- ☑ [03. 内核不必由模拟器直接装好：从 Virtual I/O Device（VIRTIO）磁盘加载 kernel 和 shell](/posts/virtio-bootloader-from-disk/)

## 第二部分：从裸机程序长成一个小内核

- ☑ [04. 从 M-mode 到 S-mode，再到 U-mode：让一次异常证明权限边界](/posts/machine-supervisor-user-traps/)
- ☑ [05. 给应用一套最小接口：syscall、mini-libc 与 heap](/posts/syscall-mini-libc-heap/)
- ☑ [06. 程序被打断以后：中断、保存现场与原路返回](/posts/interrupt-save-restore-resume/)
- ☑ [07. 让多个程序交替前进：定时器、上下文切换与进程生命周期](/posts/timer-scheduler-process-lifecycle/)
- ☑ [08. 第二个 hart：并行、共享状态与锁](/posts/second-hart-shared-state-locks/)
- ☑ [09. 从轮询终端到交互式 shell](/posts/uart-interrupt-interactive-shell/)

## 第三部分：让程序和数据在重启之后留下来

- ☑ [10. 块设备到最小文件系统：先把数据放对位置](/posts/block-device-minimal-filesystem/)
- ☑ [11. 文件变多、内容变长：独立实现 B+ 树文件系统](/posts/bplus-tree-filesystem/)
- ☑ [12. 写到一半就重启：给 B+FS 加 redo journal](/posts/redo-journal-crash-recovery/)

## 第四部分：让系统自己生成和加载程序

- ☑ [13. 文件里的字节怎样成为程序：加载器与动态 math.dll](/posts/program-loader-dynamic-math-module/)
- ☑ [14. 在 console 粘贴源码，再在 OS 里编译它](/posts/guest-source-paste-native-compiler/)
- ☑ [15. 把工具链闭环接完整：浮点、运行时与动态调用](/posts/soft-float-runtime-dynamic-toolchain/)

## 第五部分：离开 QEMU，点亮真实开发板

- ☐ 16. 选板先看启动条件：制定一份移植合同
- ☐ 17. 第一次真机执行：自己的串口输出与 LED
- ☐ 18. 真正把内核运行起来：定时器、中断、用户态与 shell
- ☐ 19. 从镜像到真实介质：存储驱动、B+FS 与 journal
- ☐ 20. 终章：在自己的开发板上编译并运行 demo.c

## 这套路线怎么学

每篇都围绕一个问题、一段可以观察到的结果和一套可复现验收展开。代码仓库按课程标签固定状态，文章记录环境、命令、输出和本课范围。[QEMU（Quick Emulator，快速仿真器）](/terms/#qemu)通过只证明当前虚拟平台配置通过，不等于[操作系统（Operating System，OS）](/terms/#os)已移植，也不替代真实硬件验收；系列会把模拟器 bring-up、OS 服务和真机验收分开说明。

我把这当作[人工智能（Artificial Intelligence，AI）](/terms/#ai)辅助的费曼学习法：让 agent 协助拆小问题、实现和解释；我再检查代码与 diff，预测测试结果，实际运行，并尝试用自己的话讲清楚控制流和数据布局。AI 的回答不是验收标准，能复现、能解释、测试证据对得上，才算学会。

- [阅读序篇：为什么要重新学一次操作系统](/posts/why-this-series/)
- [查术语：RISC-V、OS 与裸机实验](/terms/)
- [查看代码仓库](https://github.com/xueliangliang/riscv-hello)
