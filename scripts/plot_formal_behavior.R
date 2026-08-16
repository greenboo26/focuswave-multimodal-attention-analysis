# plot_formal_behavior.R — 正式实验第一批行为汇总图 + 行为轨迹图
# ============================================================================
# 图表对应: 01_管理/图表索引.md（ALG-49, ALG-50）
# 数据输入: output/06_正式实验/图表数据/{behavior_summary_long.csv,
#                                          trajectory_within.csv, trajectory_between.csv}
# 输出文件: output/06_正式实验/图表数据/{behavior_summary.png, behavior_trajectory.png}
# 项目编号: 厚粲杯 / 正式实验第一批 | 分析脚本 v2
# 创建日期: 2026-08-16
# 规范: chart-config 方案 A（中文心理学期刊）——宋体/黑体, Set2 色盲友好, 无网格
# 字体: ragg 设备直接渲染系统字体（SimSun/SimHei），无 showtext 位图 dpi 缩放问题

library(ggplot2)

# 中文主题（chart-config 方案 A，ragg 设备下 family 直接指定系统字体）
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

# 数据目录
data_dir <- "D:/Project/厚粲杯/08_算法/output/06_正式实验/图表数据"

# ============================================================================
# 图1: 行为汇总图（4 面板: commission/omission/预判率/RT）
# ============================================================================
beh <- read.csv(file.path(data_dir, "behavior_summary_long.csv"), encoding = "UTF-8")

beh$metric_cn <- factor(beh$metric,
  levels = c("commission", "omission", "preempt_rate", "rt_mean"),
  labels = c("误按率 (%)", "遗漏率 (%)", "预判率 (%)", "反应时 (ms)"))

beh$subject <- factor(beh$subject, levels = c("011", "012", "013", "014", "016"))

p1 <- ggplot(beh, aes(x = subject, y = value)) +
  geom_col(aes(fill = subject), width = 0.62, alpha = 0.85) +
  geom_point(aes(x = subject, y = value), shape = 21,
             fill = "white", size = 2.2, stroke = 0.5) +
  facet_wrap(~ metric_cn, scales = "free_y", nrow = 1) +
  scale_fill_brewer(palette = "Set2") +
  labs(x = "被试编号", y = NULL,
       title = "正式实验第一批 SART 行为指标",
       subtitle = "行为有效被试 5 人（sub-015 规则理解错误已排除）") +
  theme_psy_cn(base_size = 18) +
  theme(legend.position = "none")

ggsave(file.path(data_dir, "behavior_summary.png"), p1,
       width = 200, height = 95, units = "mm", dpi = 300,
       device = ragg::agg_png, bg = "white")

# ============================================================================
# 图2: 行为轨迹图（左: Block 内 4 段; 右: Block 间 3 block）
# ============================================================================
within <- read.csv(file.path(data_dir, "trajectory_within.csv"), encoding = "UTF-8")
between <- read.csv(file.path(data_dir, "trajectory_between.csv"), encoding = "UTF-8")
within$subject <- factor(within$subject, levels = c("011", "012", "013", "014", "016"))
between$subject <- factor(between$subject, levels = c("011", "012", "013", "014", "016"))

p_within <- ggplot(within, aes(x = seg, y = comm_rate)) +
  geom_line(aes(group = subject), color = "grey70", linewidth = 0.4, alpha = 0.8) +
  geom_point(aes(group = subject), color = "grey70", size = 1.5, alpha = 0.8) +
  stat_summary(aes(group = 1), geom = "line", fun = mean, color = "#D95F02",
               linewidth = 1.2) +
  stat_summary(aes(group = 1), geom = "point", fun = mean, color = "#D95F02",
               size = 3, shape = 18) +
  scale_x_continuous(breaks = 1:4) +
  labs(x = "Block 内段位", y = "误按率 (%)", title = "Block 内轨迹") +
  theme_psy_cn(base_size = 16)

p_between <- ggplot(between, aes(x = block, y = comm_rate)) +
  geom_line(aes(group = subject), color = "grey70", linewidth = 0.4, alpha = 0.8) +
  geom_point(aes(group = subject), color = "grey70", size = 1.5, alpha = 0.8) +
  stat_summary(aes(group = 1), geom = "line", fun = mean, color = "#D95F02",
               linewidth = 1.2) +
  stat_summary(aes(group = 1), geom = "point", fun = mean, color = "#D95F02",
               size = 3, shape = 18) +
  scale_x_continuous(breaks = 1:3) +
  labs(x = "Block", y = "误按率 (%)", title = "Block 间轨迹") +
  theme_psy_cn(base_size = 16)

library(gridExtra)
p2 <- gridExtra::grid.arrange(p_within, p_between, ncol = 2,
  top = grid::textGrob("正式实验第一批误按率轨迹\n（个体灰线 + 组均值粗线, n = 5）",
                       gp = grid::gpar(fontfamily = "SimHei", fontsize = 20)))

ggsave(file.path(data_dir, "behavior_trajectory.png"), p2,
       width = 180, height = 100, units = "mm", dpi = 300,
       device = ragg::agg_png, bg = "white")

cat("行为汇总图与轨迹图已保存\n")
