function run_official_vitalsig_batch()
% OFFICIAL_DATASET_ADAPTER only. The VitalSense2024 source remains unchanged.
dataDir = 'D:\VS_C1B_DATA';
outDir = 'D:\VS_C1B_OFFICIAL_OUTPUT';
beatDir = fullfile(outDir, 'official_beats');
official = 'D:\VS_C1B\external\vendor\VitalSense2024';
if ~exist(beatDir, 'dir'); mkdir(beatDir); end
addpath(official, '-begin');
set(0, 'DefaultFigureVisible', 'off');
diary(fullfile(outDir, 'official_batch_matlab_console.log'));
fprintf('OFFICIAL_BATCH_BEGIN\n');
fprintf('official_commit=d9f71f96800da7ed2192ff1dc0cba0f0ef5b6de6\n');
fprintf('data_dir=%s\n', dataDir);
subjects = arrayfun(@(x) sprintf('VS%02d', x), 1:24, 'UniformOutput', false);
conditions = {'Resting','Apnea'};
rows = cell(0, 10);
for si = 1:numel(subjects)
    for ci = 1:numel(conditions)
        subject = subjects{si}; condition = conditions{ci};
        radarFile = fullfile(dataDir, [subject '_' condition '.mat']);
        outBeat = fullfile(beatDir, [subject '_' condition '_official_beats.csv']);
        try
            S = load(radarFile, 'VitalSig', 'Radar');
            vital = double(S.VitalSig(:)');
            fs = double(S.Radar.fs);
            t = double(S.Radar.t_frame(:)'); t = t - t(1);
            [beatT, hrFFT, hrPeaks, hrIntervals] = official_vitalsig_pipeline(vital, 1/fs, t);
            writematrix(beatT(:), outBeat);
            rows(end+1,:) = {subject, condition, fs, t(end), hrFFT, hrPeaks, hrIntervals, numel(beatT), 'complete', ''}; %#ok<AGROW>
            fprintf('COMPLETE %s %s beats=%d hr_fft=%.6f hr_peaks=%.6f hr_intervals=%.6f\n', subject, condition, numel(beatT), hrFFT, hrPeaks, hrIntervals);
        catch ME
            rows(end+1,:) = {subject, condition, NaN, NaN, NaN, NaN, NaN, NaN, 'error', getReport(ME,'basic','hyperlinks','off')}; %#ok<AGROW>
            fprintf('ERROR %s %s %s\n', subject, condition, getReport(ME,'extended','hyperlinks','off'));
        end
    end
end
T = cell2table(rows, 'VariableNames', {'subject','condition','radar_fs_hz','duration_s','hr_fft_bpm','hr_peaks_bpm','hr_intervals_bpm','radar_beats','status','error'});
writetable(T, fullfile(outDir, 'official_session_results.csv'));
status = struct('status','OFFICIAL_BATCH_COMPLETE','sessions',height(T),'complete_sessions',sum(strcmp(T.status,'complete')),'error_sessions',sum(strcmp(T.status,'error')),'official_commit','d9f71f96800da7ed2192ff1dc0cba0f0ef5b6de6');
fid=fopen(fullfile(outDir,'official_batch_status.json'),'w'); fprintf(fid,'%s\n',jsonencode(status)); fclose(fid);
fprintf('OFFICIAL_BATCH_COMPLETE complete=%d errors=%d\n', status.complete_sessions, status.error_sessions);
diary off;
end

function [locs_hsig, bpm_fft, bpm_pks, bpm_intv] = official_vitalsig_pipeline(vitsig, T_frame, Radar_t)
% Official main.m cardiac route with only the dataset input adapted.
fs = 1 / T_frame;
blp_r = fir1(300, 0.3/(fs/2), 'low');
rsig_lp = filtfilt(blp_r, 1, vitsig);
hsig_lp = vitsig - rsig_lp;
hsig_fft = fft(hsig_lp); hsig_fft(1:40) = 0; hsig_lp = real(ifft(hsig_fft));
sig = hsig_lp; orden_zp = 32;
sig_zp = [sig zeros(1, orden_zp*length(sig))]; sig_fft = fft(sig_zp);
win = zeros(1, length(sig_fft));
h_low = round((0.667*length(sig))/(1/T_frame))+1;
h_high = round((3.333*length(sig))/(1/T_frame))+1;
lo1 = max(1, h_low*orden_zp); hi1 = min(length(win), h_high*orden_zp); win(lo1:hi1) = 1;
k=1; for i=hi1+1:min(length(win),hi1+4); win(i)=cos(k*pi/8); k=k+1; end
k=1; for i=lo1-1:-1:max(1,lo1-4); win(i)=cos(k*pi/8); k=k+1; end
leftLo=max(1,lo1-4); leftHi=min(length(win),hi1+4); rightLo=max(1,length(sig_fft)-(hi1+4)+1); rightHi=min(length(win),length(sig_fft)-(lo1-4)+1);
if rightHi-rightLo == leftHi-leftLo; win(rightLo:rightHi)=win(leftLo:leftHi); end
sig_fclean = sig_fft .* win; sig_fclean_cut = sig_fclean(1:floor(length(sig_fclean)/2));
SIG0 = abs(sig_fclean_cut); SIG = SIG0; SIG(SIG<0.03)=[]; amp_mean = mean(SIG);
[~,loc_fft] = findpeaks(SIG0, 1:length(SIG0), 'MinPeakProminence', amp_mean*2, 'MinPeakDistance', 400);
loc_d = HRestim(T_frame, sig, sig_fclean_cut, sig_fft, loc_fft);
Fs_fclean = 1/(length(sig_fft)*T_frame); bps = loc_d*Fs_fclean; bpm_fft = bps*60; Tfil0 = round((1/bps)/T_frame);
filA = max(sig)*sin(linspace(0,pi,Tfil0))+min(sig); sig1_0=conv(sig,filA); sig1_0=2*(sig1_0*(max(abs(sig))/max(abs(sig1_0)))); sig1=circshift(sig1_0,fix(-length(filA)/2));
len_sig=length(sig); minpeakdist=fix(Tfil0*0.7); [~,locs_sig1]=findpeaks(sig1(1:len_sig),1:len_sig,'MinPeakDistance',minpeakdist);
pulseA=max(round(locs_sig1-Tfil0/2),1); pulseB=min(round(locs_sig1+Tfil0/2),len_sig);
if numel(pulseA)<3; error('official pulse template has fewer than 3 preliminary pulses'); end
pulses=cell(1,numel(pulseA)); for i=1:numel(pulseA); pulses{i}=sig(pulseA(i):pulseB(i)); end; pulses=pulses(2:end-1);
minLen=min(cellfun(@numel,pulses)); fil_sum=zeros(1,minLen); for i=1:numel(pulses); fil_sum=fil_sum+pulses{i}(1:minLen); end; filB=fil_sum/numel(pulses);
filC=fliplr(filB); hsig1=conv(sig,filC); hsig2=2*(hsig1*(max(abs(sig))/max(abs(hsig1)))); hsig=circshift(hsig2,fix(-length(filC)/2));
[~,locs_hsig]=findpeaks(hsig(1:len_sig),Radar_t(1:len_sig),'MinPeakDistance',minpeakdist*T_frame,'MinPeakProminence',0.02);
bpm_pks=length(locs_hsig)/(length(sig)*T_frame/60); loc_diff=diff(locs_hsig); threshold=mean(loc_diff)+2*std(loc_diff);
while ~isempty(loc_diff) && max(loc_diff)>threshold; [~,idx]=max(loc_diff); loc_diff(idx)=[]; end
if isempty(loc_diff); bpm_intv=NaN; else; bpm_intv=60/mean(loc_diff); end
end
