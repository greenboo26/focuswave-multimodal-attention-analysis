"""
毫米波雷达采集模块
==================
60GHz FMCW 雷达 (RS6240, 2T4R) SPI 采集封装:
  - ~99 fps, 每帧 256 距离 bin × 8 通道, 距离分辨率 3.75 cm
  - 输出: .datacube.bin (PSIC 格式, 调试工具兼容)
         + npz 分块 (复数 IQ, 每 1000 帧一块)
         + 时间戳 CSV (帧号, 设备时间戳, 主机时间戳)
  - 双时间戳: 设备时间戳 + 主机 Python 时间戳 (跨设备对齐锚点)
  - 分块写入 + 定期 flush: 防止长时采集内存溢出/崩溃丢数据

用法:
    from core.mmwave_capture import MMWaveCapture

    mm = MMWaveCapture(subject_id='001', session='EXPERIMENT', save_root='./data')
    mm.connect()
    mm.start()
    # ... 实验期间 ...
    mm.stop()

依赖: pip install pythonnet numpy
设备: SPI 模式 (CH347 转接)
"""


import os
import time
import json
import queue
import threading
import struct
import ctypes
import numpy as np
from datetime import datetime, timezone

# ============================================================
# DLL 加载
# ============================================================

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DLL_DIR = os.path.join(ROOT_DIR, 'dll')
DLL_FILE = os.path.join(DLL_DIR, 'HifMsgDataCollectionLib.dll')

if not os.path.exists(DLL_FILE):
    raise FileNotFoundError(f"DLL file not found: {DLL_FILE}")

# 将 dll/ 加入 Windows DLL 搜索路径，让 P/Invoke 能找到 CH347DLLA64.dll
if os.path.isdir(DLL_DIR):
    os.add_dll_directory(DLL_DIR)

def _unblock_motw(path: str) -> None:
    """删除文件的 Zone.Identifier 数据流，解除 MOTW 阻止标记。

    参数:
        path: 目标文件的绝对路径
    返回: 无
    说明: 文件经网盘/IM 传输后会被标记为"来自互联网"，.NET 拒绝加载
          此类程序集（HRESULT 0x80131515）。标记不存在时静默忽略。
    """
    # Win32 API 直接删除备用数据流（ADS），失败（无标记/被锁定）时返回 False，不影响后续
    ctypes.windll.kernel32.DeleteFileW(f"{path}:Zone.Identifier")

# 解除 MOTW 标记后再加载，否则 .NET 拒绝加载经网盘/IM 传输的 DLL
_unblock_motw(DLL_FILE)

import clr
clr.AddReference(DLL_FILE)
from HifMsgDataCollectionLib import HifMsgDataCollectionApi


# ============================================================
# PSIC 文件头构建 (与 RadarDebugTool 输出格式一致)
# ============================================================

def _build_psic_header(range_fft=256, doppler_fft=32,
                       tx_ant=2, rx_ant=4, frame_period_ms=10,
                       start_freq_mhz=57_000, max_range_cm=947,
                       range_resol_mm=37, max_velocity_cm_s=400,
                       velocity_resol_mm_s=250, interval_us=57):
    """
    构建 PSIC 格式 32 字节全局文件头。

    字段顺序参考 RS6x_7x_RadarDebugTool_使用手册 表4-2。
    默认值对齐固件 prj_config.h: RS6240, ReportDataCube1D.

    Parameters
    ----------
    range_fft : int
        距离 FFT 点数 (默认 256)。需与固件实际配置一致。
    doppler_fft : int
        多普勒 FFT 点数 (默认 32)。
    tx_ant, rx_ant : int
        天线数 (默认 2T4R)。当前硬件固定为 2T4R。
    frame_period_ms : int
        帧周期毫秒数 (默认 10，即 100fps)。
    start_freq_mhz : int
        起始频率 MHz (默认 57000，即 57GHz, 固件 prj_config.h L65)。
    max_range_cm : int
        最大探测距离 cm (默认 947=9.5m, 256×37/10, 新固件 37mm)。
    range_resol_mm : int
        距离分辨率 mm (默认 37, 新固件编译值, 带宽=150000/37≈4.05GHz)。
    max_velocity_cm_s : int
        最大速度 cm/s (默认 400, doppler_fft/2 × vel_resol / 10)。
    velocity_resol_mm_s : int
        速度分辨率 mm/s (默认 250, 固件 prj_config.h L86)。
    interval_us : int
        Chirp 间隔 us (默认 57, SDK demo 默认)。
    """
    h = bytearray(32)

    # [0:4]   File Magic: "PSIC"
    h[0:4] = b'PSIC'

    # [4]     DataType: 0=FFT data
    h[4] = 0

    # [5]     FrameType: 1=1DFFT
    h[5] = 1

    # [6]     RxAntNum
    h[6] = rx_ant & 0xFF

    # [7]     TxAntNum
    h[7] = tx_ant & 0xFF

    # [8:10]  StartFreq (MHz), uint16 LE
    struct.pack_into('<H', h, 8, start_freq_mhz & 0xFFFF)

    # [10]    reserved
    h[10] = 0

    # [12:14] Range FFT Num, uint16 LE
    struct.pack_into('<H', h, 12, range_fft & 0xFFFF)

    # [14]    reserved
    h[14] = 0

    # [16:18] Doppler FFT Num, uint16 LE
    struct.pack_into('<H', h, 16, doppler_fft & 0xFFFF)

    # [18:20] reserved
    h[18:20] = b'\x00\x00'

    # [20:22] Max Range (cm), uint16 LE
    struct.pack_into('<H', h, 20, max_range_cm & 0xFFFF)

    # [22:24] Range Resol (mm), uint16 LE
    struct.pack_into('<H', h, 22, range_resol_mm & 0xFFFF)

    # [24:26] Max Velocity (cm/s), uint16 LE
    struct.pack_into('<H', h, 24, max_velocity_cm_s & 0xFFFF)

    # [26:28] Velocity Resol (mm/s), uint16 LE
    struct.pack_into('<H', h, 26, velocity_resol_mm_s & 0xFFFF)

    # [28:30] Interval Period (us), uint16 LE
    struct.pack_into('<H', h, 28, interval_us & 0xFFFF)

    # [30:32] Frame Period (ms), uint16 LE
    struct.pack_into('<H', h, 30, frame_period_ms & 0xFFFF)

    return bytes(h)


# ============================================================
# MMWaveCapture
# ============================================================

class MMWaveCapture:
    """
    毫米波雷达数据采集器 (v3, 按 EXPERIMENT 采集规范适配)

    输出文件 (保存在 {save_root}/sub-{id}_/mmwave/):
      sub-{id}_mmwave.datacube.bin   PSIC 格式, DebugTool 兼容
      sub-{id}_mmwave_datacube.npz   结构化复数 IQ (分析用)
      sub-{id}_mmwave_timestamps.csv  帧号,Unix毫秒时间戳(三列:帧号,DLL时间戳,Python时间戳)
      sub-{id}_mmwave.meta.json       采集元信息
    """

    DATA_TYPE_MAP = {
        0: 'psic_debug',
        1: 'string',
        2: 'datacube_0xC1',
        3: 'datacube_0xC2',
        4: 'point_cloud',
    }

    def __init__(self, subject_id, session='EXPERIMENT',
                 save_root='./data', port='COM5',
                 use_uart=False, spi_index=0, spi_freq_mode=0):
        """
        Parameters
        ----------
        subject_id : str
            被试编号 (如 '001')
        session : str
            Session 标签 (默认 'EXPERIMENT')
        save_root : str
            数据根目录, 自动生成子目录结构
        port : str
            串口号 (UART 模式, 默认 COM5)
        use_uart : bool
            False=SPI (默认), True=UART
        spi_index : int
            SPI 设备序号
        spi_freq_mode : int
            SPI 频率: 0=60MHz
        """
        self.subject_id = subject_id
        self.session = session
        self.save_root = save_root
        self.port = port
        self.use_uart = use_uart
        self.spi_index = spi_index
        self.spi_freq_mode = spi_freq_mode

        # 雷达参数 (与固件配置一致)
        self.range_fft = 256
        self.doppler_fft = 32
        self.tx_ant = 2
        self.rx_ant = 4

        # 内部状态
        self._api = None
        self._recording_flag = False
        self._running = False
        self._data_queue = queue.Queue(maxsize=5000)
        self._worker = None

        # 文件句柄
        self._bin_file = None       # .datacube.bin (PSIC)
        self._ts_file = None        # _timestamps.csv
        self._frame_cache = {}      # 累积 .npz 数据

        # flush 控制
        self._last_flush_time = time.time()
        self._flush_interval = 0.5  # 0.5 秒批量 flush

        # 分块 npz 控制
        self._frames_since_save = 0
        self._npz_save_interval = 1000   # 每 1000 帧写一次（~10 秒）
        self._npz_chunk_index = 0

        # 统计
        self.frame_count = 0
        self.byte_count = 0
        self.error_count = 0
        self._convert_error = 0   # DatacubeConversion 失败帧数(诊断丢数据用)
        self._start_time = None
        self._bin_path = None

    def __enter__(self):
        """支持 with 语句。"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出 with 块时自动停止并断开。"""
        try:
            self.stop()
        finally:
            self.disconnect()
        return False  # 不吞异常

    # ---------- 生命周期 ----------

    def connect(self):
        """初始化 DLL 并打开 SPI/UART 设备"""
        self._api = HifMsgDataCollectionApi()
        self._api.callback += self._on_data

        if self.use_uart:
            ok = self._api.OpenUartDevice(self.port, '921600')
        else:
            ok = self._api.OpenSpiDevice(self.spi_index, self.spi_freq_mode)

        if not ok:
            raise ConnectionError(
                f"打开设备失败: {'UART ' + self.port if self.use_uart else 'SPI'}")
        print(f"[mmWave] 连接成功 {'UART' if self.use_uart else 'SPI'} "
              f"lib={self._api.GetLibVersion()}")

    def disconnect(self):
        """关闭设备"""
        self._running = False
        if self._api:
            try:
                self._api.StopCollectingData()
            except Exception:
                pass
            try:
                if self.use_uart:
                    self._api.CloseUartDevice()
                else:
                    self._api.CloseSpiDevice(self.spi_index)
            except Exception:
                pass
            self._api.callback -= self._on_data
        self._api = None

        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=3)

        self._close_files()

    def _close_files(self):
        """关闭 bin 和 csv 文件句柄（先 flush 确保落盘）。"""
        for f in [self._bin_file, self._ts_file]:
            if f:
                try:
                    f.flush()       # 先确保落盘
                    f.close()
                except Exception:
                    pass
        self._bin_file = None
        self._ts_file = None

    # ---------- 数据回调 ----------

    def _on_data(self, sender, receive_data):
        """DLL 回调 (后台线程), 仅入队不阻塞"""
        try:
            self._data_queue.put_nowait(receive_data)
        except queue.Full:
            self.error_count += 1

    # ---------- 后台处理 ----------

    def _get_payload(self, receive_data):
        """从 DLL 回调数据中提取 payload 字节。兼容两种属性名。"""
        if hasattr(receive_data, 'payloadData') and receive_data.payloadData is not None:
            return receive_data.payloadData
        return receive_data.pointCloudRawDataOrStringData

    def _dotnet_ts_to_unix_ms(self, receive_data):
        """
        将 DLL 回调中的 .NET DateTime 转为 Unix 毫秒时间戳。
        .NET DateTime 无时区信息，值为本地时间（北京时间 UTC+8），
        转为 naive datetime 后用 .timestamp() 自动处理时区转换。
        """
        ts = receive_data.timeStamp
        if ts is None:
            return int(time.time() * 1000)
        # 兼容两种类型: 字符串 "2026-07-20-21:28:03.566" 或 .NET DateTime
        if hasattr(ts, 'Year'):
            # .NET DateTime → 本地时间 naive datetime → Unix ms
            dt = datetime(ts.Year, ts.Month, ts.Day,
                          ts.Hour, ts.Minute, ts.Second,
                          ts.Millisecond * 1000)
            return int(dt.timestamp() * 1000)
        else:
            # 字符串格式 "2026-07-20-21:28:03.566"
            try:
                s = str(ts)
                # 预期格式: "2026-07-20-21:28:03.566"
                dt = datetime.strptime(s, '%Y-%m-%d-%H:%M:%S.%f')
                return int(dt.timestamp() * 1000)
            except Exception:
                return int(time.time() * 1000)

    def _process_datacube(self, receive_data):
        """处理 dataType=3 (0xC2 DataCube)"""
        payload = self._get_payload(receive_data)
        if payload is None:
            return

        raw_bytes = bytes(payload)
        frame_idx = int(receive_data.frameIndex)

        # 双时间戳：DLL 时间戳（硬件接收时刻）+ Python time.time()（跨设备对齐锚点）
        dll_ts_ms = self._dotnet_ts_to_unix_ms(receive_data)
        py_ts_ms = int(time.time() * 1000)

        # ---- 写入 .datacube.bin (PSIC 帧数据) ----
        if self._bin_file:
            self._bin_file.write(raw_bytes)

        # ---- 写入 _timestamps.csv（三列：帧号, DLL时间戳, Python time.time()）----
        if self._ts_file:
            self._ts_file.write(f"{frame_idx},{dll_ts_ms},{py_ts_ms}\n")

        # ---- 定期 flush（不每帧刷，减少时间戳抖动）----
        now = time.time()
        if now - self._last_flush_time >= self._flush_interval:
            if self._bin_file:
                self._bin_file.flush()
            if self._ts_file:
                self._ts_file.flush()
            self._last_flush_time = now

        # ---- 累积 .npz 数据 ----
        try:
            data_cube = self._api.DatacubeConversion(
                payload, frame_idx, len(raw_bytes))
        except Exception:
            self._convert_error += 1
            data_cube = None

        if data_cube and data_cube.antennaData:
            for ant in data_cube.antennaData:
                key = f'tx{ant.txAntId}_rx{ant.rxAntId}'
                if ant.real and ant.imag:
                    arr = np.array(list(ant.real)) + 1j * np.array(list(ant.imag))
                    if key not in self._frame_cache:
                        self._frame_cache[key] = []
                    self._frame_cache[key].append(arr)

        self.frame_count += 1
        self.byte_count += len(raw_bytes)

        # 每 N 帧写入一个分块 npz，清空内存
        self._frames_since_save += 1
        if self._frames_since_save >= self._npz_save_interval:
            self._flush_npz_chunk()

    def _flush_npz_chunk(self):
        """将当前累积的帧写入分块 npz 文件，然后清空内存缓存。

        若本分片无任何数据（DatacubeConversion 全失败），跳过写入，
        否则会产生 22 字节空 npz，导致分析端 np.stack 崩溃。
        """
        if not self._frame_cache:
            return
        # 第一块用原名（兼容现有分析流程），后续加序号
        base_path, ext = os.path.splitext(self._npz_path)
        if self._npz_chunk_index == 0:
            chunk_path = self._npz_path
        else:
            chunk_path = f'{base_path}_part{self._npz_chunk_index:03d}{ext}'

        save_dict = {}
        for key, frames in self._frame_cache.items():
            if frames:
                save_dict[key] = np.stack(frames, axis=0)
        if not save_dict:
            print(f"[mmWave]   警告: 本分片 {self._npz_chunk_index} 无数据"
                  f" (转换失败 {self._convert_error} 帧), 跳过写入空文件")
            self._frame_cache = {k: [] for k in self._frame_cache}
            self._frames_since_save = 0
            self._npz_chunk_index += 1
            return
        np.savez_compressed(chunk_path, **save_dict)

        # 清空内存缓存
        self._frame_cache = {k: [] for k in self._frame_cache}
        self._frames_since_save = 0
        self._npz_chunk_index += 1

    def _process_data_loop(self):
        """后台线程: 从队列取数据并分发"""
        first = True
        while self._running:
            try:
                data = self._data_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                dtype = int(data.dataType)
                if first:
                    tn = self.DATA_TYPE_MAP.get(dtype, f'unknown({dtype})')
                    print(f"[mmWave] 首帧 dataType={dtype}({tn})")
                    first = False

                if dtype == 3:   # datacube_0xC2 (ReportDataCube1D)
                    if self._recording_flag:
                        self._process_datacube(data)

            except Exception:
                self.error_count += 1
            finally:
                self._data_queue.task_done()

    # ---------- 采集控制 ----------

    def start(self):
        """
        开始采集。

        自动创建目录结构: {save_root}/sub-{id}_/mmwave/
        输出:
          sub-{id}_mmwave.datacube.bin
          sub-{id}_mmwave_timestamps.csv
          sub-{id}_mmwave_datacube.npz  (分块写入, ~10s/块)
          sub-{id}_mmwave.meta.json      (stop 时写入)
        """
        # 创建目录
        save_dir = os.path.join(
            self.save_root,
            f'sub-{self.subject_id}_',
            'mmwave'
        )
        os.makedirs(save_dir, exist_ok=True)

        prefix = f'sub-{self.subject_id}_mmwave'

        # 打开文件
        bin_path = os.path.join(save_dir, f'{prefix}.datacube.bin')
        ts_path = os.path.join(save_dir, f'{prefix}_timestamps.csv')
        print(f"[mmWave]   创建 {os.path.basename(bin_path)}...", end=' ')
        self._bin_file = open(bin_path, 'wb')
        print("OK")
        print(f"[mmWave]   创建 {os.path.basename(ts_path)}...", end=' ')
        self._ts_file = open(ts_path, 'w')
        print("OK")

        # 写入 PSIC 全局头
        psic_hdr = _build_psic_header(
            range_fft=self.range_fft,
            doppler_fft=self.doppler_fft,
            tx_ant=self.tx_ant,
            rx_ant=self.rx_ant,
        )
        self._bin_file.write(psic_hdr)
        self._bin_file.flush()
        print(f"[mmWave]   已写入 PSIC 文件头 (32 字节)")

        self._bin_path = bin_path
        self._ts_path = ts_path
        self._npz_path = os.path.join(save_dir, f'{prefix}_datacube.npz')
        self._meta_path = os.path.join(save_dir, f'{prefix}.meta.json')
        self._recording_flag = True
        self.frame_count = 0
        self.byte_count = 0
        self.error_count = 0
        self._frame_cache = {}
        self._start_time = time.time()

        # 启动后台处理
        self._running = True
        self._worker = threading.Thread(target=self._process_data_loop, daemon=True)
        self._worker.start()

        # 启动 DLL 采集
        self._api.EnableRetransmission()
        self._api.StartCollectingData()

        print(f"[mmWave]   npz 分块保存: {os.path.basename(self._npz_path)}"
              f"  (每 {self._npz_save_interval} 帧一个数据块)")

    def stop(self):
        """停止采集, 保存 .npz 和 .meta.json"""
        # ① 先停 DLL 采集
        if self._api is None:
            print("[mmWave] 未连接，无需停止")
            return
        self._api.StopCollectingData()
        self._recording_flag = False

        # ② 等待队列排空（最多5秒超时，防止工作线程异常时永久阻塞）
        wait_start = time.time()
        while not self._data_queue.empty() and time.time() - wait_start < 5.0:
            time.sleep(0.1)
        if not self._data_queue.empty():
            print(f"[mmWave]   警告: 队列未完全排空"
                  f" ({self._data_queue.qsize()} 条残留)")

        # ③ 再停工作线程
        self._running = False

        # ④ 写入最后一块 npz
        print("[mmWave]   保存最后一块 npz...", end=' ')
        self._flush_npz_chunk()
        print("OK")

        # ⑤ 关闭文件
        print("[mmWave]   关闭文件...", end=' ')
        self._close_files()
        print("OK")

        # ⑥ 统计与 meta
        elapsed = time.time() - self._start_time if self._start_time else 0
        fps = self.frame_count / elapsed if elapsed > 0 else 0

        if not hasattr(self, '_meta_path') or not self._meta_path:
            print("[mmWave]   未调用 start(), 跳过 meta 写入")
        else:
            meta = {
                'subject_id': self.subject_id,
                'session': self.session,
                'transport': 'UART' if self.use_uart else 'SPI',
                'frame_count': self.frame_count,
                'duration_s': round(elapsed, 2),
                'fps': round(fps, 1),
                'range_fft': self.range_fft,
                'doppler_fft': self.doppler_fft,
                'tx_ant': self.tx_ant,
                'rx_ant': self.rx_ant,
                'bin_file': os.path.basename(self._bin_path) if self._bin_path else '',
                'ts_file': os.path.basename(self._ts_path) if hasattr(self, '_ts_path') and self._ts_path else '',
            }
            with open(self._meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
            print(f"[mmWave]   已写入 meta.json")

        print(f"[mmWave]   统计: {self.frame_count} 帧, "
              f"{self.byte_count / 1024:.0f} KB, {elapsed:.1f}s, {fps:.1f} fps")
        if self._convert_error:
            print(f"[mmWave]   警告: DatacubeConversion 失败 {self._convert_error} 帧"
                  f" (未写入 npz)")



# ============================================================
# 独立运行 (调试用)
# ============================================================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='mmWave 采集模块 v3')
    parser.add_argument('-s', '--subject', default='test', help='被试编号')
    parser.add_argument('--session', default='EXPERIMENT', help='Session 标签')
    parser.add_argument('-o', '--output', default='./data', help='数据根目录')
    parser.add_argument('-p', '--port', default='COM5', help='串口号')
    parser.add_argument('-d', '--duration', type=int, default=10, help='采集时长(秒)')
    parser.add_argument('--uart', action='store_true', help='UART 模式 (默认 SPI)')
    args = parser.parse_args()

    mm = MMWaveCapture(
        subject_id=args.subject,
        session=args.session,
        save_root=args.output,
        port=args.port,
        use_uart=args.uart,
    )

    try:
        mm.connect()
        mm.start()
        print(f"\n采集中... {args.duration} 秒后自动停止 (Ctrl+C 提前结束)")
        time.sleep(args.duration)
    except KeyboardInterrupt:
        print("\n[中断]")
    finally:
        mm.stop()
        mm.disconnect()
