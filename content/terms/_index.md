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

## 文件与持久化

### FS

文件系统（File System，FS）：约定文件名、逻辑长度、数据位置及访问规则，并把相关元数据保存到存储介质的组织方式。块设备能读写扇区，不代表已经有文件系统。

背景：[Wikipedia：File system](https://en.wikipedia.org/wiki/File_system)。本系列具体磁盘格式以各课固定版本的格式说明为准。

### EOF

文件结束位置（End of File，EOF）。本课读取接口以逻辑长度为边界；当前游标到达末尾时读取返回零字节。EOF 不是存进文件的一个特殊字符，也不等于文件预留物理区段的末尾。

背景：[Wikipedia：End-of-file](https://en.wikipedia.org/wiki/End-of-file)。

### handle

句柄（handle）：内核交给调用者、用来引用一条打开记录的标识。文件目录记录文件本身，打开记录还包含游标、权限和所有者等访问状态；同一文件和一次打开不是同一个概念。具体编码与失效规则属于本课接口，不默认等同于 POSIX 文件描述符。

背景：[Wikipedia：Handle](https://en.wikipedia.org/wiki/Handle_(computing))。

### extent

连续区段（extent）：分配给文件的一段连续存储空间。第 10 课的最小文件系统用固定大小区段降低实现复杂度；预留容量与逻辑文件长度不同，固定区段也会限制增长和空间利用率。

背景：[Wikipedia：Extent](https://en.wikipedia.org/wiki/Extent_(file_systems))。

### B+ 树 {#bplus-tree}

B-plus tree（B+ 树）：以较大扇出缩短查找路径的一类有序树；文件记录放在叶子，内部页保存分隔键与孩子位置，叶子后继支持顺序枚举。本课把它用作平面文件名索引，不等于实现目录层级，也不等于直接使用数据库的并发或恢复协议。

背景：[Wikipedia：B+ tree](https://en.wikipedia.org/wiki/B%2B_tree)；实现参考：[PostgreSQL 的 B-Tree Structure](https://www.postgresql.org/docs/17/btree.html#BTREE-STRUCTURE)。本系列的磁盘格式由各课独立定义。

### bitmap

位图（bitmap）：用每一位记录某个编号资源是否分配。节点位图与数据位图可以管理不同大小、不同编号空间的资源，不能仅凭位图下标直接推断设备扇区位置。格式校验还要核对位图与真实引用关系，而不只是数出有多少位为一。

背景：[Wikipedia：Bit array](https://en.wikipedia.org/wiki/Bit_array)。

### block chain {#block-chain}

数据块链（block chain）：文件记录指向首个块，各块再记录下一个块的编号，直到链尾标记。这里是文件内容的组织方式，不是区块链系统；记录链指针的空间不能再算作用户有效载荷。合法编号仍可能形成环或被两个文件共享，需要单独检查。

背景：[Wikipedia：File allocation table](https://en.wikipedia.org/wiki/File_Allocation_Table)介绍了另一种用链接组织文件块的方式；第 11 课把 next 存在哪里、链尾如何表示，以该课格式说明为准。

### defrag

空间整理（defragmentation，常简称 defrag）：搬动仍在使用的数据，使空闲或占用分布更连续。移动字节以后还要改引用位置、块链和分配记录；整理前后内容应相同。数据区整理不自动意味着目录树合并、元数据压缩、性能提升或崩溃原子性。

背景：[Wikipedia：Defragmentation](https://en.wikipedia.org/wiki/Defragmentation)。

### DMA

直接内存访问（Direct Memory Access，DMA）：设备通过约定的内存地址读写缓冲区，不由 CPU 一字节一字节代为搬运。本系列 virtio 描述符记录 guest 物理地址；地址有效期、访问方向、内存顺序和完成后再复用都属于驱动合同。QEMU 中能工作不等于真机缓存一致性、IOMMU 和总线约束已经处理。

背景：[Wikipedia：Direct memory access](https://en.wikipedia.org/wiki/Direct_memory_access)。

### FLUSH

刷新设备写缓存的操作，flush 是普通英文词而非缩写。本课的 `VIRTIO_BLK_T_FLUSH` 是真实块请求，需要协商相应特性并核对完成状态；处理器内存屏障不是设备刷新请求。一次刷新完成不自动使多个扇区的文件更新具有事务原子性。

规范：[VirtIO 1.2 的块设备与写缓存语义](https://docs.oasis-open.org/virtio/virtio/v1.2/virtio-v1.2.html)。

### journal

恢复日志（journal）：保存恢复依据的结构，不是面向读者的运行日志。redo journal 保存足以安装已提交结果的信息；恢复是否重放、何时可以复用日志，取决于明确的提交记录、刷新顺序和格式验证。数据日志与仅元数据日志的保护范围不同。

背景：[Wikipedia：Journaling file system](https://en.wikipedia.org/wiki/Journaling_file_system)；机制参考：[Linux 内核 ext4 journal 文档](https://docs.kernel.org/filesystems/ext4/journal.html)。本系列自行定义格式，不承诺兼容 ext4。

### WAL

预写日志（Write-Ahead Logging，WAL）：依赖日志恢复的正式数据修改，必须在相应日志恢复依据已经持久化以后，才允许覆盖正式位置。具体提交标记、设备缓存合同和事务边界由实现定义；不是一种通用可互换的磁盘格式。

参考：[PostgreSQL 17：Write-Ahead Logging](https://www.postgresql.org/docs/17/wal-intro.html)。

### after-image {#after-image}

修改后镜像（after-image）：记录某个目标块或扇区修改后应有的完整字节。本系列 redo journal 重放安装这份目标状态，不是重新执行一次追加操作；重复安装同一份镜像不会把同一内容追加两遍。

相关机制见 [xv6 日志实现](https://github.com/mit-pdos/xv6-riscv/blob/e93dabeb98431235c6e1a101cb96c73c923fdbc4/kernel/log.c)；具体粒度与校验规则以本课格式为准。

### checkpoint

检查点安装（checkpoint）：本课日志语境中，把已提交的修改后镜像安装到正式位置，并在确认正式位置持久化之后，清理和复用日志。它不是保存一份内存快照，也不意味着任意位置停止执行都能忽略设备刷新顺序。

相关机制见 [Linux 内核 ext4 journal 文档](https://docs.kernel.org/filesystems/ext4/journal.html)。

### idempotence {#idempotence}

幂等（idempotence）：一次或多次执行同一操作，最终具有相同的目标效果。本课恢复重复安装相同扇区镜像，不会重复增加逻辑文件长度；它不意味着第二次可以不校验，也不意味着没有设备错误。

背景：[Wikipedia：Idempotence](https://en.wikipedia.org/wiki/Idempotence)。

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

### PIC {#pic}

位置无关代码（Position-Independent Code，PIC）：内部引用按约定编译，使代码不必依赖唯一的安装地址。不能把所有 PIC 都当成可以直接复制运行的字节；常见动态链接还需要地址表和重定位支持。本系列第 13 课把范围收窄为不需要运行时外部地址修补的有界平面模块，并用不同安装地址实际执行来补充构建检查。

参考：[GCC Code Generation Options](https://gcc.gnu.org/onlinedocs/gcc/Code-Gen-Options.html)。

### DLL {#dll}

动态链接库（Dynamic-Link Library，DLL）：程序可以通过动态装载机制取得其导出函数的库。这个名称常见于 Windows；本系列的 `math.dll` 只借用文件名，用的是自定义模块容器，不是 Windows 动态库兼容性声明，也不意味着有了通用 ELF 动态链接器。

背景：[Microsoft：About Dynamic-Link Libraries](https://learn.microsoft.com/en-us/windows/win32/dlls/about-dynamic-link-libraries)。

### relocation {#relocation}

重定位（relocation）：工具链或加载器根据地址布局修补代码或数据中的引用。链接时重定位与运行时重定位不是同一阶段；没有未解析外部符号，也不自动证明一个平面映像能在所有位置正确执行。本系列的有界模块通过构建检查和实际换址执行共同验证自己的位置无关合同。

参考：[RISC-V ELF psABI](https://riscv-non-isa.github.io/riscv-elf-psabi-doc/)。

### `gp`

RISC-V 整数寄存器的惯用名称：`gp` 是 global pointer（全局指针）。若编译结果使用 small-data 访问，启动代码必须按链接布局初始化它。

参考：[RISC-V ELF psABI](https://github.com/riscv-non-isa/riscv-elf-psabi-doc/blob/master/riscv-cc.adoc)。

### `sp`

Stack pointer（栈指针）。RISC-V C ABI 要求它满足栈对齐约定；栈通常从高地址向低地址增长。

参考：[RISC-V ELF psABI](https://github.com/riscv-non-isa/riscv-elf-psabi-doc/blob/master/riscv-cc.adoc)。

### BSS

BSS 是可执行文件中存放零初始化/未显式初始化数据的一类区域，通常不需要把整段零字节写进文件；加载器或启动代码要保证运行时内存为零。历史名称常展开为 “Block Started by Symbol”，但读代码时更重要的是它的内存语义。

背景：[Wikipedia：.bss](https://en.wikipedia.org/wiki/.bss)；初始化示例见 [GNU ld 文档](https://sourceware.org/binutils/docs/ld/Output-Section-LMA.html)。

## 编译器与源码输入

### AST {#ast}

抽象语法树（Abstract Syntax Tree，AST）：用节点及其组合关系表达源码的语法结构，而不是保留字符的平铺顺序。例如加法的右侧可以是一整棵乘法表达式，后续名称检查、类型检查和代码生成再依据这种结构工作。它是一种表示方式，不意味着编译器必须使用某个外部框架，也不等同于运行时解释源码。

参考：[LLVM 官方教程：Parser and AST](https://llvm.org/docs/tutorial/MyFirstLanguageFrontend/LangImpl02.html)。

### self-hosting {#self-hosting}

编译器自举（self-hosting）：编译器能够处理自身实现所用的语言，并实际参与构建它自己。在宿主机上交叉构建一个编译器，再让它在 guest 里编译其他程序，只证明编译过程已经能在 guest 运行；若还不能编译自身实现，就不能据此宣称完成自举。

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

### scheduler

Scheduler（调度器）：根据任务状态和调度策略，决定接下来在哪个执行资源上运行哪个任务。可运行、正在运行、睡眠、已退出但未回收是不同状态；一次中断并不必然导致切换任务。

背景：[Wikipedia：Scheduling](https://en.wikipedia.org/wiki/Scheduling_(computing))。

### PID

Process Identifier（PID，进程标识）：用于引用一个具体进程实例的标识。它不一定等于进程表下标，更不等于 hart 编号。槽位复用时还需要防止旧标识误指向新实例；具体编码由本课程接口定义。

背景：[Wikipedia：Process identifier](https://en.wikipedia.org/wiki/Process_identifier)。

### hart

Hardware thread（硬件线程，hart）：RISC-V 架构中的独立指令执行线程，拥有自己的寄存器和特权状态。它是任务使用的执行资源，不是进程槽，也不保证与实体芯片的物理核心一一对应。

参考：[RISC-V 非特权架构导论](https://docs.riscv.org/reference/isa/v20260120/unpriv/intro.html)。

### spinlock

Spinlock（自旋锁）：通过原子操作竞争、等待时反复检查的一类锁。它适合短临界区；持锁等待串口输入或睡眠会妨碍其他执行者推进。互斥与内存发布顺序都需要明确约定，`volatile` 本身不能替代它们。

背景：[Wikipedia：Spinlock](https://en.wikipedia.org/wiki/Spinlock)。

### SMP

Symmetric Multiprocessing（SMP，对称多处理）：多个处理器执行资源在共享内存环境中由同一操作系统管理的组织方式。具备多个 hart，不等于已经实现负载均衡、任务迁移或可扩展的调度器。

背景：[Wikipedia：Symmetric multiprocessing](https://en.wikipedia.org/wiki/Symmetric_multiprocessing)。

### TCG

Tiny Code Generator（TCG，微型代码生成器）：QEMU 的动态代码翻译后端。多线程 TCG 可让多个虚拟 CPU 使用不同的主机执行线程；这仍是仿真执行，不是被仿真芯片的真实硬件吞吐。

参考：[QEMU：Multi-threaded TCG](https://www.qemu.org/docs/master/devel/multi-thread-tcg.html)。

### MSIP

Machine Software Interrupt Pending（MSIP，机器软件中断挂起位）：RISC-V 机器软件中断的挂起状态，对应的内存映射寄存器可以用于跨 hart 通知。课程中的具体寄存器地址属于 QEMU virt 平台；把它作为轮询启动握手，不等于已经实现核间中断处理服务。

规范：[RISC-V Machine-Level ISA](https://docs.riscv.org/reference/isa/v20260120/priv/machine.html)。

### WFI

Wait for Interrupt（WFI，等待中断指令）：允许处理器等待可处理事件的特权架构指令。软件不能把它当成绝不提前返回的保证，恢复后仍需要检查等待条件；是否实际省电取决于实现。

规范：[RISC-V Machine-Level ISA：Wait for Interrupt](https://docs.riscv.org/reference/isa/v20260120/priv/machine.html)。

### PLIC

Platform-Level Interrupt Controller（PLIC，平台级中断控制器）：将平台设备的外部中断请求按优先级、使能和目标上下文送往 hart。它的 claim/complete 流程与 Sstc 定时器的比较值更新不是同一条路径。

规范：[RISC-V PLIC 规范](https://github.com/riscv/riscv-plic-spec)。

### IRQ

Interrupt Request（IRQ，中断请求）：设备或中断源请求处理器处理事件的信号或编号。具体源编号、控制器路由与使能条件由平台决定，不能把某台虚拟机的编号当成整个指令集的常量。

背景：[Wikipedia：Interrupt request](https://en.wikipedia.org/wiki/Interrupt_request)。

### ring-buffer

Ring buffer（环形缓冲区）：在固定容量数组中让读写位置回绕的缓冲结构。它需要明确满/空条件、生产者与消费者的同步，以及容量耗尽后的行为；有限缓冲本身不是流控。

背景：[Wikipedia：Circular buffer](https://en.wikipedia.org/wiki/Circular_buffer)。

### DTB

Devicetree Blob（DTB，设备树二进制）：设备树数据的扁平二进制编码，常用于启动时向内核描述硬件。它记录某个平台的设备地址、中断连接和属性，不是 CPU 指令集对所有平台的统一地址约定。

规范：[Devicetree Specification：Flattened Devicetree Format](https://github.com/devicetree-org/devicetree-specification/blob/main/source/chapter5-flattened-format.rst)。

### FIFO

First In, First Out（FIFO，先进先出）：先写入的数据先取出的队列顺序。UART 的硬件接收 FIFO 与内核软件环形缓冲是不同层次，容量、溢出和可观察计数不能混为一谈。

背景：[Wikipedia：FIFO](https://en.wikipedia.org/wiki/FIFO_(computing_and_electronics))。

### DLAB

Divisor Latch Access Bit（DLAB，除数锁存访问位）：16550 串口线控制寄存器中的控制位，决定部分偏移访问普通收发/中断寄存器，还是波特率除数锁存器。课程初始化先清它，再访问接收数据和中断使能。

实现参考：[QEMU v10.2.1：serial.c](https://github.com/qemu/qemu/blob/v10.2.1/hw/char/serial.c)。

### ASCII

American Standard Code for Information Interchange（ASCII，美国信息交换标准代码）：常见的字符编码标准。本课 shell 只编辑可打印 ASCII 字节，不把这个最小编辑器描述为 Unicode 终端。

背景：[Wikipedia：ASCII](https://en.wikipedia.org/wiki/ASCII)。

### CRLF

Carriage Return / Line Feed（CR/LF，回车/换行）：两个不同的控制字符。CRLF 是它们连续出现的形式；逐字节读取时也应保持跨读取的状态，避免把一组 CRLF 当成两次命令提交。

背景：[Wikipedia：Newline](https://en.wikipedia.org/wiki/Newline)。

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
