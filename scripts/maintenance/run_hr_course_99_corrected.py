from __future__ import annotations
import importlib.util, json
from pathlib import Path

ALGO=Path(r"D:\Project\厚粲杯\08_算法\scripts\process_vital_signs_v3_1_1.py")
RAW=Path(r"D:\acq_mmwave_data")
OUT=Path(r"D:\Project\厚粲杯\08_算法\output\20_生理金标准验证\06_HR_COURSE_99_CORRECTED_GATE")
SUBS=[('sub-97793_','sub-97793'),('sub-97794_','sub-97994'),('sub-97795_','sub-97795'),('sub-97796_','sub-97796'),('sub-9779_','sub-9779')]
def load_mod():
 s=importlib.util.spec_from_file_location('v311_99',ALGO); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def read_json(p):
 return json.loads(p.read_text(encoding='utf-8'))
def main():
 m=load_mod(); OUT.mkdir(parents=True,exist_ok=True)
 for fn in ('plot_result','save_selected_channel_range_fft','save_breath_raw_phase_plot','save_breath_unwrapped_phase_plot'):
  if hasattr(m,fn): setattr(m,fn,lambda *a,**k: OUT/'suppressed.png')
 for fn in ('save_range_fft_map','save_range_fft_channel_grid'):
  if hasattr(m,fn): setattr(m,fn,lambda *a,**k:(OUT/'suppressed.png',OUT/'suppressed.png'))
 for refsub,prefix in SUBS:
  raw=RAW/(prefix+'_')/'mmwave'; pattern=f'{prefix}_mmwave_datacube_part*.npz'; subout=OUT/refsub
  selout=subout/'_selection_60s'; final=subout/f'{prefix}_ses-SART_mmwave_vital_signs.json'
  if final.exists(): print('SKIP',refsub,flush=True); continue
  selout.mkdir(parents=True,exist_ok=True)
  sj=selout/f'{prefix}_ses-SART_mmwave_vital_signs.json'
  if not sj.exists():
   print('SELECT',refsub,flush=True)
   m.analyze_long_record(parts_dir=raw,output_dir=selout,session=f'{prefix}_ses-SART',method='bp_heart',pattern=pattern,frame_start=0,frame_end=6000,min_range_m=.3,max_range_m=1.5,bin_spacing_m=.037,range_bias_m=0.0)
  sd=read_json(sj); hch=int(sd['channels']['heart']); hbin=int(sd['bins']['heart'])
  print('FULL',refsub,'corrected ch/bin',hch,hbin,flush=True)
  m.analyze_long_record(parts_dir=raw,output_dir=subout,session=f'{prefix}_ses-SART',method='bp_heart',pattern=pattern,forced_heart_ch=hch,forced_heart_bin=hbin,min_range_m=.3,max_range_m=1.5,bin_spacing_m=.037,range_bias_m=0.0)
  print('DONE',refsub,flush=True)
if __name__=='__main__': main()


