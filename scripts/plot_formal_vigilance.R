# plot_formal_vigilance.R — 正式实验第一批警觉度（清醒程度）分布 + 注意状态交叉图
# ============================================================================
# 图表对应: 01_管理/图表索引.md（ALG-52, ALG-53）
# 数据输入: output/06_正式实验/图表数据/{vigilance_dist.csv, vigilance_attention_cross.csv}
# 输出文件: output/06_正式实验/图表数据/{vigilance_dist.png, vigilance_cross.png}
# 项目编号: 厚粲杯 / 正式实验第一批 | 分析脚本 v2
# 创建日期: 2026-08-16
# 规范: chart-config 方案 A（中文心理学期刊）
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

# ============================================================================
# 图4: 警觉度分布（6 被试 × 4 点, 堆叠柱）
# ============================================================================
vig <- read.csv(file.path(data_dir, "vigilance_dist.csv"), encoding = "UTF-8")
vig$subject <- factor(vig$subject, levels = c("011", "012", "013", "014", "015", "016"))
vig$vigilance <- factor(vig$vigilance, levels = 1:4,
  labels = c("极度困倦", "比较困倦", "比较清醒", "极度清醒"))

p1 <- ggplot(vig, aes(x = subject, fill = vigilance)) +
  geom_bar(position = "stack", width = 0.65) +
  scale_fill_brewer(palette = "OrRd", direction = -1) +
  labs(x = "被试编号", y = "探针数（个）", fill = "警觉度",
       title = "正式实验第一批警觉度（清醒程度）分布",
       subtitle = "每被试 30 探针, 1=极度困倦 → 4=极度清醒") +
  theme_psy_cn(base_size = 18)

ggsave(file.path(data_dir, "vigilance_dist.png"), p1,
       width = 200, height = 115, units = "mm", dpi = 300,
       device = ragg::agg_png, bg = "white")

# ============================================================================
# 图5: 注意状态 × 警觉度 交叉（比例堆叠）
# ============================================================================
cross <- read.csv(file.path(data_dir, "vigilance_attention_cross.csv"), encoding = "UTF-8")
cross$attention <- factor(cross$attention, levels = 1:4,
  labels = c("专注", "任务干扰", "走神", "大脑空白"))
cross$vigilance <- factor(cross$vigilance, levels = 1:4,
  labels = c("极度困倦", "比较困倦", "比较清醒", "极度清醒"))

p2 <- ggplot(cross, aes(x = attention, y = count, fill = vigilance)) +
  geom_bar(position = "fill", width = 0.6, stat = "identity") +
  scale_y_continuous(labels = scales::percent) +
  scale_fill_brewer(palette = "OrRd", direction = -1) +
  labs(x = "注意状态", y = "比例", fill = "警觉度",
       title = "注意状态 × 警觉度（清醒程度）交叉",
       subtitle = "走神/大脑空白状态下困倦比例高于专注（6 被试 180 探针）") +
  theme_psy_cn(base_size = 18)

ggsave(file.path(data_dir, "vigilance_cross.png"), p2,
       width = 180, height = 115, units = "mm", dpi = 300,
       device = ragg::agg_png, bg = "white")

cat("警觉度分布图与交叉图已保存\n")
