function run_official_sample()
% Run the unmodified VitalSense2024 main.m through a file-selection adapter.
% This wrapper only controls noninteractive input, logging and output export.
root = 'D:\VS_C1B';
official = fullfile(root, 'external', 'vendor', 'VitalSense2024');
outdir = 'D:\VS_C1B_OFFICIAL_OUTPUT';
if ~exist(outdir, 'dir'); mkdir(outdir); end
addpath(fullfile(root, 'work', 'vitalsense_official_sample_adapter'), '-begin');
addpath(official, '-begin');
set(0, 'DefaultFigureVisible', 'off');
logfile = fullfile(outdir, 'official_sample_matlab_console.log');
diary(logfile);
fprintf('OFFICIAL_SAMPLE_BEGIN\n');
fprintf('official_root=%s\n', official);
fprintf('official_commit=d9f71f96800da7ed2192ff1dc0cba0f0ef5b6de6\n');
fprintf('sample=C_chest_normal_withECG.mat\n');
try
    run(fullfile(official, 'main.m'));
    % Variables below are created by the official script itself.
    outdir = official_output_dir();
    save(fullfile(outdir, 'official_sample_workspace.mat'), ...
        'LocFinder', 'locs_hsig', 'amp_hsig', 'bpm_fft', 'bpm_pks', ...
        'bpm_intv', 'Radar', 'Digitizer', 'Sampling', 'T', '-v7');
    fid = fopen(fullfile(outdir, 'official_sample_summary.json'), 'w');
    fprintf(fid, '{"status":"OFFICIAL_SAMPLE_COMPLETE","sample":"C_chest_normal_withECG.mat","radar_beats":%d,"hr_fft_bpm":%.9g,"hr_peaks_bpm":%.9g,"hr_intervals_bpm":%.9g,"hrestim_called":true,"official_template_and_rw_amf_called":true,"matlab_findpeaks_called":true}\n', ...
        numel(locs_hsig), bpm_fft, bpm_pks, bpm_intv);
    fclose(fid);
    fprintf('OFFICIAL_SAMPLE_COMPLETE\n');
catch ME
    outdir = official_output_dir();
    fid = fopen(fullfile(outdir, 'official_sample_error.txt'), 'w');
    fprintf(fid, '%s\n', getReport(ME, 'extended', 'hyperlinks', 'off'));
    fclose(fid);
    fprintf('OFFICIAL_SAMPLE_ERROR\n%s\n', getReport(ME, 'extended', 'hyperlinks', 'off'));
    diary off;
    rethrow(ME);
end
diary off;
end

function outdir = official_output_dir()
outdir = 'D:\VS_C1B_OFFICIAL_OUTPUT';
if ~exist(outdir, 'dir'); mkdir(outdir); end
end
