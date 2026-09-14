function execute()
%EXECUTE  Thermal Analysis Pro - temperature windows to 1024-bit PUF responses.
%   EXECUTE() opens the extractor window.  Load a *_new.mat stack
%   (samplematcher output), click three probe points, drag the ROI, set the
%   trigger / window parameters and press "Run Macro & Save".  For every
%   temperature window the ROI is binarised (adaptive threshold), area-resized,
%   DCT-transformed, sign-quantised, cropped to 32 x 32 and XORed with a fixed
%   seed; the outputs (*_bin.png, *_bits.png, *_thermal.png and one .xlsx with
%   1024 bits per window) are written to <name>_<trigger>/ next to the input.
%   "Batch Save Points/ROI" sets up points / ROI for many groups in a row and
%   "Batch Run All Samples" processes all files that have saved points / ROI.
%
%   MATLAB port of execute.py.  Tested with MATLAB R2016a.
%   Requires Image Processing Toolbox.

addpath(fullfile(fileparts(mfilename('fullpath')), 'lib'));

BG     = [46 46 46] / 255;
PANEL  = [60 63 65] / 255;
TEXTC  = [1 1 1];
ACCENT = [58 150 221] / 255;
ENTRY  = [69 73 74] / 255;
LISTBG = [43 43 43] / 255;
CMAPS  = {'jet', 'parula', 'hot', 'cool', 'gray', 'bone', 'copper', 'hsv'};   % built-in MATLAB colormaps (preview / thermal PNG only)
RIGHT_W = 400;

script_dir = fileparts(mfilename('fullpath'));

% ---- state --------------------------------------------------------------
mat_path = '';
file_dir = '';
base_name = '';
full_data = [];
num_frames = 0;
points = [];            % 3 x 2 [x y], 0-based
roi_coords = [];        % [x1 x2 y1 y2], 0-based, exclusive upper bounds
trigger_idx = -1;       % 0-based
temp_history = [];
start_frame_idx = 0;    % 0-based
point_setup_mode = false;
point_setup_queue = {};
point_setup_index = 0;
cbar = [];

% ---- window -------------------------------------------------------------
fig = figure('Name', 'Thermal Analysis Pro (Perfect Arrow Navigation)', 'NumberTitle', 'off', ...
    'MenuBar', 'none', 'ToolBar', 'none', 'Color', BG, 'Units', 'pixels', ...
    'Position', [40 40 1400 980]);

ax_graph = axes('Parent', fig, 'Units', 'pixels');
ax_roi   = axes('Parent', fig, 'Units', 'pixels');
ax_bin   = axes('Parent', fig, 'Units', 'pixels');
for a = [ax_graph ax_roi ax_bin]
    style_axes(a);
end

right = uipanel('Parent', fig, 'Units', 'pixels', 'BackgroundColor', PANEL, 'BorderType', 'none');

% File Operations
p_file = section(right, ' File Operations ');
lbl_filename = uicontrol('Parent', p_file, 'Style', 'text', 'String', 'No file loaded', ...
    'HorizontalAlignment', 'center', 'BackgroundColor', PANEL, 'ForegroundColor', TEXTC, ...
    'FontName', 'Segoe UI', 'FontSize', 10);
chk_reset_pts = checkbox(p_file, 'Reset Points', false, []);
chk_reset_roi = checkbox(p_file, 'Reset ROI', false, []);
btn_load = button(p_file, 'Load New File', @(~, ~) load_new_file());

% Parameters
p_param = section(right, ' Parameters ');
[~, ed_trig]  = entry(p_param, 'Trigger Temp:', '50.0');
[~, ed_start] = entry(p_param, 'Start Temp:', '40.0');
[~, ed_end]   = entry(p_param, 'End Temp:', '49.0');
[~, ed_step]  = entry(p_param, 'Step Size:', '3.0');

% Noise Filter Parameters
p_filter = section(right, ' Noise Filter Parameters ');
[~, ed_block]  = entry(p_filter, 'Adapt. Block Size (odd):', '21');
[~, ed_C]      = entry(p_filter, 'Adapt. C (bias):', '2');
[~, ed_resize] = entry(p_filter, 'Resize Target (NxN):', '64');
[~, ed_crop]   = entry(p_filter, 'DCT Crop Range:', '2:33');
[~, ed_avg]    = entry(p_filter, 'Frame Avg (1~5):', '1');
chk_dct_sign = checkbox(p_filter, 'Apply DCT sign quantize (dct > 0)', true, @(~, ~) update_plots());

% Visualization
p_vis = section(right, ' Visualization (Preview Only) ');
[~, ed_vmin] = entry(p_vis, 'Min Temp:', '40.0');
[~, ed_vmax] = entry(p_vis, 'Max Temp:', '43.0');
lbl_cmap = uicontrol('Parent', p_vis, 'Style', 'text', 'String', 'Colormap:', 'HorizontalAlignment', 'left', ...
    'BackgroundColor', PANEL, 'ForegroundColor', TEXTC, 'FontName', 'Segoe UI', 'FontSize', 10);
pop_cmap = uicontrol('Parent', p_vis, 'Style', 'popupmenu', 'String', CMAPS, 'Value', 1, ...
    'BackgroundColor', ENTRY, 'ForegroundColor', TEXTC, 'FontName', 'Segoe UI', 'FontSize', 10, ...
    'Callback', @(~, ~) update_plots());

% Preview Ranges
p_list = section(right, ' Preview Ranges (Use Arrows) ');
list_ranges = uicontrol('Parent', p_list, 'Style', 'listbox', 'String', {}, 'Value', [], 'Min', 0, 'Max', 1, ...
    'BackgroundColor', LISTBG, 'ForegroundColor', TEXTC, 'FontName', 'Consolas', 'FontSize', 10, ...
    'Callback', @(~, ~) on_range_select());

% Save Options
p_opt = section(right, ' Save Options ');
chk_thermal = checkbox(p_opt, 'Save Thermal ROI (.png)', true, []);
chk_binary  = checkbox(p_opt, 'Save Binary Image (.png)', true, []);
chk_bit     = checkbox(p_opt, 'Save Bit Image (XOR) (.png)', true, []);
chk_excel   = checkbox(p_opt, 'Save Excel Data (.xlsx)', true, []);

% Run buttons
btn_run   = button(right, 'Run Macro & Save', @(~, ~) run_macro());
btn_setup = button(right, 'Batch Save Points/ROI', @(~, ~) run_batch_point_setup());
btn_batch = button(right, 'Batch Run All Samples', @(~, ~) run_batch_macro());

layout();
set(fig, 'ResizeFcn', @(~, ~) layout());

% ======================================================================
%  layout
% ======================================================================
    function layout()
        if ~ishandle(fig), return, end
        pos = get(fig, 'Position');
        W = pos(3); H = pos(4);
        set(right, 'Position', [W - RIGHT_W, 0, RIGHT_W, H]);
        left_w = W - RIGHT_W;
        m = 60;
        gw = left_w - 2 * m;
        set(ax_graph, 'Position', [m, H * 0.58, gw, H * 0.34]);
        pw = (gw - 80) / 2;
        set(ax_roi, 'Position', [m, H * 0.07, pw, H * 0.40]);
        set(ax_bin, 'Position', [m + pw + 80, H * 0.07, pw, H * 0.40]);

        % right panel: stack the sections from the top
        pw = RIGHT_W - 20;
        y = H - 8;
        y = place_section(p_file, y, 118, pw);
        set(lbl_filename, 'Position', [10, 118 - 46, pw - 20, 20]);
        set(chk_reset_pts, 'Position', [12, 118 - 74, 120, 22]);
        set(chk_reset_roi, 'Position', [140, 118 - 74, 120, 22]);
        set(btn_load, 'Position', [10, 8, pw - 20, 30]);

        y = place_section(p_param, y, 4 * 27 + 26, pw);
        place_entries(p_param, [ed_trig ed_start ed_end ed_step], pw);

        y = place_section(p_filter, y, 5 * 27 + 24 + 30, pw);
        place_entries(p_filter, [ed_block ed_C ed_resize ed_crop ed_avg], pw);
        set(chk_dct_sign, 'Position', [12, 8, pw - 24, 22]);

        y = place_section(p_vis, y, 3 * 27 + 26, pw);
        place_entries(p_vis, [ed_vmin ed_vmax], pw);
        set(lbl_cmap, 'Position', [12, 12, 150, 20]);
        set(pop_cmap, 'Position', [170, 10, pw - 185, 24]);

        y = place_section(p_list, y, 112, pw);
        set(list_ranges, 'Position', [10, 8, pw - 20, 80]);

        y = place_section(p_opt, y, 4 * 22 + 34, pw);
        chks = [chk_thermal chk_binary chk_bit chk_excel];
        for k = 1:4
            set(chks(k), 'Position', [12, 4 * 22 + 34 - 26 - k * 22 + 4, pw - 24, 22]);
        end

        bh = 34;
        set(btn_run,   'Position', [10, y - 4 - bh, pw, bh]);
        set(btn_setup, 'Position', [10, y - 4 - 2 * bh - 8, pw, bh]);
        set(btn_batch, 'Position', [10, y - 4 - 3 * bh - 16, pw, bh]);
    end

    function y = place_section(p, y_top, h, pw)
        set(p, 'Position', [10, y_top - h, pw, h]);
        y = y_top - h - 5;
    end

    function place_entries(p, eds, pw)
        ph = get(p, 'Position'); ph = ph(4);
        for k = 1:numel(eds)
            lbl = get(eds(k), 'UserData');
            yk = ph - 22 - k * 27;
            set(lbl, 'Position', [12, yk, 165, 22]);
            set(eds(k), 'Position', [180, yk, pw - 195, 24]);
        end
    end

% ======================================================================
%  file handling
% ======================================================================
    function load_new_file()
        [name, folder] = uigetfile({'*_new.mat', 'New MAT files (*_new.mat)'}, 'Select _new.mat file', script_dir);
        if isequal(name, 0), return, end
        fp = fullfile(folder, name);
        if ~puf_names('is_target', fp)
            warndlg('Only *_new.mat files can be selected.', 'Invalid File');
            return
        end
        point_setup_mode = false;
        point_setup_queue = {};
        point_setup_index = 0;
        prepare_file_context(fp);
        select_points_popup();
    end

    function prepare_file_context(fp)
        mat_path = fp;
        file_dir = fileparts(fp);
        base_name = puf_names('base_name', fp);
        [~, n, e] = fileparts(fp);
        set(lbl_filename, 'String', [n e]);
        roi_coords = [];
        cla(ax_graph); cla(ax_roi); cla(ax_bin);
        if ~isempty(cbar) && ishandle(cbar), delete(cbar); cbar = []; end
        load_data_logic();
    end

    function load_data_logic()
        try
            full_data = puf_load_images(mat_path, 'images');
            num_frames = size(full_data, 1);
            frame_means = mean(reshape(full_data, num_frames, []), 2);
            [~, i] = min(frame_means);
            start_frame_idx = i - 1;
        catch err
            errordlg(sprintf('Load failed: %s', err.message), 'Error');
        end
    end

    function fr = frame(idx0)
        fr = reshape(full_data(idx0 + 1, :, :), size(full_data, 2), size(full_data, 3));
    end

% ======================================================================
%  point / ROI selection popups (blocking)
% ======================================================================
    function ok = select_points_popup()
        ok = false;
        reset_pts = get(chk_reset_pts, 'Value');
        pts_path = puf_names('points_path', mat_path);
        if ~reset_pts && exist(pts_path, 'file')
            loaded = false;
            try
                s = load(pts_path);
                points = double(s.points);
                loaded = true;
            catch
            end
            if loaded
                fprintf('>> [Points] Loaded from %s\n', pts_path);
                select_roi_popup();
                ok = true;
                return
            end
        end

        temp_points = zeros(0, 2);
        if start_frame_idx < num_frames, initial_frame = start_frame_idx; else initial_frame = 0; end
        pf = figure('Name', 'Select Points', 'NumberTitle', 'off', 'Color', 'w', 'MenuBar', 'none', ...
            'ToolBar', 'figure', 'Units', 'pixels', 'Position', [150 100 1000 800]);
        axp = axes('Parent', pf, 'Position', [0.05 0.18 0.9 0.74]);
        img = imagesc(frame(initial_frame), 'Parent', axp);
        colormap(axp, jet(256));
        axis(axp, 'image', 'off');
        hold(axp, 'on');
        title(axp, sprintf('Select 3 Points (Frame %d)\nUse Slider to find best view -> Click 3 times', initial_frame), 'FontSize', 11);
        uicontrol('Parent', pf, 'Style', 'text', 'String', 'Frame', 'Units', 'normalized', ...
            'Position', [0.12 0.045 0.07 0.03], 'BackgroundColor', 'w');
        step = 1 / max(num_frames - 1, 1);
        uicontrol('Parent', pf, 'Style', 'slider', 'Min', 0, 'Max', max(num_frames - 1, 1), 'Value', initial_frame, ...
            'SliderStep', [step, min(1, 10 * step)], 'Units', 'normalized', 'Position', [0.2 0.05 0.6 0.03], ...
            'Callback', @(s, ~) update_slider(round(get(s, 'Value'))));
        set(pf, 'WindowButtonDownFcn', @onclick);
        uiwait(pf);

        if size(temp_points, 1) == 3
            points = temp_points;
            puf_save_mat(pts_path, struct('points', points));
            select_roi_popup();
            ok = true;
        else
            if point_setup_mode
                point_setup_mode = false;
                warndlg('Point selection was cancelled or incomplete.', 'Batch Point Setup Stopped');
            else
                msgbox('Selection cancelled or incomplete.', 'Info');
            end
        end

        function update_slider(idx)
            cf = frame(idx);
            set(img, 'CData', cf);
            vmin_new = min(cf(:)); vmax_new = max(cf(:));
            set(axp, 'CLim', [vmin_new, max(vmax_new, vmin_new + eps)]);
            title(axp, sprintf('Select 3 Points (Frame %d)\nRange: %.1f~%.1f', idx, vmin_new, vmax_new), 'FontSize', 11);
        end

        function onclick(~, ~)
            if ~strcmp(get(pf, 'SelectionType'), 'normal'), return, end
            cp = get(axp, 'CurrentPoint');
            x = cp(1, 1); y = cp(1, 2);
            xl = get(axp, 'XLim'); yl = get(axp, 'YLim');
            if x < xl(1) || x > xl(2) || y < yl(1) || y > yl(2), return, end
            temp_points(end + 1, :) = [x - 1, y - 1];
            plot(axp, x, y, 'rx', 'MarkerSize', 10, 'LineWidth', 2);
            if size(temp_points, 1) >= 3
                uiresume(pf);
                close(pf);
            end
        end
    end

    function select_roi_popup()
        reset_roi = get(chk_reset_roi, 'Value');
        common_roi_path = puf_names('common_roi_path', mat_path);
        group_roi_path = puf_names('group_roi_path', mat_path);
        template_side = [];
        if exist(common_roi_path, 'file')
            try
                d = load(common_roi_path);
                template_side = get_roi_side(d.roi);
            catch
                template_side = [];
            end
        end
        if ~reset_roi && exist(group_roi_path, 'file')
            loaded = false;
            try
                d = load(group_roi_path);
                roi_coords = double(d.roi(:))';
                loaded = true;
            catch
            end
            if loaded
                fprintf('>> [Group ROI] Loaded from %s\n', group_roi_path);
                init_dashboard_data();
                return
            end
        end
        if start_frame_idx < num_frames, frame_idx = start_frame_idx; else frame_idx = 0; end
        sample = frame(frame_idx);
        [h_img, w_img] = size(sample);

        pf = figure('Name', 'Select ROI', 'NumberTitle', 'off', 'Color', 'w', 'MenuBar', 'none', ...
            'ToolBar', 'none', 'Units', 'pixels', 'Position', [150 150 1000 620]);
        axr = axes('Parent', pf, 'Position', [0.03 0.03 0.94 0.88]);
        imagesc(sample, 'Parent', axr);
        colormap(axr, jet(256));
        axis(axr, 'image', 'off');
        hold(axr, 'on');
        plot(axr, points(:, 1) + 1, points(:, 2) + 1, 'rx');
        if ~isempty(template_side)
            title(axr, sprintf('Draw ROI center -> Fixed square size %dpx -> Close', template_side), 'FontSize', 11, 'Color', 'b');
        else
            title(axr, 'Draw ROI -> Snaps to SQUARE on release -> Close', 'FontSize', 11, 'Color', 'b');
        end
        rect = [];
        drag_start = [];
        set(pf, 'WindowButtonDownFcn', @on_down, 'WindowButtonUpFcn', @on_up);
        uiwait(pf);

        if isempty(roi_coords)
            if ~isempty(template_side), min_side = template_side; else min_side = min(w_img, h_img); end
            roi_coords = [0, min_side, 0, min_side];
        end
        puf_save_mat(group_roi_path, struct('roi', roi_coords));
        if isempty(template_side) || reset_roi
            puf_save_mat(common_roi_path, struct('roi', roi_coords));
        end
        init_dashboard_data();

        function on_down(~, ~)
            if ~strcmp(get(pf, 'SelectionType'), 'normal'), return, end
            cp = get(axr, 'CurrentPoint');
            xl = get(axr, 'XLim'); yl = get(axr, 'YLim');
            if cp(1, 1) < xl(1) || cp(1, 1) > xl(2) || cp(1, 2) < yl(1) || cp(1, 2) > yl(2), return, end
            drag_start = cp(1, 1:2);
            if ~isempty(rect) && ishandle(rect), delete(rect); end
            rect = rectangle('Parent', axr, 'Position', [drag_start, 0.1, 0.1], 'EdgeColor', 'w', 'LineStyle', '--', 'LineWidth', 1);
            set(pf, 'WindowButtonMotionFcn', @on_move);
        end

        function on_move(~, ~)
            if isempty(drag_start), return, end
            cp = get(axr, 'CurrentPoint');
            p = [min(drag_start, cp(1, 1:2)), max(abs(cp(1, 1:2) - drag_start), 0.1)];
            set(rect, 'Position', p);
        end

        function on_up(~, ~)
            if isempty(drag_start), return, end
            set(pf, 'WindowButtonMotionFcn', '');
            cp = get(axr, 'CurrentPoint');
            on_select(drag_start, cp(1, 1:2));
            drag_start = [];
        end

        function on_select(p_click, p_release)
            x1 = fix(p_click(1) - 1);   y1 = fix(p_click(2) - 1);
            x2 = fix(p_release(1) - 1); y2 = fix(p_release(2) - 1);
            cx = floor((x1 + x2) / 2); cy = floor((y1 + y2) / 2);
            w = abs(x2 - x1); h = abs(y2 - y1);
            if ~isempty(template_side), side = template_side; else side = max(w, h); end
            half = floor(side / 2);
            nx1 = cx - half; nx2 = cx + half;
            ny1 = cy - half; ny2 = cy + half;
            if nx1 < 0, nx2 = nx2 + abs(nx1); nx1 = 0; end
            if ny1 < 0, ny2 = ny2 + abs(ny1); ny1 = 0; end
            if nx2 > w_img, nx1 = nx1 - (nx2 - w_img); nx2 = w_img; end
            if ny2 > h_img, ny1 = ny1 - (ny2 - h_img); ny2 = h_img; end
            nx1 = max(0, nx1); ny1 = max(0, ny1);
            final_side = min(nx2 - nx1, ny2 - ny1);
            xmin = nx1; xmax = nx1 + final_side;
            ymin = ny1; ymax = ny1 + final_side;
            roi_coords = [xmin, xmax, ymin, ymax];
            set(rect, 'Position', [xmin + 0.5, ymin + 0.5, max(final_side, 0.1), max(final_side, 0.1)], 'EdgeColor', 'y', 'LineStyle', '-');
            fprintf('>> ROI Snapped to Square: [%d, %d, %d, %d]\n', roi_coords);
        end
    end

    function side = get_roi_side(roi)
        v = fix(double(roi(:)));
        side = min(abs(v(2) - v(1)), abs(v(4) - v(3)));
    end

% ======================================================================
%  dashboard
% ======================================================================
    function init_dashboard_data()
        [temp_history, start_frame_idx] = puf_compute_trigger(full_data, points, Inf);
        update_plots();
    end

    function [block_size, C_val, resize_size, frame_avg] = get_filter_params()
        block_size = round(str2double(get(ed_block, 'String')));
        if ~isfinite(block_size), block_size = 21; end
        if block_size < 3, block_size = 3; end
        if mod(block_size, 2) == 0, block_size = block_size + 1; end
        C_val = str2double(get(ed_C, 'String'));
        if ~isfinite(C_val), C_val = 2.0; end
        resize_size = round(str2double(get(ed_resize, 'String')));
        if ~isfinite(resize_size), resize_size = 64; end
        if resize_size < 32, resize_size = 32; end
        frame_avg = round(str2double(get(ed_avg, 'String')));
        if ~isfinite(frame_avg), frame_avg = 1; end
        frame_avg = min(max(frame_avg, 1), 5);
    end

    function on_range_select()
        sel = get(list_ranges, 'Value');
        if isempty(sel), return, end
        start_t = str2double(get(ed_start, 'String'));
        step_t = str2double(get(ed_step, 'String'));
        if ~isfinite(start_t) || ~isfinite(step_t), return, end
        curr_min = start_t + (sel(1) - 1) * step_t;
        curr_max = curr_min + step_t;
        set(ed_vmin, 'String', sprintf('%.1f', curr_min));
        set(ed_vmax, 'String', sprintf('%.1f', curr_max));
        update_plots();
    end

    function update_plots()
        if isempty(temp_history) || isempty(roi_coords), return, end
        trig = str2double(get(ed_trig, 'String'));
        start_t = str2double(get(ed_start, 'String'));
        end_t = str2double(get(ed_end, 'String'));
        step_t = str2double(get(ed_step, 'String'));
        vmin = str2double(get(ed_vmin, 'String'));
        vmax = str2double(get(ed_vmax, 'String'));
        if ~all(isfinite([trig start_t end_t step_t vmin vmax])), return, end
        if vmin >= vmax, vmax = vmin + 1.0; end
        cmap_name = CMAPS{get(pop_cmap, 'Value')};

        % preview range list
        saved_sel = get(list_ranges, 'Value');
        items = {};
        curr = start_t; idx = 1;
        while curr < end_t
            c_max = round(curr + step_t, 2);
            c = round(curr, 2);
            items{end + 1} = sprintf(' %02d. %.1f ~ %.1f %sC', idx, c, c_max, char(176));   %#ok<AGROW>
            curr = curr + step_t; idx = idx + 1;
        end
        if isempty(saved_sel) || saved_sel(1) > numel(items), saved_sel = 1; end   % single-select listbox needs a scalar Value
        if isempty(items), saved_sel = []; end
        set(list_ranges, 'String', items, 'Value', saved_sel);

        % trigger detection
        [~, i_min] = min(temp_history);
        start_frame_idx = i_min - 1;
        frames = (0:num_frames - 1)';
        valid = find(temp_history >= trig & frames >= start_frame_idx);
        if ~isempty(valid)
            trigger_idx = valid(1) - 1;
            status_txt = sprintf('Triggered: Frame %d (%.1fC), Start Frame %d', trigger_idx, temp_history(trigger_idx + 1), start_frame_idx);
        else
            trigger_idx = num_frames - 1;
            status_txt = sprintf('Not Triggered (Start Frame %d)', start_frame_idx);
        end

        % temperature profile
        cla(ax_graph);
        hold(ax_graph, 'on');
        hs = plot(ax_graph, frames, temp_history, 'Color', [0 1 0.8]);
        labels = {'Avg Temp'};
        xlim(ax_graph, [0, max(num_frames - 1, 1)]);
        yl = get(ax_graph, 'YLim');
        patch([0 start_frame_idx start_frame_idx 0], [yl(1) yl(1) yl(2) yl(2)], [0.5 0.5 0.5], ...
            'Parent', ax_graph, 'FaceAlpha', 0.3, 'EdgeColor', 'none');
        hs(end + 1) = plot(ax_graph, [0, num_frames - 1], [trig trig], 'r--'); labels{end + 1} = 'Trigger';
        hs(end + 1) = plot(ax_graph, start_frame_idx, temp_history(start_frame_idx + 1), 'yo', 'MarkerSize', 6, 'MarkerFaceColor', 'y');
        labels{end + 1} = 'Start (Min Temp)';
        if ~isempty(valid)
            plot(ax_graph, trigger_idx, temp_history(trigger_idx + 1), 'ro', 'MarkerFaceColor', 'r');
        end
        set(ax_graph, 'YLim', yl);
        title(ax_graph, sprintf('Temperature Profile: %s', status_txt), 'Color', 'w', 'Interpreter', 'none');
        lg = legend(ax_graph, hs, labels);
        set(lg, 'TextColor', 'w', 'Color', PANEL, 'EdgeColor', [0.4 0.4 0.4]);
        grid(ax_graph, 'on');
        set(ax_graph, 'GridColor', 'w', 'GridAlpha', 0.2);

        % thermal ROI (with frame averaging)
        [block_size, C_val, ~, frame_avg] = get_filter_params();
        roi_img = puf_averaged_roi(full_data, roi_coords, trigger_idx, frame_avg);
        cla(ax_roi);
        imagesc(roi_img, 'Parent', ax_roi);
        set(ax_roi, 'CLim', [vmin vmax]);
        colormap(ax_roi, puf_colormap(cmap_name, 256));
        axis(ax_roi, 'image', 'off');
        if ~isempty(cbar) && ishandle(cbar), delete(cbar); end
        cbar = colorbar(ax_roi);
        set(cbar, 'Color', 'w');
        if frame_avg > 1, avg_tag = sprintf(' [avg=%d]', frame_avg); else avg_tag = ''; end
        title(ax_roi, sprintf('Thermal ROI (%.1f~%.1fC)%s', vmin, vmax, avg_tag), 'Color', 'w', 'Interpreter', 'none');

        % binary preview
        binary = puf_get_binary(roi_img, vmin, vmax, block_size, C_val);
        cla(ax_bin);
        imagesc(binary, 'Parent', ax_bin);
        set(ax_bin, 'CLim', [0 255]);
        colormap(ax_bin, gray(256));
        axis(ax_bin, 'image', 'off');
        if get(chk_dct_sign, 'Value'), sign_tag = 'sign'; else sign_tag = 'raw'; end
        title(ax_bin, sprintf('Preview Binary (blk=%d, C=%s, %s)', block_size, num2str(C_val), sign_tag), 'Color', 'w', 'Interpreter', 'none');
        drawnow;
    end

% ======================================================================
%  output generation
% ======================================================================
    function save_dir = generate_outputs_for_current_file()
        P = struct();
        P.start = str2double(get(ed_start, 'String'));
        P.end_ = str2double(get(ed_end, 'String'));
        P.step = str2double(get(ed_step, 'String'));
        P.trig = str2double(get(ed_trig, 'String'));
        if ~all(isfinite([P.start P.end_ P.step P.trig]))
            error('puf:params', 'Invalid temperature parameters.');
        end
        if P.end_ >= P.trig, error('puf:params', 'End Temp must be lower than Trigger Temp!'); end
        if P.start >= P.end_, error('puf:params', 'Start Temp must be lower than End Temp.'); end
        [P.block, P.C, P.resize, P.frame_avg] = get_filter_params();
        P.use_sign = logical(get(chk_dct_sign, 'Value'));
        P.crop = get(ed_crop, 'String');
        P.cmap = CMAPS{get(pop_cmap, 'Value')};
        P.do_bin = logical(get(chk_binary, 'Value'));
        P.do_bit = logical(get(chk_bit, 'Value'));
        P.do_excel = logical(get(chk_excel, 'Value'));
        P.do_thermal = logical(get(chk_thermal, 'Value'));

        init_dashboard_data();     % refresh temperature history / trigger with the current parameters
        save_dir = puf_generate_outputs(full_data, roi_coords, trigger_idx, file_dir, base_name, P);
    end

    function run_macro()
        try
            save_dir = generate_outputs_for_current_file();
        catch err
            errordlg(err.message, 'Error');
            return
        end
        [~, dn, de] = fileparts(save_dir);           % '.0' of '<name>_50.0' is not an extension
        msgbox(sprintf('All done!\nSaved in:\n%s%s', dn, de), 'Success');
    end

    function run_batch_point_setup()
        [names, folder] = uigetfile({'*_new.mat', 'New MAT files (*_new.mat)'}, ...
            'Select _new.mat file(s) for point setup', script_dir, 'MultiSelect', 'on');
        if isequal(names, 0), return, end
        if ischar(names), names = {names}; end
        file_paths = filter_target(cellfun(@(n) fullfile(folder, n), names, 'UniformOutput', false));
        if isempty(file_paths)
            warndlg('Only *_new.mat files can be selected.', 'Invalid Files');
            return
        end
        % one file per point group
        unique_group_files = {};
        seen = {};
        for k = 1:numel(file_paths)
            key = puf_names('group_key', file_paths{k});
            if any(strcmp(seen, key)), continue, end
            seen{end + 1} = key;                              %#ok<AGROW>
            unique_group_files{end + 1} = file_paths{k};      %#ok<AGROW>
        end
        point_setup_queue = unique_group_files;
        point_setup_mode = true;
        for k = 1:numel(point_setup_queue)
            point_setup_index = k;
            fp = point_setup_queue{point_setup_index};
            prepare_file_context(fp);
            [~, n, e] = fileparts(fp);
            set(lbl_filename, 'String', sprintf('[Setup %d/%d] %s%s', point_setup_index, numel(point_setup_queue), n, e));
            ok = select_points_popup();
            if ~ok || ~point_setup_mode
                point_setup_mode = false;
                return
            end
        end
        point_setup_mode = false;
        set(lbl_filename, 'String', 'Batch point setup complete');
        msgbox(sprintf(['All selected groups now have shared point files.\n\n' ...
            'Use ''Batch Run All Samples'' when you want to process the full dataset.']), 'Batch Point Setup Complete');
    end

    function run_batch_macro()
        [names, folder] = uigetfile({'*_new.mat', 'New MAT files (*_new.mat)'}, ...
            'Select _new.mat file(s) for batch run', script_dir, 'MultiSelect', 'on');
        if isequal(names, 0), return, end
        if ischar(names), names = {names}; end
        file_paths = filter_target(cellfun(@(n) fullfile(folder, n), names, 'UniformOutput', false));
        if isempty(file_paths)
            warndlg('Only *_new.mat files can be selected.', 'Invalid Files');
            return
        end
        success = {};
        failed = {};
        for idx = 1:numel(file_paths)
            fp = file_paths{idx};
            [~, n, e] = fileparts(fp);
            try
                prepare_file_context(fp);
                pts_path = puf_names('points_path', fp);
                group_roi_path = puf_names('group_roi_path', fp);
                common_roi_path = puf_names('common_roi_path', fp);
                if ~exist(pts_path, 'file')
                    [~, pn, pe] = fileparts(pts_path);
                    error('puf:batch', 'Missing shared points file: %s%s', pn, pe);
                end
                s = load(pts_path);
                points = double(s.points);
                if exist(group_roi_path, 'file')
                    d = load(group_roi_path);
                    roi_coords = double(d.roi(:))';
                elseif exist(common_roi_path, 'file')
                    d = load(common_roi_path);
                    roi_coords = double(d.roi(:))';
                else
                    [~, gn, ge] = fileparts(group_roi_path);
                    [~, cn, ce] = fileparts(common_roi_path);
                    error('puf:batch', 'Missing ROI file: %s%s (or fallback %s%s)', gn, ge, cn, ce);
                end
                drawnow;
                save_dir = generate_outputs_for_current_file();
                success{end + 1} = [n e];                                           %#ok<AGROW>
                set(lbl_filename, 'String', sprintf('[Batch %d/%d] %s%s', idx, numel(file_paths), n, e));
                fprintf('>> Batch processed: %s -> %s\n', fp, save_dir);
            catch err
                failed{end + 1} = sprintf('%s%s: %s', n, e, err.message);           %#ok<AGROW>
            end
        end
        if ~isempty(success)
            set(lbl_filename, 'String', sprintf('Batch complete: %d/%d', numel(success), numel(file_paths)));
        end
        if ~isempty(failed)
            shown = failed(1:min(10, numel(failed)));
            warndlg(sprintf('Processed %d/%d files.\n\n%s', numel(success), numel(file_paths), strjoin(shown, sprintf('\n'))), 'Batch Complete');
        else
            msgbox(sprintf('Processed all %d files successfully.', numel(success)), 'Batch Complete');
        end
    end

    function out = filter_target(paths)
        out = paths(cellfun(@(p) puf_names('is_target', p), paths));
    end

% ======================================================================
%  widget helpers
% ======================================================================
    function p = section(parent, ttl)
        p = uipanel('Parent', parent, 'Title', ttl, 'Units', 'pixels', 'BackgroundColor', PANEL, ...
            'ForegroundColor', ACCENT, 'FontName', 'Segoe UI', 'FontSize', 10, 'FontWeight', 'bold', ...
            'HighlightColor', [0.35 0.35 0.35]);
    end

    function [lbl, ed] = entry(parent, label_text, default)
        lbl = uicontrol('Parent', parent, 'Style', 'text', 'String', label_text, 'HorizontalAlignment', 'left', ...
            'BackgroundColor', PANEL, 'ForegroundColor', TEXTC, 'FontName', 'Segoe UI', 'FontSize', 10);
        ed = uicontrol('Parent', parent, 'Style', 'edit', 'String', default, 'HorizontalAlignment', 'left', ...
            'BackgroundColor', ENTRY, 'ForegroundColor', TEXTC, 'FontName', 'Segoe UI', 'FontSize', 10, ...
            'Callback', @(~, ~) update_plots(), 'UserData', lbl);
    end

    function h = checkbox(parent, str, value, cb)
        h = uicontrol('Parent', parent, 'Style', 'checkbox', 'String', str, 'Value', value, ...
            'BackgroundColor', PANEL, 'ForegroundColor', TEXTC, 'FontName', 'Segoe UI', 'FontSize', 10);
        if ~isempty(cb), set(h, 'Callback', cb); end
    end

    function h = button(parent, str, cb)
        h = uicontrol('Parent', parent, 'Style', 'pushbutton', 'String', str, ...
            'BackgroundColor', ACCENT, 'ForegroundColor', TEXTC, 'FontName', 'Segoe UI', ...
            'FontSize', 10, 'FontWeight', 'bold', 'Callback', cb);
    end

    function style_axes(a)
        set(a, 'Color', BG, 'XColor', 'w', 'YColor', 'w', 'Box', 'off');
    end
end
