function [temp_history, start_idx, trigger_idx, triggered] = puf_compute_trigger(full_data, points, trig)
%PUF_COMPUTE_TRIGGER  Probe-temperature history and trigger frame of a recording.
%   [HIST, START, TRIG_IDX, TRIGGERED] = PUF_COMPUTE_TRIGGER(DATA, POINTS, TRIG)
%   DATA   : N x H x W temperature stack.
%   POINTS : 3 x 2 [x y] probe pixels in 0-based coordinates (as stored in
%            <group>_points.mat by both the Python and MATLAB tools).
%   TRIG   : trigger temperature.
%   HIST is the N x 1 mean temperature of the probes, START the index of the
%   coldest frame and TRIG_IDX the first frame at or after START whose probe
%   temperature is >= TRIG.  Indices are 0-based (frame numbers as shown in
%   the GUI); add 1 to index DATA.  When no frame reaches TRIG, TRIG_IDX is
%   the last frame and TRIGGERED is false.
%
%   Mirrors init_dashboard_data / update_plots in execute.py.

[n, h, w] = size(full_data);
xs = min(max(floor(points(:, 1)), 0), w - 1);
ys = min(max(floor(points(:, 2)), 0), h - 1);

vals = zeros(n, numel(xs), 'like', full_data);
for k = 1:numel(xs)
    vals(:, k) = full_data(:, ys(k) + 1, xs(k) + 1);
end
temp_history = double(mean(vals, 2));

[~, i_min] = min(temp_history);
start_idx = i_min - 1;

frames = (0:n - 1)';
valid = find(temp_history >= trig & frames >= start_idx);
if isempty(valid)
    trigger_idx = n - 1;
    triggered = false;
else
    trigger_idx = valid(1) - 1;
    triggered = true;
end
end
