function roi_img = puf_averaged_roi(full_data, roi_coords, trigger_idx, frame_avg)
%PUF_AVERAGED_ROI  ROI of the trigger frame, optionally averaged over neighbours.
%   ROI = PUF_AVERAGED_ROI(DATA, ROI_COORDS, TRIG_IDX, FRAME_AVG)
%   DATA       : N x H x W temperature stack.
%   ROI_COORDS : [x1 x2 y1 y2], 0-based with exclusive upper bounds (the
%                convention of <group>_roi.mat / common_roi.mat).
%   TRIG_IDX   : 0-based trigger frame.
%   FRAME_AVG  : number of frames (1..5) centred on the trigger to average.
%
%   Mirrors get_averaged_roi in execute.py.

x1 = double(roi_coords(1)); x2 = double(roi_coords(2));
y1 = double(roi_coords(3)); y2 = double(roi_coords(4));
n = size(full_data, 1);

if frame_avg <= 1
    roi_img = reshape(full_data(trigger_idx + 1, y1 + 1:y2, x1 + 1:x2), [y2 - y1, x2 - x1]);
    return
end

half = floor(frame_avg / 2);
s = max(0, trigger_idx - half);
e = min(n, s + frame_avg);
s = max(0, e - frame_avg);          % pull the start back so exactly FRAME_AVG frames are used

stack = full_data(s + 1:e, y1 + 1:y2, x1 + 1:x2);
roi_img = reshape(mean(stack, 1), [y2 - y1, x2 - x1]);
end
