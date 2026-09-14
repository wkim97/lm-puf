function save_dir = puf_generate_outputs(full_data, roi_coords, trigger_idx, file_dir, base_name, P)
%PUF_GENERATE_OUTPUTS  Sweep the temperature windows and write all outputs.
%   SAVE_DIR = PUF_GENERATE_OUTPUTS(DATA, ROI_COORDS, TRIG_IDX, FILE_DIR, BASE, P)
%   creates <FILE_DIR>/<BASE>_<trig>/ and writes, for every window
%   [start, start+step), [start+step, start+2*step), ... up to end:
%       R<n>_<min>-<max>_bin.png      binarised ROI          (P.do_bin)
%       R<n>_<min>-<max>_bits.png     32x32 response, x10    (P.do_bit)
%       R<n>_<min>-<max>_thermal.png  ROI colour-scaled      (P.do_thermal)
%       Reference_Thermal.png         ROI scaled to [start, end]
%       <BASE>_<trig>_<start>_<end>_<step>.xlsx   one column per window (P.do_excel)
%
%   P is a struct with fields: trig, start, end_, step, block, C, resize,
%   use_sign, crop, frame_avg, cmap, do_bin, do_bit, do_excel, do_thermal.
%
%   Mirrors generate_outputs_for_current_file in execute.py.

if P.end_ >= P.trig
    error('puf:params', 'End Temp must be lower than Trigger Temp!');
end
if P.start >= P.end_
    error('puf:params', 'Start Temp must be lower than End Temp.');
end

roi_img = puf_averaged_roi(full_data, roi_coords, trigger_idx, P.frame_avg);

folder_name = [base_name '_' puf_format_float(P.trig)];
save_dir = fullfile(file_dir, folder_name);
if ~exist(save_dir, 'dir')
    mkdir(save_dir);
end

cmap = puf_colormap(P.cmap, 256);
if P.do_thermal
    puf_save_colormapped_png(roi_img, fullfile(save_dir, 'Reference_Thermal.png'), cmap, P.start, P.end_);
end

headers = {};
columns = {};
curr = P.start;
idx = 1;
while curr < P.end_
    curr_max = round(curr + P.step, 2);
    curr = round(curr, 2);
    range_name = sprintf('R%d_%s-%s', idx, puf_format_float(curr), puf_format_float(curr_max));

    binary = puf_get_binary(roi_img, curr, curr_max, P.block, P.C);
    bits = puf_process_dct(binary, P.resize, P.use_sign, P.crop);

    if P.do_bin
        imwrite(binary, fullfile(save_dir, [range_name '_bin.png']));
    end
    if P.do_bit
        big_bits = uint8(kron(bits, ones(10)) * 255);
        imwrite(big_bits, fullfile(save_dir, [range_name '_bits.png']));
    end
    if P.do_thermal
        puf_save_colormapped_png(roi_img, fullfile(save_dir, [range_name '_thermal.png']), cmap, curr, curr_max);
    end
    if P.do_excel
        headers{end + 1} = range_name;                 %#ok<AGROW>
        columns{end + 1} = reshape(bits', [], 1);      %#ok<AGROW>  row-major flatten
    end

    curr = curr + P.step;
    idx = idx + 1;
end

if P.do_excel && ~isempty(headers)
    excel_name = sprintf('%s_%s_%s_%s_%s.xlsx', base_name, puf_format_float(P.trig), ...
        puf_format_float(P.start), puf_format_float(P.end_), puf_format_float(P.step));
    puf_write_bits_xlsx(fullfile(save_dir, excel_name), headers, columns);
end
end
