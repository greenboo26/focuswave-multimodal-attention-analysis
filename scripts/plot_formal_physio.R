# plot_formal_physio.R — 正式实验第一批毫米波生理分布图
# ============================================================================
# 图表对应: 01_管理/图表索引.md（ALG-51）
# 数据输入: output/06_正式实验/图表数据/physio_dist_long.csv
# 输出文件: output/06_正式实验/图表数据/physio_dist.png
# 项目编号: 厚粲杯 / 正式实验第一批 | 分析脚本 v2
# 创建日期: 2026-08-16
# 规范: chart-config 方案 A（中文心理学期刊）——宋体/黑体, Set2 色盲友好, 无网格
# 字体: ragg 设备直接渲染系统字体（SimSun/SimHei）

library(ggplot2)

theme_psy_cn <- function(base_size = 18) {
  theme_minimal(base_family = "SimSun", base_size = base_size) %+replace%
    theme(
      panel.grid.major = element_blank(),
      panel.grid.minor = element_blank(),
      panel.border   = element_rect(fill = NA, color = "grey50", linewidth = 0.4),
      axis.line       = element_blank(),
      axis.ticks      = element_line(color = "grey50", linewidth = 0.3),
      axis.ticks.length = unit(1.5, "mm"),
      axis.title.x    = element_text(family = "SimHei", size = base_size, margin = margin(t = 10)),
      axis.title.y    = element_text(family = "SimHei", size = base_size, margin = margin(r = 10)),
      axis.text       = element_text(family = "SimSun", size = base_size - 1, color = "black"),
      legend.position  = "bottom",
      legend.title     = element_text(family = "SimHei", size = base_size),
      legend.text      = element_text(family = "SimSun", size = base_size - 1),
      legend.key.size  = unit(6, "mm"),
      plot.title       = element_text(family = "SimHei", size = base_size + 5, hjust = 0.5,
                                       margin = margin(b = 12)),
      plot.subtitle    = element_text(family = "SimSun", size = base_size - 2, color = "grey50",
                                       hjust = 0.5),
      plot.margin      = margin(15, 15, 12, 12),
      strip.text       = element_text(family = "SimHei", size = base_size + 2, margin = margin(b = 6)),
      strip.background = element_rect(fill = "grey95", color = NA)
    )
}

data_dir <- "D:/Project/厚粲杯/08_算法/output/06_正式实验/图表数据"
physio <- read.csv(file.path(data_dir, "physio_dist_long.csv"), encoding = "UTF-8")

physio$subject <- factor(physio$subject,
  levels = c("011", "012", "013", "014", "015", "016"))

physio$metric_cn <- factor(physio$metric,
  levels = c("hr_bpm", "sdnn_ms", "rmssd_ms"),
  labels = c("心率 (bpm)", "SDNN (ms)", "RMSSD (ms)"))

p <- ggplot(physio, aes(x = subject, y = value, fill = subject)) +
  geom_violin(alpha = 0.55, linewidth = 0.3, trim = FALSE) +
  geom_boxplot(width = 0.15, alpha = 0.9, outlier.size = 0.6,
               outlier.alpha = 0.4, linewidth = 0.3) +
  facet_wrap(~ metric_cn, scales = "free_y", nrow = 1) +
  scale_fill_brewer(palette = "Set2") +
  labs(x = "被试编号", y = NULL,
       title = "正式实验第一批毫米波生理指标分布",
       subtitle = "6 生理被试全程可信窗（sub-015 行为无效但生理保留）") +
  theme_psy_cn(base_size = 18) +
  theme(legend.position = "none")

ggsave(file.path(data_dir, "physio_dist.png"), p,
       width = 200, height = 100, units = "mm", dpi = 300,
       device = ragg::agg_png, bg = "white")

cat("生理分布图已保存\n")
