+++
title = "术语索引：RISC-V、OS 与裸机实验"
description = "系列文章里常见缩写、英文全称和简明解释；首次出现时按本索引标注，标准行为优先链接官方规范。"
+++

本页集中解释系列中反复出现的缩写和术语。文章第一次用到重要缩写时，会写出英文全称和中文意思，并链接到这里；不用为每个寄存器名或命令行参数造词条。

Wikipedia 链接作为入门背景阅读；涉及 ABI、指令语义、ELF 装载或设备协议时，以对应的官方规范和工具文档为准。

## 学习路线与内存

### OS

操作系统（Operating System，OS）：管理进程、内存、设备和持久数据的一组软件机制。本系列讲的是逐步搭起一个教学系统，不以实现完整 Unix 用户态接口或替代 Linux 为目标。

背景：[Wikipedia：Operating system](https://en.wikipedia.org/wiki/Operating_system)

### AI

人工智能（Artificial Intelligence，AI）。本文里的“AI 辅助费曼式学习”指让 agent 帮忙解释和实现，再由学习者审查、预测测试结果、亲自运行并复述；模型输出本身不是验证证据。

背景：[Wikipedia：Artificial intelligence](https://en.wikipedia.org/wiki/Artificial_intelligence)

### RAM

随机存取存储器（Random-Access Memory，RAM）。文章中的加载地址表示 guest 可访问的内存地址，不等于磁盘上的逻辑块编号。

背景：[Wikipedia：Random-access memory](https://en.wikipedia.org/wiki/Random-access_memory)

### CPU

中央处理器（Central Processing Unit，CPU）：执行指令并协调计算机其他部件的处理器。

背景：[Wikipedia：Central processing unit](https://en.wikipedia.org/wiki/Central_processing_unit)

### ROM

只读存储器（Read-Only Memory，ROM）。本系列提到模拟器的 reset ROM 时，指虚拟平台提供的启动代码，不代表这篇课程实现了板级固件。

背景：[Wikipedia：Read-only memory](https://en.wikipedia.org/wiki/Read-only_memory)

### DRAM

动态随机存取存储器（Dynamic Random-Access Memory，DRAM）。本系列 `virt` guest 的 DRAM 地址范围由虚拟平台定义。

背景：[Wikipedia：Dynamic random-access memory](https://en.wikipedia.org/wiki/Dynamic_random-access_memory)

### PC

程序计数器（Program Counter，PC）：保存处理器当前执行位置相关地址的寄存器。调试器显示的 PC 用于确认控制流跳到了哪里。

背景：[Wikipedia：Program counter](https://en.wikipedia.org/wiki/Program_counter)

### LBA

逻辑块寻址（Logical Block Addressing，LBA）：用从零开始的逻辑块编号定位块设备上的数据。本课的磁盘镜像以 512 字节扇区编号；例如 LBA 0 是启动记录，kernel 从 LBA 1 开始。

背景：[Wikipedia：Logical block addressing](https://en.wikipedia.org/wiki/Logical_block_addressing)；virtio 设备请求的具体协议见 [VirtIO 规范](https://docs.oasis-open.org/virtio/virtio/v1.2/virtio-v1.2.html)。

## 可执行文件与调用约定

### ELF

可执行与可链接格式（Executable and Linkable Format，ELF）：包含目标架构、入口、节和程序段等信息的文件格式。模拟器的 `-kernel` 和本文的 bootloader 承担的装载职责不同，不能把 ELF 文件与 raw binary 混为一谈。

背景：[Wikipedia：Executable and Linkable Format](https://en.wikipedia.org/wiki/Executable_and_Linkable_Format)；格式细节见 [System V ELF ABI](https://gabi.xinuos.com/elf/)。

### PT_LOAD

ELF 程序头中的可装载段类型。`p_filesz` 描述文件里有多少字节，`p_memsz` 描述装载后占用多少内存；两者不同的部分常用于 [BSS](/terms/#bss)/零填充。

规范：[ELF Program Header](https://gabi.xinuos.com/elf/08-pheader.html)。

### ISA

指令集架构（Instruction Set Architecture，ISA）：软件可见的指令、寄存器和行为约定。`rv64imac_zicsr_zifencei` 是本系列实验使用的一组 RISC-V ISA 扩展。

背景：[Wikipedia：Instruction set architecture](https://en.wikipedia.org/wiki/Instruction_set_architecture)。

### ABI

应用二进制接口（Application Binary Interface，ABI）：规定编译后的函数如何传递参数、使用寄存器、布置栈以及交接控制。RISC-V 的 `lp64` 是一种 ABI 配置，不是 ISA 名称。

背景：[Wikipedia：Application binary interface](https://en.wikipedia.org/wiki/Application_binary_interface)；RISC-V 约定见 [RISC-V ELF psABI](https://github.com/riscv-non-isa/riscv-elf-psabi-doc/blob/master/riscv-cc.adoc)。

### `gp`

RISC-V 整数寄存器的惯用名称：`gp` 是 global pointer（全局指针）。若编译结果使用 small-data 访问，启动代码必须按链接布局初始化它。

参考：[RISC-V ELF psABI](https://github.com/riscv-non-isa/riscv-elf-psabi-doc/blob/master/riscv-cc.adoc)。

### `sp`

Stack pointer（栈指针）。RISC-V C ABI 要求它满足栈对齐约定；栈通常从高地址向低地址增长。

参考：[RISC-V ELF psABI](https://github.com/riscv-non-isa/riscv-elf-psabi-doc/blob/master/riscv-cc.adoc)。

### BSS

BSS 是可执行文件中存放零初始化/未显式初始化数据的一类区域，通常不需要把整段零字节写进文件；加载器或启动代码要保证运行时内存为零。历史名称常展开为 “Block Started by Symbol”，但读代码时更重要的是它的内存语义。

背景：[Wikipedia：.bss](https://en.wikipedia.org/wiki/.bss)；初始化示例见 [GNU ld 文档](https://sourceware.org/binutils/docs/ld/Output-Section-LMA.html)。

## 权限、设备与调试

### CSR

Control and Status Register（CSR，控制与状态寄存器）：RISC-V 中用于读取状态和控制处理器行为的一类寄存器。访问所需的最低特权级由寄存器编码与架构规则决定；低权限访问受限寄存器会触发异常。它不是普通 RAM 变量。

规范：[RISC-V CSR 地址与访问权限](https://docs.riscv.org/reference/isa/v20260120/priv/priv-csrs.html)。

### trap

Trap（陷入/异常入口）：执行过程中因异常或中断转入处理入口的过程。本系列第 04、05 课先处理同步异常：`ecall` 和非法指令。硬件记录原因、地址和来源状态，软件负责保存通用寄存器、安排处理栈和恢复现场。

规范：[RISC-V Supervisor-Level ISA](https://docs.riscv.org/reference/isa/v20260120/priv/supervisor.html)。

### syscall

System call（syscall，系统调用）：用户程序请求内核服务的受控入口。RISC-V 的 `ecall` 提供产生环境调用异常的指令，具体请求编号、参数和返回值由系统调用 ABI 另行定义，不能只看到 `ecall` 就认为与 Linux 兼容。

背景：[Wikipedia：System call](https://en.wikipedia.org/wiki/System_call)；本系列第 05 课的接口见代码仓库 `lessons/05/abi.h` 和该课 README。

### interrupt

Interrupt（中断）：相对于当前普通指令流异步发生的事件，在挂起、使能、委托与特权条件满足时进入处理入口。中断处理后可以恢复原程序，也可以在调度器决策后运行其他任务；两者不是同一概念。第 06 课先只演示恢复同一条程序流。

背景：[Wikipedia：Interrupt](https://en.wikipedia.org/wiki/Interrupt)；规范见 [RISC-V Supervisor-Level ISA](https://docs.riscv.org/reference/isa/v20260120/priv/supervisor.html)。

### Sstc

RISC-V Supervisor-mode Timer Interrupts 扩展，名称中的 Ss 表示监管者级扩展，tc 来自 timecmp。它允许监管者模式通过 `stimecmp` 管理定时器比较值；是否可访问，还取决于机器模式的授权。它不是外部设备中断控制器，也不是一个调度器。

规范：[RISC-V Sstc 1.0](https://docs.riscv.org/reference/isa/v20260120/priv/sstc.html)。

### heap

Heap（堆）：用于动态分配对象的一块内存。本系列第 05 课先做 bump allocator（顺序推进分配器），按对齐后的请求大小向前移动游标；容量固定、失败不消耗空间、不支持释放。它在用户态操作已预留内存，不是向内核申请新页的系统调用。

背景：[Wikipedia：Memory management](https://en.wikipedia.org/wiki/Memory_management)。

### M-mode

Machine mode（机器模式）是 RISC-V 的机器级特权模式。

### S-mode

Supervisor mode（监管者模式），RISC-V 常见的操作系统内核运行模式。

### U-mode

User mode（用户模式），用于运行受控的应用代码。仅切换到 U-mode 不自动提供内存隔离；实际隔离还依赖 [Physical Memory Protection（PMP，物理内存保护）](/terms/#pmp)、页表及其配置。

规范：[RISC-V Privileged Architecture](https://docs.riscv.org/reference/isa/priv/priv-intro.html)。

### PMP

Physical Memory Protection（PMP，物理内存保护）：RISC-V 特权架构用于限制 hart 对物理地址区域访问的机制。它不是页表，也不意味着配置完成后自然就形成了某种固定的隔离策略。

规范：[RISC-V Privileged Architecture](https://docs.riscv.org/reference/isa/priv/priv-intro.html)。

### UART

通用异步收发器（Universal Asynchronous Receiver-Transmitter，UART）：常见的串行通信硬件接口。本系列 `virt` 模型的 UART 地址和真实板卡的地址、时钟、pinmux 不能互换。

背景：[Wikipedia：Universal asynchronous receiver-transmitter](https://en.wikipedia.org/wiki/Universal_asynchronous_receiver-transmitter)。

### LSR

Line Status Register（线路状态寄存器）：UART 状态寄存器之一；本课轮询它以判断发送端是否可写。

### THR

Transmit Holding Register（发送保持寄存器）：UART 发送数据寄存器；本课向它写入下一个字符。

### MMIO

内存映射 I/O（Memory-Mapped I/O，MMIO）：把设备寄存器映射到处理器的地址空间，软件通过特定地址读写设备。具体地址和访问宽度由平台/设备约定，不是所有 RISC-V 机器通用的数值。

背景：[Wikipedia：Memory-mapped I/O and port-mapped I/O](https://en.wikipedia.org/wiki/Memory-mapped_I/O_and_port-mapped_I/O)。

### VirtIO

Virtual I/O Device（VIRTIO，虚拟 I/O 设备接口）：虚拟机与虚拟设备之间的标准化接口；virtio-mmio 是通过 MMIO 暴露其 transport 的一种方式。本文的 queue、feature 和 descriptor 细节按 [OASIS VirtIO 1.2](https://docs.oasis-open.org/virtio/virtio/v1.2/virtio-v1.2.html) 和对应 QEMU transport 文档核对。

### `fence.i`

RISC-V 指令取值同步指令。若代码字节刚被当作数据写入内存、随后要从该地址执行，需要按架构约定同步同一 hart 的后续指令取值；它不是通用内存写入完成的替代品。

规范：[RISC-V Zifencei 扩展](https://docs.riscv.org/reference/isa/unpriv/zifencei.html)。

### GDB

GNU 调试器（GNU Debugger，GDB）：可设置断点、检查寄存器和单步执行的调试器。`gdb-multiarch` 可连接 QEMU 的 RISC-V GDB stub。

背景：[Wikipedia：GNU Debugger](https://en.wikipedia.org/wiki/GNU_Debugger)。

### QEMU

Quick Emulator（QEMU）是开源机器模拟器与虚拟化工具。本系列使用 `qemu-system-riscv64` 的 `virt` 虚拟平台；在 QEMU 上通过不等于在实体板卡上通过。

背景：[Wikipedia：QEMU](https://en.wikipedia.org/wiki/QEMU)；项目术语见 [QEMU Glossary](https://www.qemu.org/docs/master/glossary.html)，平台资料见 [QEMU RISC-V `virt` 文档](https://www.qemu.org/docs/master/system/riscv/virt.html)。

## 构建与测试

### LTS

Long-Term Support（长期支持，LTS）：软件发行版采用的一类长期维护版本标记。本系列环境表中的 Ubuntu 版本号记录实际测试基线。

### GCC

GNU Compiler Collection（GCC）：GNU 项目提供的编译器集合；交叉 GCC 在主机上生成目标架构的程序。

背景：[Wikipedia：GNU Compiler Collection](https://en.wikipedia.org/wiki/GNU_Compiler_Collection)；项目文档见 [GCC 官网](https://gcc.gnu.org/)。

### CRC

Cyclic Redundancy Check（循环冗余校验，CRC）：为一段数据计算校验值，用于检测意外损坏；它不等同于密码学哈希或防篡改签名。

背景：[Wikipedia：Cyclic redundancy check](https://en.wikipedia.org/wiki/Cyclic_redundancy_check)。

### PTY

Pseudoterminal（伪终端，PTY）：一对由内核提供的伪设备端点，让终端程序和另一个进程进行双向通信；本系列提到 PTY 测试时，是指程序在伪终端环境下运行。

背景：[Wikipedia：Pseudoterminal](https://en.wikipedia.org/wiki/Pseudoterminal)；Linux 说明见 [`pty(7)`](https://man7.org/linux/man-pages/man7/pty.7.html)。
