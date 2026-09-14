function samplematcher()
%SAMPLEMATCHER  Perspective Correction Pro - warp thermal stacks onto a fixed grid.
%   SAMPLEMATCHER() opens the perspective-correction window.  Load one or
%   more .mat temperature stacks (Count2Temp output), scrub to a frame with
%   the arrow keys or the slider, place the 4 sample corners ("Set Points
%   (Manual)"; click a point again and use the arrow keys to nudge it,
%   Shift+arrow for 5 px), optionally snap them to the sample edge
%   ("Calculate Position (Auto)") and press "Run Current Sample".  Every
%   frame is warped to the Target Width x Height grid and saved as
%   <name>_new.mat (variable 'images'); the corners are saved as
%   <name>_xy.mat.  "Save Points Only" stores the corners for the whole
%   file group (same name with a different repeat index) and moves on to the
%   next group in the queue; "Batch Process Saved Points" then warps every
%   loaded file that has a saved point file.
%
%   MATLAB port of samplematcher.py.  Tested with MATLAB R2016a.
%   Requires Image Processing Toolbox.

addpath(fullfile(fileparts(mfilename('fullpath')), 'lib'));

BG      = [46 46 46] / 255;
PANEL   = [60 63 65] / 255;
TEXTC   = [1 1 1];
ACCENT  = [58 150 221] / 255;
ACTION  = [230 126 34] / 255;
SUCCESS = [39 174 96] / 255;
STOP    = [192 57 43] / 255;
ENTRY   = [69 73 74] / 255;
DISABLED = [127 140 141] / 255;
RIGHT_W = 350;

script_dir = fileparts(mfilename('fullpath'));

% ---- state --------------------------------------------------------------
mat_path = '';
full_images = [];
current_frame = [];
file_dir = script_dir;
file_name = '';
file_queue = {};
current_file_index = 0;
manual_points = zeros(0, 2);      % [x y], 0-based
is_positioning_mode = false;
selected_point_idx = [];
zoom_radius = 20;
img_obj = [];
scatter_manual = [];
scatter_selected = [];
line_manual = [];
zoom_img_obj = [];
zoom_marker = [];
zoom_hline = [];
zoom_vline = [];

% ---- window -------------------------------------------------------------
fig = figure('Name', 'Perspective Correction Pro (Auto-Snap Points)', 'NumberTitle', 'off', ...
    'MenuBar', 'none', 'ToolBar', 'none', 'Color', BG, 'Units', 'pixels', ...
    'Position', [40 40 1400 950], ...
    'WindowButtonDownFcn', @(~, ~) on_canvas_click(), 'KeyPressFcn', @on_key);

ax = axes('Parent', fig, 'Units', 'pixels', 'Color', BG, 'XColor', BG, 'YColor', BG);
axis(ax, 'off');
zoom_ax = axes('Parent', fig, 'Units', 'pixels', 'Color', [0.07 0.07 0.07], 'XColor', 'w', 'YColor', 'w', ...
    'XTick', [], 'YTick', [], 'Box', 'on', 'Visible', 'off');
title(zoom_ax, 'Zoom', 'Color', 'w', 'FontSize', 9);

right = uipanel('Parent', fig, 'Units', 'pixels', 'BackgroundColor', PANEL, 'BorderType', 'none');

p_file = section(right, ' 1. File Operations ');
lbl_file = uicontrol('Parent', p_file, 'Style', 'text', 'String', 'No file loaded', 'HorizontalAlignment', 'center', ...
    'BackgroundColor', PANEL, 'ForegroundColor', TEXTC, 'FontName', 'Segoe UI', 'FontSize', 10);
btn_load = button(p_file, 'Load MAT File', ACCENT, @(~, ~) load_file());

p_slide = section(right, ' 2. Select Frame (Use <- / ->) ');
lbl_frame = uicontrol('Parent', p_slide, 'Style', 'text', 'String', 'Frame: 0', 'HorizontalAlignment', 'left', ...
    'BackgroundColor', PANEL, 'ForegroundColor', TEXTC, 'FontName', 'Segoe UI', 'FontSize', 10);
slider = uicontrol('Parent', p_slide, 'Style', 'slider', 'Min', 0, 'Max', 100, 'Value', 0, ...
    'Callback', @(s, ~) on_slider_change(get(s, 'Value')));

p_pts = section(right, ' 3. Corner Detection ');
btn_pos = button(p_pts, 'Set Points (Manual)', ACCENT, @(~, ~) toggle_positioning_mode());
lbl_pts_status = uicontrol('Parent', p_pts, 'Style', 'text', 'String', 'Points: 0 / 4', 'HorizontalAlignment', 'center', ...
    'BackgroundColor', PANEL, 'ForegroundColor', TEXTC, 'FontName', 'Segoe UI', 'FontSize', 11);
btn_calc = button(p_pts, 'Calculate Position (Auto)', DISABLED, @(~, ~) run_calculation());
set(btn_calc, 'Enable', 'off');
btn_reset = button(p_pts, 'Reset Points', ACCENT, @(~, ~) reset_points(false));

p_target = section(right, ' 4. Target Scale ');
[lbl_w, ed_width] = entry(p_target, 'Target Width (mm):', '760');
[lbl_h, ed_height] = entry(p_target, 'Target Height (mm):', '390');

p_exec = section(right, ' 5. Execute ');
btn_save = button(p_exec, 'Run Current Sample', DISABLED, @(~, ~) run_warp_process());
set(btn_save, 'Enable', 'off');
btn_open = button(p_exec, 'Open Current Folder', ACCENT, @(~, ~) open_current_folder());
btn_save_points = button(p_exec, 'Save Points Only', DISABLED, @(~, ~) save_points_only());
set(btn_save_points, 'Enable', 'off');
btn_batch = button(p_exec, 'Batch Process Saved Points', ACTION, @(~, ~) batch_process_saved_points());

lbl_status = uicontrol('Parent', right, 'Style', 'text', 'String', 'Ready. Load a file.', 'HorizontalAlignment', 'center', ...
    'BackgroundColor', PANEL, 'ForegroundColor', [0.67 0.67 0.67], 'FontName', 'Segoe UI', 'FontSize', 10);

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
        set(ax, 'Position', [20, 20, left_w - 40, H - 40]);
        set(zoom_ax, 'Position', [20 + (left_w - 40) * 0.68, 20 + (H - 40) * 0.70, (left_w - 40) * 0.22, (H - 40) * 0.22]);

        pw = RIGHT_W - 30;
        y = H - 10;
        y = place_section(p_file, y, 96, pw);
        set(lbl_file, 'Position', [10, 96 - 48, pw - 20, 20]);
        set(btn_load, 'Position', [10, 10, pw - 20, 32]);

        y = place_section(p_slide, y, 88, pw);
        set(lbl_frame, 'Position', [12, 88 - 46, 150, 20]);
        set(slider, 'Position', [10, 10, pw - 20, 24]);

        y = place_section(p_pts, y, 170, pw);
        set(btn_pos, 'Position', [10, 170 - 62, pw - 20, 36]);
        set(lbl_pts_status, 'Position', [10, 170 - 90, pw - 20, 22]);
        set(btn_calc, 'Position', [10, 170 - 130, pw - 20, 36]);
        set(btn_reset, 'Position', [10, 6, pw - 20, 28]);

        y = place_section(p_target, y, 90, pw);
        set(lbl_w, 'Position', [12, 90 - 50, 150, 20]); set(ed_width, 'Position', [pw - 110, 90 - 52, 95, 24]);
        set(lbl_h, 'Position', [12, 90 - 80, 150, 20]); set(ed_height, 'Position', [pw - 110, 90 - 82, 95, 24]);

        exec_h = 200;
        set(p_exec, 'Position', [10, 40, pw, exec_h]);
        set(btn_save, 'Position', [10, exec_h - 70, pw - 20, 46]);
        set(btn_open, 'Position', [10, exec_h - 102, pw - 20, 26]);
        set(btn_save_points, 'Position', [10, exec_h - 146, pw - 20, 36]);
        set(btn_batch, 'Position', [10, 8, pw - 20, 36]);
        set(lbl_status, 'Position', [10, 8, pw, 22]);
    end

    function y = place_section(p, y_top, h, pw)
        set(p, 'Position', [10, y_top - h, pw, h]);
        y = y_top - h - 8;
    end

% ======================================================================
%  file loading / queue
% ======================================================================
    function load_file()
        [names, folder] = uigetfile({'*.mat', 'MAT files (*.mat)'}, 'Select MAT file(s)', script_dir, 'MultiSelect', 'on');
        if isequal(names, 0), return, end
        if ischar(names), names = {names}; end
        paths = cellfun(@(n) fullfile(folder, n), names, 'UniformOutput', false);
        try
            paths = paths(~cellfun(@(p) puf_names('sm_is_generated', p), paths));
            if isempty(paths)
                warndlg('Select source MAT files, not *_xy.mat or *_new.mat files.', 'Warning');
                return
            end
            file_queue = sort_queue(paths);
            current_file_index = 1;
            load_selected_mat_file(file_queue{current_file_index});
        catch err
            errordlg(sprintf('Failed to load: %s', err.message), 'Error');
        end
    end

    function sorted = sort_queue(paths)
        % order by (group key, repeat index, stem) like samplematcher.py
        keys = cell(size(paths));
        for k = 1:numel(paths)
            [~, stem] = fileparts(paths{k});
            tok = regexp(stem, '(?:[ _-])(\d+)$', 'tokens', 'once');
            if isempty(tok), rep = 0; else rep = str2double(tok{1}); end
            keys{k} = sprintf('%s|%012d|%s', puf_names('sm_group_key', paths{k}), rep, lower(stem));
        end
        [~, order] = sort(keys);
        sorted = paths(order);
    end

    function load_selected_mat_file(fp)
        full_images = puf_load_images(fp, 'temperature_frames');
        mat_path = fp;
        [file_dir, file_name] = fileparts(fp);
        num_frames = size(full_images, 1);
        init_idx = floor(num_frames * 0.1);
        set(slider, 'Min', 0, 'Max', max(num_frames - 1, 1), 'Value', init_idx, ...
            'SliderStep', [1, min(10, num_frames)] / max(num_frames - 1, 1));
        reset_points(true);
        update_image(init_idx);
        set(lbl_frame, 'String', sprintf('Frame: %d', init_idx));
        q = queue_label();
        set(lbl_file, 'String', [q file_name]);
        if restore_saved_points_for_current_file()
            status(sprintf('%sLoaded saved points for %s.', q, file_name));
        else
            status(sprintf('%sLoaded. Total frames: %d', q, num_frames));
        end
        figure(fig);
    end

    function q = queue_label()
        if ~isempty(file_queue) && current_file_index >= 1 && current_file_index <= numel(file_queue)
            q = sprintf('[%d/%d] ', current_file_index, numel(file_queue));
        else
            q = '';
        end
    end

    function paths = current_group_paths()
        if isempty(mat_path), paths = {}; return, end
        if isempty(file_queue), paths = {mat_path}; return, end
        key = puf_names('sm_group_key', mat_path);
        paths = file_queue(cellfun(@(p) strcmp(puf_names('sm_group_key', p), key), file_queue));
    end

    function moved = move_to_next_file_in_queue()
        moved = false;
        if isempty(file_queue), return, end
        current_key = '';
        if current_file_index >= 1 && current_file_index <= numel(file_queue)
            current_key = puf_names('sm_group_key', file_queue{current_file_index});
        end
        next_index = current_file_index + 1;
        while next_index <= numel(file_queue)
            if ~strcmp(puf_names('sm_group_key', file_queue{next_index}), current_key), break, end
            next_index = next_index + 1;
        end
        if next_index > numel(file_queue)
            status('All selected MAT files have saved points.');
            msgbox(sprintf(['All selected MAT files have saved points.\n\n' ...
                'Use ''Batch Process Saved Points'' to process them all at once.']), 'Queue Complete');
            return
        end
        current_file_index = next_index;
        load_selected_mat_file(file_queue{current_file_index});
        moved = true;
    end

    function ok = restore_saved_points_for_current_file()
        ok = false;
        xy_path = puf_names('xy_path', mat_path);
        if ~exist(xy_path, 'file'), return, end
        [pts, tw, th] = load_points_metadata(xy_path);
        manual_points = pts;
        selected_point_idx = [];
        set(ed_width, 'String', num2str(tw));
        set(ed_height, 'String', num2str(th));
        set(lbl_pts_status, 'String', 'Points: 4 / 4');
        enable(btn_calc, ACTION); enable(btn_save, SUCCESS); enable(btn_save_points, ACCENT);
        draw_points();
        ok = true;
    end

    function open_current_folder()
        if exist(file_dir, 'dir')
            winopen(file_dir);
        else
            warndlg('No active folder found.', 'Warning');
        end
    end

% ======================================================================
%  display
% ======================================================================
    function on_slider_change(val)
        if isempty(full_images), return, end
        idx = round(val);
        set(lbl_frame, 'String', sprintf('Frame: %d', idx));
        update_image(idx);
    end

    function update_image(idx)
        current_frame = reshape(full_images(idx + 1, :, :), size(full_images, 2), size(full_images, 3));
        if isempty(img_obj) || ~ishandle(img_obj)
            img_obj = imagesc(current_frame, 'Parent', ax);
            colormap(ax, jet(256));
            axis(ax, 'image', 'off');
            hold(ax, 'on');
        else
            set(img_obj, 'CData', current_frame);
            vmin = double(min(current_frame(:))); vmax = double(max(current_frame(:)));
            set(ax, 'CLim', [vmin, max(vmax, vmin + eps)]);
        end
        update_zoom_view();
        drawnow;
    end

    function draw_points()
        for h = [scatter_manual, scatter_selected, line_manual]
            if ~isempty(h) && ishandle(h), delete(h); end
        end
        scatter_manual = []; scatter_selected = []; line_manual = [];
        pts = manual_points;
        if ~isempty(pts)
            if size(pts, 1) > 1
                if size(pts, 1) == 4, closed = [pts; pts(1, :)]; else closed = pts; end
                line_manual = plot(ax, closed(:, 1) + 1, closed(:, 2) + 1, 'r--', 'LineWidth', 1);
            end
            scatter_manual = plot(ax, pts(:, 1) + 1, pts(:, 2) + 1, 'o', 'MarkerSize', 9, ...
                'MarkerFaceColor', 'r', 'MarkerEdgeColor', 'w', 'LineStyle', 'none');
            if ~isempty(selected_point_idx) && selected_point_idx >= 1 && selected_point_idx <= size(pts, 1)
                sp = pts(selected_point_idx, :);
                scatter_selected = plot(ax, sp(1) + 1, sp(2) + 1, 'o', 'MarkerSize', 16, ...
                    'MarkerEdgeColor', 'y', 'LineWidth', 2, 'LineStyle', 'none');
            end
        end
        update_zoom_view();
        drawnow;
    end

    function target = zoom_target_point()
        target = [];
        if isempty(manual_points), return, end
        if ~isempty(selected_point_idx) && selected_point_idx >= 1 && selected_point_idx <= size(manual_points, 1)
            target = manual_points(selected_point_idx, :);
        else
            target = manual_points(end, :);
        end
    end

    function update_zoom_view()
        if isempty(current_frame), return, end
        target = zoom_target_point();
        if isempty(target)
            set(zoom_ax, 'Visible', 'off');
            set(get(zoom_ax, 'Children'), 'Visible', 'off');
            return
        end
        [height, width] = size(current_frame);
        x = min(max(target(1), 0), width - 1);
        y = min(max(target(2), 0), height - 1);
        half = zoom_radius;
        x0 = max(0, floor(x - half)); x1 = min(width, ceil(x + half + 1));
        y0 = max(0, floor(y - half)); y1 = min(height, ceil(y + half + 1));
        region = current_frame(y0 + 1:y1, x0 + 1:x1);
        if isempty(region)
            set(zoom_ax, 'Visible', 'off');
            return
        end
        vmin = double(min(current_frame(:))); vmax = double(max(current_frame(:)));
        xdata = [x0 + 1, x1]; ydata = [y0 + 1, y1];        % pixel centres in MATLAB coordinates
        if isempty(zoom_img_obj) || ~ishandle(zoom_img_obj)
            zoom_img_obj = imagesc(xdata, ydata, region, 'Parent', zoom_ax);
            colormap(zoom_ax, jet(256));
            hold(zoom_ax, 'on');
            zoom_hline = plot(zoom_ax, [0 1], [y y] + 1, 'w-', 'LineWidth', 0.8);
            zoom_vline = plot(zoom_ax, [x x] + 1, [0 1], 'w-', 'LineWidth', 0.8);
            zoom_marker = plot(zoom_ax, x + 1, y + 1, 'o', 'MarkerSize', 10, 'MarkerEdgeColor', 'y', 'LineWidth', 1.4);
            set(zoom_ax, 'XTick', [], 'YTick', [], 'YDir', 'reverse', 'Box', 'on', 'XColor', 'w', 'YColor', 'w');
            title(zoom_ax, 'Zoom', 'Color', 'w', 'FontSize', 9);
        else
            set(zoom_img_obj, 'CData', region, 'XData', xdata, 'YData', ydata);
        end
        set(zoom_ax, 'CLim', [vmin, max(vmax, vmin + eps)], 'XLim', [x0 + 0.5, x1 + 0.5], 'YLim', [y0 + 0.5, y1 + 0.5]);
        set(zoom_hline, 'XData', [x0 + 0.5, x1 + 0.5], 'YData', [y y] + 1);
        set(zoom_vline, 'XData', [x x] + 1, 'YData', [y0 + 0.5, y1 + 0.5]);
        set(zoom_marker, 'XData', x + 1, 'YData', y + 1);
        set(zoom_ax, 'Visible', 'on');
        set(get(zoom_ax, 'Children'), 'Visible', 'on');
    end

% ======================================================================
%  points
% ======================================================================
    function set_position_button_state(active)
        if active
            set(btn_pos, 'String', 'Stop Setting', 'BackgroundColor', STOP);
        else
            set(btn_pos, 'String', 'Set Points (Manual)', 'BackgroundColor', ACCENT);
        end
    end

    function toggle_positioning_mode()
        if isempty(full_images)
            warndlg('Load a file first.', 'Warning');
            return
        end
        is_positioning_mode = ~is_positioning_mode;
        set_position_button_state(is_positioning_mode);
        if is_positioning_mode
            status('Click points to add or reselect them. Use arrow keys for fine adjustment.');
        else
            status('Positioning mode stopped.');
        end
    end

    function idx = find_nearby_point(x, y)
        idx = [];
        if isempty(manual_points) || isempty(current_frame), return, end
        d = sqrt(sum(bsxfun(@minus, manual_points, [x y]).^2, 2));
        pick_radius = max(8.0, min(size(current_frame)) * 0.03);
        [dmin, k] = min(d);
        if dmin <= pick_radius, idx = k; end
    end

    function on_canvas_click()
        if isempty(current_frame) || isempty(img_obj), return, end
        cp = get(ax, 'CurrentPoint');
        x = cp(1, 1); y = cp(1, 2);
        xl = get(ax, 'XLim'); yl = get(ax, 'YLim');
        if x < xl(1) || x > xl(2) || y < yl(1) || y > yl(2), return, end
        x = x - 1; y = y - 1;                                   % 0-based image coordinates

        sel = find_nearby_point(x, y);
        if ~isempty(sel)
            selected_point_idx = sel;
            draw_points();
            status(sprintf('Point %d selected. Use arrow keys to fine-tune it.', sel));
            return
        end
        if ~is_positioning_mode, return, end
        if size(manual_points, 1) >= 4
            status('Select an existing point to fine-tune it.');
            return
        end
        manual_points(end + 1, :) = [x y];
        selected_point_idx = size(manual_points, 1);
        draw_points();
        count = size(manual_points, 1);
        set(lbl_pts_status, 'String', sprintf('Points: %d / 4', count));
        if count == 4
            is_positioning_mode = false;
            set_position_button_state(false);
            enable(btn_calc, ACTION); enable(btn_save, SUCCESS); enable(btn_save_points, ACCENT);
            status('4 points set. Save points only, run this sample now, or calculate first.');
        else
            status(sprintf('Point %d added. Click it again, then use arrow keys to fine-tune.', count));
        end
    end

    function reset_points(silent)
        manual_points = zeros(0, 2);
        selected_point_idx = [];
        draw_points();
        set(lbl_pts_status, 'String', 'Points: 0 / 4');
        disable(btn_calc); disable(btn_save); disable(btn_save_points);
        is_positioning_mode = false;
        set_position_button_state(false);
        if ~silent, status('Points reset.'); end
    end

    function on_key(~, evt)
        shift = any(strcmp(evt.Modifier, 'shift'));
        if shift, step = 5; else step = 1; end
        switch evt.Key
            case 'leftarrow',  handle_horizontal(-step);
            case 'rightarrow', handle_horizontal(step);
            case 'uparrow',    handle_vertical(-step);
            case 'downarrow',  handle_vertical(step);
        end
    end

    function handle_horizontal(delta)
        if ~isempty(selected_point_idx)
            nudge_selected_point(delta, 0);
        elseif abs(delta) == 1
            move_frame(delta);
        end
    end

    function handle_vertical(delta)
        if ~isempty(selected_point_idx)
            nudge_selected_point(0, delta);
        end
    end

    function move_frame(delta)
        if isempty(full_images), return, end
        new_idx = round(get(slider, 'Value')) + delta;
        if new_idx >= 0 && new_idx < size(full_images, 1)
            set(slider, 'Value', new_idx);
            on_slider_change(new_idx);
        end
    end

    function nudge_selected_point(dx, dy)
        if isempty(selected_point_idx) || isempty(current_frame), return, end
        if selected_point_idx < 1 || selected_point_idx > size(manual_points, 1)
            selected_point_idx = [];
            return
        end
        [height, width] = size(current_frame);
        p = manual_points(selected_point_idx, :);
        p(1) = min(max(p(1) + dx, 0), width - 1);
        p(2) = min(max(p(2) + dy, 0), height - 1);
        manual_points(selected_point_idx, :) = p;
        draw_points();
        status(sprintf('Point %d adjusted to (%.1f, %.1f).', selected_point_idx, p(1), p(2)));
    end

    function run_calculation()
        if size(manual_points, 1) ~= 4
            warndlg('Please set 4 points first.', 'Warning');
            return
        end
        status('Calculating...');
        drawnow;
        try
            manual_points = puf_refine_corners(manual_points, current_frame);
            selected_point_idx = [];
            draw_points();
            status('Points snapped to edges. Click a point if you want more fine adjustment.');
            enable(btn_save, SUCCESS); enable(btn_save_points, ACCENT);
        catch err
            errordlg(sprintf('Calculation failed: %s', err.message), 'Error');
            status('Calculation failed.');
        end
    end

% ======================================================================
%  metadata / warping
% ======================================================================
    function [tw, th] = get_target_dimensions()
        tw = str2double(get(ed_width, 'String'));
        th = str2double(get(ed_height, 'String'));
        if ~isfinite(tw) || ~isfinite(th) || tw ~= fix(tw) || th ~= fix(th)
            error('puf:target', 'Invalid target dimensions.');
        end
        if tw <= 0 || th <= 0
            error('puf:target', 'Target dimensions must be positive.');
        end
    end

    function xy_path = save_points_metadata(fp, pts, tw, th)
        xy_path = puf_names('xy_path', fp);
        s = struct();
        s.x = single(pts(:, 1));
        s.y = single(pts(:, 2));
        s.target_width = int32(tw);
        s.target_height = int32(th);
        puf_save_mat(xy_path, s);
    end

    function [pts, tw, th] = load_points_metadata(xy_path)
        d = load(xy_path);
        [~, n, e] = fileparts(xy_path);
        if ~isfield(d, 'x') || ~isfield(d, 'y')
            error('puf:xy', 'Invalid point file: %s%s', n, e);
        end
        x = double(d.x(:)); y = double(d.y(:));
        if numel(x) ~= 4 || numel(y) ~= 4
            error('puf:xy', 'Point file must contain exactly 4 points: %s%s', n, e);
        end
        pts = [x y];
        if isfield(d, 'target_width'), tw = double(d.target_width(1)); else tw = str2double(get(ed_width, 'String')); end
        if isfield(d, 'target_height'), th = double(d.target_height(1)); else th = str2double(get(ed_height, 'String')); end
        if ~isfinite(tw) || ~isfinite(th) || tw <= 0 || th <= 0
            error('puf:xy', 'Invalid target size in point file: %s%s', n, e);
        end
    end

    function new_path = process_single_sample(fp, pts, tw, th, progress_prefix)
        images = puf_load_images(fp, 'temperature_frames');
        out = puf_warp_images(images, pts, tw, th, @(i, n) progress(progress_prefix, i, n));
        new_path = puf_names('new_path', fp);
        puf_save_mat(new_path, struct('images', out));
    end

    function progress(prefix, i, n)
        if ~isempty(prefix)
            status(sprintf('%s: %d/%d frames', prefix, i, n));
        end
        drawnow;
    end

    function run_warp_process()
        if size(manual_points, 1) ~= 4
            warndlg('Points not set.', 'Warning');
            return
        end
        if isempty(mat_path)
            warndlg('Load a file first.', 'Warning');
            return
        end
        try
            [tw, th] = get_target_dimensions();
            final_pts = manual_points;
            xy_path = save_points_metadata(mat_path, final_pts, tw, th);
            status('Processing current sample...');
            drawnow;
            new_path = process_single_sample(mat_path, final_pts, tw, th, 'Current sample');
            status('Processing complete.');
            [~, xn, xe] = fileparts(xy_path); [~, nn, ne] = fileparts(new_path);
            msgbox(sprintf('Files saved:\n%s%s\n%s%s', xn, xe, nn, ne), 'Success');
        catch err
            errordlg(sprintf('Processing failed: %s', err.message), 'Error');
            status('Processing failed.');
        end
    end

    function save_points_only()
        if size(manual_points, 1) ~= 4
            warndlg('Please set 4 points first.', 'Warning');
            return
        end
        if isempty(mat_path)
            warndlg('Load a file first.', 'Warning');
            return
        end
        try
            [tw, th] = get_target_dimensions();
            group_paths = current_group_paths();
            last_xy = '';
            for k = 1:numel(group_paths)
                last_xy = save_points_metadata(group_paths{k}, manual_points, tw, th);
            end
            [~, stem] = fileparts(mat_path);
            group_label = puf_names('strip_repeat', stem);
            status(sprintf('Saved shared point file for %s (%d file(s)).', group_label, numel(group_paths)));
            has_next = ~isempty(file_queue) && (current_file_index + 1) <= numel(file_queue);
            if has_next
                move_to_next_file_in_queue();
            else
                status('All selected MAT files have saved points.');
                [~, ln, le] = fileparts(last_xy);
                msgbox(sprintf(['Shared point file saved for group %s.\nApplied to %d file(s).\n\n' ...
                    'Last saved file:\n%s%s\n\nAll selected MAT files are done.\n' ...
                    'Use ''Batch Process Saved Points'' to process them all at once.'], ...
                    group_label, numel(group_paths), ln, le), 'Saved');
            end
        catch err
            errordlg(sprintf('Failed to save points: %s', err.message), 'Error');
        end
    end

    function batch_process_saved_points()
        if ~isempty(file_queue)
            loaded = file_queue;
        elseif ~isempty(mat_path)
            loaded = {mat_path};
        else
            loaded = {};
        end
        [~, ia] = unique(loaded, 'stable');
        loaded = loaded(sort(ia));
        if isempty(loaded)
            warndlg('Load MAT file(s) first.', 'Warning');
            return
        end
        success = {}; failed = {};
        total = numel(loaded);
        for idx = 1:total
            src = loaded{idx};
            [~, sn, se] = fileparts(src);
            source_name = [sn se];
            if ~exist(src, 'file')
                failed{end + 1} = sprintf('%s: MAT file not found', source_name);   %#ok<AGROW>
                continue
            end
            xy_path = puf_names('xy_path', src);
            if ~exist(xy_path, 'file')
                [~, xn, xe] = fileparts(xy_path);
                failed{end + 1} = sprintf('%s: saved point file not found (%s%s)', source_name, xn, xe);   %#ok<AGROW>
                continue
            end
            try
                [pts, tw, th] = load_points_metadata(xy_path);
                status(sprintf('Batch %d/%d: %s', idx, total, source_name));
                drawnow;
                new_path = process_single_sample(src, pts, tw, th, sprintf('Batch %d/%d', idx, total));
                [~, nn, ne] = fileparts(new_path);
                success{end + 1} = [nn ne];                                          %#ok<AGROW>
            catch err
                failed{end + 1} = sprintf('%s: %s', source_name, err.message);      %#ok<AGROW>
            end
        end
        summary = {sprintf('Processed %d / %d samples.', numel(success), total)};
        if ~isempty(failed)
            summary{end + 1} = '';
            summary = [summary, failed(1:min(10, numel(failed)))];
            if numel(failed) > 10
                summary{end + 1} = sprintf('... and %d more failures', numel(failed) - 10);
            end
        end
        status(sprintf('Batch complete: %d / %d samples processed.', numel(success), total));
        msgbox(strjoin(summary, sprintf('\n')), 'Batch Complete');
    end

% ======================================================================
%  widget helpers
% ======================================================================
    function status(msg)
        set(lbl_status, 'String', msg);
        drawnow;
    end

    function p = section(parent, ttl)
        p = uipanel('Parent', parent, 'Title', ttl, 'Units', 'pixels', 'BackgroundColor', PANEL, ...
            'ForegroundColor', ACCENT, 'FontName', 'Segoe UI', 'FontSize', 10, 'FontWeight', 'bold', ...
            'HighlightColor', [0.35 0.35 0.35]);
    end

    function [lbl, ed] = entry(parent, label_text, default)
        lbl = uicontrol('Parent', parent, 'Style', 'text', 'String', label_text, 'HorizontalAlignment', 'left', ...
            'BackgroundColor', PANEL, 'ForegroundColor', TEXTC, 'FontName', 'Segoe UI', 'FontSize', 10);
        ed = uicontrol('Parent', parent, 'Style', 'edit', 'String', default, ...
            'BackgroundColor', ENTRY, 'ForegroundColor', TEXTC, 'FontName', 'Segoe UI', 'FontSize', 10);
    end

    function h = button(parent, str, color, cb)
        h = uicontrol('Parent', parent, 'Style', 'pushbutton', 'String', str, ...
            'BackgroundColor', color, 'ForegroundColor', TEXTC, 'FontName', 'Segoe UI', ...
            'FontSize', 11, 'FontWeight', 'bold', 'Callback', cb);
    end

    function enable(h, color)
        set(h, 'Enable', 'on', 'BackgroundColor', color);
    end

    function disable(h)
        set(h, 'Enable', 'off', 'BackgroundColor', DISABLED);
    end
end
