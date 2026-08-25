function [file, path, filterindex] = uigetfile(varargin)
% Test-only adapter: return the preselected official VitalSense sample.
% The official VitalSense2024 source is not modified.
file = 'C_chest_normal_withECG.mat';
path = 'D:\VS_C1B\external\vendor\VitalSense2024\data\';
filterindex = 1;
end
